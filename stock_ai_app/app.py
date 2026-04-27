from flask import Flask, render_template, request, jsonify
from datetime import datetime
from services.yahoo_finance_client import YahooFinanceClient
import yfinance as yf
from ai_engines.engines import combined_score
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from services.smart_summary import generate_summary

app = Flask(__name__)

# ⭐ CONFIGURACIÓN DE RATE LIMITING PARA RENDER
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per 15 minutes"],  # 200 requests cada 15 minutos por IP real
    storage_uri="memory://"  # Opcional: elimina la advertencia de memoria
)


av_client = YahooFinanceClient()
yahoo_client = YahooFinanceClient()



@app.route("/")
def index():
    return render_template("index.html")

@app.route("/analyze", methods=["POST"])
@limiter.limit("30 per minute")  # ⭐ Limita a 30 requests por minuto por IP
def analyze():
    data = request.get_json()
    tickers_raw = data.get("tickers", "")
    date_str = data.get("date", "")

    try:
        date = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "Fecha inválida"}), 400

    tickers = [t.strip().upper() for t in tickers_raw.split(",") if t.strip()]
    if not tickers:
        return jsonify({"error": "Debes introducir al menos un ticker"}), 400

    results = []
    for symbol in tickers:
        try:
            df = av_client.get_daily_series(symbol)
            scores = combined_score(df, date, symbol, yahoo_client)
            price = av_client.get_price_on_or_before(symbol, date)
            
            # ⭐ OBTENER INFORMACIÓN ADICIONAL (agrega esto)
            info = yahoo_client.get_stock_info(symbol)  # Si tienes este método
            sector = info.get("sector") if info else None
            industry = info.get("industry") if info else None
            
            # Generar un resumen simple (o usa tu lógica existente)
            summary = f"Análisis de {symbol} - Score total: {scores['total']:.3f}"
            
            # Obtener dominio para el logo
            domain = f"{symbol.lower()}.com"  # Simplificado, ajusta según necesites
                # df = av_client.get_daily_series(symbol)
                # scores = combined_score(df, date, symbol, yahoo_client)
                # price = av_client.get_price_on_or_before(symbol, date)
            results.append(
                    {
                        "symbol": symbol,
                        "price": round(price, 4),
                        "ia1": round(scores["ia1"], 3),
                        "ia2": round(scores["ia2"], 3),
                        "ia3": round(scores["ia3"], 3),
                        "ia4": round(scores["ia4"], 3),
                        "ia5": round(scores["ia5"], 3),
                        "ia6": round(scores["ia6"], 3),
                        "total": round(scores["total"], 3),
                        "summary": summary,
                        "sector": info.get("sector"),
                        "industry": info.get("industry"),
                        "logo": f"https://logo.clearbit.com/{domain}" if domain else None,
                    }
                )

        except Exception as e:
            print("ERROR EN", symbol, ":", e)
            results.append(
                {
                    "symbol": symbol,
                    "error": str(e),
                }
            )
        
        info = yf.Ticker(symbol).info

        summary = generate_summary(
            symbol,
            scores,
            info
        )

        website = info.get("website")
        domain = None
        if website:
            domain = website.replace("https://", "").replace("http://", "").split("/")[0]


    # Ordenamos por score total descendente
    results_sorted = sorted(
        results, key=lambda x: x.get("total", -1), reverse=True
    )

    return jsonify({"results": results_sorted})


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=True)
