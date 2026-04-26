import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["ma_20"] = df["adj_close"].rolling(20).mean()
    df["ma_50"] = df["adj_close"].rolling(50).mean()
    df["ret_5"] = df["adj_close"].pct_change(5)
    df["ret_20"] = df["adj_close"].pct_change(20)

    # RSI simple
    delta = df["adj_close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / (loss + 1e-9)
    df["rsi_14"] = 100 - (100 / (1 + rs))

    return df


# IA 1: Técnica (tendencia + RSI)
def ia1_technical_score(df: pd.DataFrame, date) -> float:
    df = compute_indicators(df)
    row = df[df.index <= date].iloc[-1]

    score = 0.0
    # Precio por encima de MA50 = tendencia alcista
    if row["adj_close"] > row["ma_50"]:
        score += 0.4
    # Precio por encima de MA20
    if row["adj_close"] > row["ma_20"]:
        score += 0.3
    # RSI entre 40 y 60 = zona “saludable”
    if 40 <= row["rsi_14"] <= 60:
        score += 0.3
    # RSI muy bajo (sobreventa) puede ser oportunidad
    if row["rsi_14"] < 30:
        score += 0.2

    return float(score)


# IA 2: Valor relativo (barata vs su propio histórico reciente)
def ia2_value_relative_score(df: pd.DataFrame, date) -> float:
    df = df[df.index <= date].copy()
    if len(df) < 60:
        return 0.0

    last_price = df["adj_close"].iloc[-1]
    window = df["adj_close"].tail(60)
    mean = window.mean()
    std = window.std() + 1e-9

    z = (last_price - mean) / std
    # Cuanto más negativa la z, más “barata” vs su media
    # Normalizamos a [0,1] de forma simple
    score = np.clip(-z / 3 + 0.5, 0, 1)
    return float(score)


# IA 3: Modelo ML simple (RandomForest sobre features técnicos)
def ia3_ml_score(df: pd.DataFrame, date) -> float:
    df = compute_indicators(df)
    df = df.dropna().copy()
    if len(df) < 80:
        return 0.0

    # Features y target: predecir retorno futuro a 10 días
    df["future_ret_10"] = df["adj_close"].pct_change(10).shift(-10)
    df = df.dropna()

    features = ["ma_20", "ma_50", "ret_5", "ret_20", "rsi_14"]
    X = df[features]
    y = df["future_ret_10"]

    # Entrenamos con todo el histórico menos las últimas 10 velas
    X_train = X.iloc[:-10]
    y_train = y.iloc[:-10]

    model = RandomForestRegressor(
        n_estimators=80, random_state=42, max_depth=5
    )
    model.fit(X_train, y_train)

    # Tomamos la fila más cercana a la fecha
    if df[df.index <= date].empty:
        return 0.0
    row = df[df.index <= date].iloc[-1]

# Crear DataFrame con nombres de columnas
    X_input = pd.DataFrame([{
        'ma_20': row['ma_20'],
        'ma_50': row['ma_50'],
        'ret_5': row['ret_5'],
        'ret_20': row['ret_20'],
        'rsi_14': row['rsi_14']
    }])

    pred_ret = model.predict(X_input)[0]

    # Convertimos retorno esperado a score [0,1]
    score = np.clip((pred_ret + 0.1) / 0.2, 0, 1)
    return float(score)

def ia4_financial_health(symbol, yf_client):
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info

        de = info.get("debtToEquity", None)
        current = info.get("currentRatio", None)
        quick = info.get("quickRatio", None)

        # Si falta todo, devolvemos neutral
        if de is None and current is None and quick is None:
            return 0.5

        # --- Debt/Equity ---
        if de is None:
            score_de = 0.5
        elif de < 0.5:
            score_de = 1.0
        elif de < 1.5:
            score_de = 0.7
        else:
            score_de = 0.3

        # --- Current Ratio ---
        if current is None:
            score_current = 0.5
        elif current > 1.5:
            score_current = 1.0
        elif current >= 1.0:
            score_current = 0.7
        else:
            score_current = 0.3

        # --- Quick Ratio ---
        if quick is None:
            score_quick = 0.5
        elif quick > 1.0:
            score_quick = 1.0
        elif quick >= 0.5:
            score_quick = 0.7
        else:
            score_quick = 0.3

        # Puntaje final IA4
        score = (score_de * 0.5) + (score_current * 0.25) + (score_quick * 0.25)
        return score

    except Exception:
        return 0.5
    
import re
import numpy as np
import yfinance as yf

NEGATIVE_KEYWORDS = [
    "fraud", "lawsuit", "fine", "sanction", "probe", "investigation",
    "scandal", "corruption", "bribery", "antitrust", "regulator",
    "recall", "data breach", "hack", "layoffs", "bankruptcy",
    "default", "restatement", "sec charges", "whistleblower",
]

POSITIVE_KEYWORDS = [
    "award", "recognition", "best workplace", "esg", "sustainability",
    "upgrade", "investment", "partnership", "contract win",
    "approval", "license", "patent", "milestone",
]


def ia5_reputation_score(symbol: str) -> float:
    try:
        ticker = yf.Ticker(symbol)
        news = getattr(ticker, "news", None)

        if not news:
            return 0.5  # neutral si no hay noticias

        neg_hits = 0
        pos_hits = 0
        total_items = 0

        for item in news[:30]:  # últimas 30 noticias
            title = (item.get("title") or "").lower()
            summary = (item.get("summary") or "").lower()
            text = title + " " + summary

            if not text.strip():
                continue

            total_items += 1

            for kw in NEGATIVE_KEYWORDS:
                if re.search(r"\b" + re.escape(kw) + r"\b", text):
                    neg_hits += 1

            for kw in POSITIVE_KEYWORDS:
                if re.search(r"\b" + re.escape(kw) + r"\b", text):
                    pos_hits += 1

        if total_items == 0:
            return 0.5

        raw = pos_hits - neg_hits  # puede ser negativo
        score = 0.5 + np.tanh(raw / 5) * 0.5  # normalización suave

        return float(np.clip(score, 0, 1))

    except Exception:
        return 0.5
    
import numpy as np
import yfinance as yf

def ia6_market_outlook_score(symbol: str) -> float:
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info

        # --- 1. Recomendación de analistas ---
        # recommendationMean: 1 = Strong Buy, 5 = Sell
        rec_mean = info.get("recommendationMean", None)
        if rec_mean is None:
            score_rec = 0.5
        else:
            # Convertimos 1–5 a 0–1 (1=1.0, 5=0.0)
            score_rec = np.clip((5 - rec_mean) / 4, 0, 1)

        # --- 2. Precio objetivo vs precio actual ---
        current = info.get("currentPrice", None)
        target = info.get("targetMeanPrice", None)
        if current is None or target is None or current <= 0:
            score_target = 0.5
        else:
            upside = (target - current) / current
            # Normalizamos upside: -20% = 0, +20% = 1
            score_target = np.clip((upside + 0.2) / 0.4, 0, 1)

        # --- 3. Tendencia de ganancias (earningsTrend) ---
        trend = info.get("earningsTrend", None)
        score_trend = 0.5
        if trend and isinstance(trend, list):
            # Buscamos el forecast más reciente
            for t in trend:
                if "earningsEstimate" in t:
                    est = t["earningsEstimate"]
                    growth = est.get("growth", None)
                    if growth is not None:
                        # growth: -0.2 a +0.2 → 0 a 1
                        score_trend = np.clip((growth + 0.2) / 0.4, 0, 1)
                    break

        # --- 4. Estimaciones de crecimiento (growthEstimates) ---
        growth_est = info.get("growthEstimates", None)
        score_growth = 0.5
        if growth_est and isinstance(growth_est, dict):
            long_term = growth_est.get("longterm", None)
            if long_term is not None:
                score_growth = np.clip((long_term + 0.1) / 0.2, 0, 1)

        # --- Score final IA6 ---
        score = (
            0.35 * score_rec +
            0.25 * score_target +
            0.20 * score_trend +
            0.20 * score_growth
        )

        return float(np.clip(score, 0, 1))

    except Exception:
        return 0.5


    
def combined_score(df: pd.DataFrame, date, symbol, yf_client) -> dict:
    s1 = ia1_technical_score(df, date)
    s2 = ia2_value_relative_score(df, date)
    s3 = ia3_ml_score(df, date)
    s4 = ia4_financial_health(symbol, yf_client)
    s5 = ia5_reputation_score(symbol)
    s6 = ia6_market_outlook_score(symbol)

    total = (
        0.22 * s1 +   # técnico
        0.16 * s2 +   # valor relativo
        0.16 * s3 +   # ML
        0.22 * s4 +   # salud financiera
        0.12 * s5 +   # reputación
        0.12 * s6     # proyección de mercado
    )

    return {
        "ia1": s1,
        "ia2": s2,
        "ia3": s3,
        "ia4": s4,
        "ia5": s5,
        "ia6": s6,
        "total": float(total),
    }
