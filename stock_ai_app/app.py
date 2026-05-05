# backend/app.py
from flask import Flask, render_template, request, jsonify
from datetime import datetime
import yfinance as yf
import requests
import sys
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from translations import bp as translations_bp
from flask import request, jsonify
from services.sectors import refresh_sector_universe, SECTOR_CACHE
from services.scores import refresh_scores, SCORE_CACHE
import random


# from services.yahoo_finance_client import YahooFinanceClient
# from ai_engines.engines import combined_score
# from services.smart_summary import generate_summary

# IMPORTS DE EJEMPLO (descomentar si existen en tu repo)
try:
    from services.yahoo_finance_client import YahooFinanceClient
except Exception:
    YahooFinanceClient = None

try:
    from ai_engines.engines import combined_score
except Exception:
    combined_score = None

try:
    from services.smart_summary import generate_summary
except Exception:
    generate_summary = None

print("🚀 Iniciando app.py", flush=True)
print(f"Python version: {sys.version}", flush=True)

app = Flask(__name__)
app.register_blueprint(translations_bp)

# Custom session for yfinance to bypass Render blocks
yf_session = requests.Session()
yf_session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
})

# Rate limiter
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["200 per 15 minutes"],
    storage_uri="memory://"
)

# Clientes (si tenés tu cliente, úsalo; si no, usaremos yfinance directo en helpers)
av_client = YahooFinanceClient() if YahooFinanceClient else None
yahoo_client = YahooFinanceClient() if YahooFinanceClient else None


# Mapeo de sufijos locales
LOCAL_TICKERS = {
    "AR": ".BA",
    "CL": ".CL",
    "PE": ".LP",
    "CO": ".CN",
    "MX": ".MX",
    "UY": ".UY",
    "PA": ".PA",
    "CR": ".CR",
    "DO": ".DO",
    "EC": ".EC",
    "PY": ".PY",
    "BO": ".BO",
    "VE": ".VE",
    "BR": ".SA",   # ajustar según convención (ej: BVMF)
    "MT": "",      # Malta: no hay ticker local por defecto
    "US": "",
    "ES": ".MC",
    "IT": ".MI",
    "GB": ".L",
}


# ---------- Helpers ----------
def fetch_price_from_yahoo(symbol: str):
    """Devuelve float o None. Usa yfinance directamente."""
    if not symbol:
        return None
    try:
        t = yf.Ticker(symbol, session=yf_session)
        hist = t.history(period="1d")
        if hist.empty:
            # intentar info regular
            info = t.info
            if info and "regularMarketPrice" in info and info["regularMarketPrice"] is not None:
                return float(info["regularMarketPrice"])
            return None
        return float(hist["Close"].iloc[-1])
    except Exception:
        return None


def fetch_fx_rate(from_currency: str, to_currency: str):
    """Devuelve la tasa float USD->target o None. Usa exchangerate.host y fallback."""
    if not from_currency or not to_currency or from_currency == to_currency:
        return 1.0
    try:
        # API principal
        url = f"https://api.exchangerate.host/latest?base={from_currency}&symbols={to_currency}"
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            data = r.json()
            rate = data.get("rates", {}).get(to_currency)
            if rate:
                return float(rate)

        # Fallback si exchangerate.host falla
        alt = requests.get(f"https://open.er-api.com/v6/latest/{from_currency}", timeout=5).json()
        rate = alt.get("rates", {}).get(to_currency)
        if rate:
            return float(rate)

        return None

    except Exception:
        return None

def get_sector_industry_manual(symbol):
    """Consulta directa a internet a la API de Yahoo, evadiendo bloqueos de yfinance."""
    try:
        import requests
        s = requests.Session()
        s.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        s.get('https://fc.yahoo.com', timeout=5)
        crumb = s.get('https://query1.finance.yahoo.com/v1/test/getcrumb', timeout=5).text
        url = f'https://query1.finance.yahoo.com/v10/finance/quoteSummary/{symbol}?modules=summaryProfile&crumb={crumb}'
        data = s.get(url, timeout=5).json()
        prof = data.get('quoteSummary', {}).get('result', [{}])[0].get('summaryProfile', {})
        return prof.get('sector'), prof.get('industry')
    except Exception:
        return None, None



def map_to_local_ticker(symbol: str, country: str):
    """Mapea símbolo a ticker local usando sufijos simples."""
    if not symbol:
        return None
    suffix = LOCAL_TICKERS.get((country or "").upper(), "")
    if not suffix:
        return None
    return f"{symbol}{suffix}"


def country_to_currency(country: str):
    mapping = {"MT": "EUR", "AR": "ARS", "US": "USD", "ES": "EUR", "IT": "EUR", "GB": "GBP", "BR": "BRL"}
    return mapping.get((country or "").upper(), "USD")


def resolve_local_price(symbol: str, country: str, price_usd):
    """Intenta obtener ticker local; si no existe, convierte USD->moneda local."""
    local_symbol = map_to_local_ticker(symbol, country)
    price_local = None
    if local_symbol:
        price_local = fetch_price_from_yahoo(local_symbol)
    # si no hay price_local y tenemos price_usd, convertir por FX
    if price_local is None and price_usd is not None:
        currency = country_to_currency(country)
        if currency != "USD":
            fx = fetch_fx_rate("USD", currency)
            if fx:
                price_local = round(price_usd * fx, 2)
    return local_symbol, price_local


# ---------- Routes ----------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
@limiter.limit("30 per minute")
def analyze():
    data = request.get_json(silent=True) or {}
    tickers_raw = data.get("tickers", "")
    date_str = data.get("date", "")
    country = data.get("country", "US")

    # parse date (si no viene, usamos hoy)
    if date_str:
        try:
            date = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return jsonify({"error": "Fecha inválida, formato esperado YYYY-MM-DD"}), 400
    else:
        date = datetime.utcnow()

    tickers = [t.strip().upper() for t in tickers_raw.split(",") if t.strip()]
    if not tickers:
        return jsonify({"error": "Debes introducir al menos un ticker"}), 400

    results = []
    for symbol in tickers:
        try:
            # 1) obtener series y scores (si tenés av_client y combined_score)
            df = None
            scores = {}
            if av_client and combined_score:
                try:
                    df = av_client.get_daily_series(symbol)
                    scores = combined_score(df, date, symbol, yahoo_client)
                except Exception as e:
                    print("WARN: fallo al calcular scores con av_client/combined_score:", e)

            # 2) precio USD: preferimos av_client.get_price_on_or_before si existe, sino yfinance
            price = None
            if av_client:
                try:
                    price = av_client.get_price_on_or_before(symbol, date)
                except Exception:
                    price = None
            if price is None:
                price = fetch_price_from_yahoo(symbol)

            price_usd = round(price, 4) if price is not None else None

            # 3) resolver precio local
            local_symbol, price_local_resolved = resolve_local_price(symbol, country, price_usd)

            # 4) info adicional (si tenés yahoo_client)
            info = {}
            try:
                t = yf.Ticker(symbol, session=yf_session)
                info = t.info or {}
            except Exception:
                info = {}

            sector = info.get("sector")
            industry = info.get("industry")
            
            # Si yfinance falla por culpa de Render, consultamos directo a internet
            if not sector or not industry:
                s_man, i_man = get_sector_industry_manual(symbol)
                sector = sector or s_man
                industry = industry or i_man

            # 5) summary (si existe la función)
            summary = None
            if generate_summary:
                try:
                    summary = generate_summary(symbol, scores, info)
                except Exception:
                    summary = None

            # 6) dominio para logo (simple)
            domain = f"{symbol.lower()}.com"

            # 7) armar resultado
            results.append({
                "symbol": symbol,
                "price": price_usd,                # legacy
                "price_usd": price_usd,
                "price_local": price_local_resolved,
                "currency_local": country_to_currency(country),
                "local_symbol": local_symbol,
                "ia1": round(scores.get("ia1", 0), 3) if isinstance(scores, dict) else None,
                "ia2": round(scores.get("ia2", 0), 3) if isinstance(scores, dict) else None,
                "ia3": round(scores.get("ia3", 0), 3) if isinstance(scores, dict) else None,
                "ia4": round(scores.get("ia4", 0), 3) if isinstance(scores, dict) else None,
                "ia5": round(scores.get("ia5", 0), 3) if isinstance(scores, dict) else None,
                "ia6": round(scores.get("ia6", 0), 3) if isinstance(scores, dict) else None,
                "total": round(scores.get("total", 0), 3) if isinstance(scores, dict) else None,
                "summary": summary,
                "sector": sector,
                "industry": industry,
                "logo": f"https://logo.clearbit.com/{domain}" if domain else None,
            })

        except Exception as e:
            print("ERROR EN", symbol, ":", e)
            results.append({
                "symbol": symbol,
                "error": str(e),
            })

    results_sorted = sorted(results, key=lambda x: x.get("total") if x.get("total") is not None else -1, reverse=True)
    # Log mínimo para debug
    print("REQ:", data)
    if results_sorted:
        print("RESULT sample:", results_sorted[0])
    return jsonify({"results": results_sorted})

@app.route("/convert", methods=["POST"])
def convert():
    data = request.get_json(silent=True) or {}
    amount = data.get("amount")
    from_currency = data.get("from")
    to_currency = data.get("to")

    if amount is None or from_currency is None or to_currency is None:
        return jsonify({"error": "Faltan parámetros: amount, from, to"}), 400

    fx = fetch_fx_rate(from_currency.upper(), to_currency.upper())
    if fx is None:
        return jsonify({"error": "No se pudo obtener la tasa de conversión"}), 500

    result = round(amount * fx, 4)
    return jsonify({
            "amount": amount,
            "from": from_currency.upper(),
            "to": to_currency.upper(),
            "rate": fx,
            "result": result
    })

import yfinance as yf
from flask import Blueprint, request, jsonify

bp = Blueprint("stocks", __name__)

@bp.route("/stocks/resolve", methods=["POST"])
def resolve_stock():
    data = request.get_json()
    query = data.get("q", "").strip()

    if not query:
        return jsonify({"error": "Nombre o símbolo inválido"}), 400

    try:
        # Yahoo Finance search
        results = yf.search(query)

        if not results or "quotes" not in results or len(results["quotes"]) == 0:
            return jsonify({"error": "No se encontró ninguna empresa con ese nombre"}), 404

        # Tomamos el primer resultado relevante
        for item in results["quotes"]:
            if item.get("quoteType") == "EQUITY":
                return jsonify({
                    "symbol": item.get("symbol"),
                    "name": item.get("shortname") or item.get("longname")
                })

        return jsonify({"error": "No se encontró ningún activo financiero válido"}), 404

    except Exception as e:
        return jsonify({"error": f"Error al buscar la empresa: {str(e)}"}), 500


@app.route("/sectors/picks", methods=["POST"])
def sectors_picks():
    data = request.get_json(silent=True) or {}
    sector = data.get("sector", "").strip()
    mode = data.get("mode", "free")

    if not sector:
        return jsonify({"error": "Sector requerido"}), 400

    refresh_sector_universe()
    refresh_scores(SECTOR_CACHE)

    symbols = SECTOR_CACHE.get(sector)
    if not symbols:
        return jsonify({"error": "Sector no encontrado"}), 404

    scored = []
    for symbol in symbols:
        s = SCORE_CACHE.get(symbol)
        if not s:
            continue
        scored.append({
            "symbol": symbol,
            "total": s["total"],
            "ia1": s["ia1"],
            "ia2": s["ia2"],
            "ia3": s["ia3"],
            "ia4": s["ia4"],
            "ia5": s["ia5"],
            "ia6": s["ia6"],
        })

    if not scored:
        return jsonify({"error": "No hay datos suficientes"}), 404

    scored_sorted = sorted(scored, key=lambda x: x["total"], reverse=True)

    if mode == "premium":
        picks = scored_sorted[:3]
    else:
        mid = len(scored_sorted) // 2
        window = scored_sorted[max(0, mid - 10):min(len(scored_sorted), mid + 10)]
        picks = random.sample(window, k=min(3, len(window)))

    results = []
    for item in picks:
        symbol = item["symbol"]
        try:
            info = yf.Ticker(symbol).info or {}
        except:
            info = {}

        domain = f"{symbol.lower()}.com"
        results.append({
            "symbol": symbol,
            "total": round(item["total"], 3),
            "ia1": item["ia1"],
            "ia2": item["ia2"],
            "ia3": item["ia3"],
            "ia4": item["ia4"],
            "ia5": item["ia5"],
            "ia6": item["ia6"],
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "logo": f"https://logo.clearbit.com/{domain}"
        })

    return jsonify({"results": results})




if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=True)
