import yfinance as yf
import pandas as pd
import time


class YahooFinanceClient:
    def __init__(self):
        pass

    def get_daily_series(self, symbol, max_retries=3):
        """
        Obtiene datos diarios con reintentos automáticos en caso de rate limit
        """
        for intento in range(max_retries):
            try:
                # Tu código original aquí
                ticker = yf.Ticker(symbol)
                df = ticker.history(period="5y")

                if df.empty:
                    raise ValueError(f"Sin datos para {symbol}")

                # 🔥 FIX: quitar zona horaria del índice
                df.index = df.index.tz_localize(None)

                df = df.rename(columns={
                    "Open": "open",
                    "High": "high",
                    "Low": "low",
                    "Close": "close",
                    "Volume": "volume"
                })

                df["adj_close"] = df["close"]
                return df

                
            except Exception as e:
                error_msg = str(e).lower()
                
                # Si es rate limit de Yahoo Finance
                if "rate" in error_msg or "too many" in error_msg or "429" in error_msg:
                    espera = (intento + 1) * 2  # 2, 4, 6 segundos
                    print(f"⚠️ Rate limit en Yahoo Finance para {symbol}. Reintento {intento+1}/{max_retries} en {espera}s...")
                    time.sleep(espera)
                else:
                    # Otro error, no reintentamos
                    print(f"❌ Error obteniendo {symbol}: {e}")
                    raise e
        
        # Si llegamos aquí, todos los reintentos fallaron
        raise Exception(f"No se pudo obtener {symbol} después de {max_retries} intentos")


    def get_price_on_or_before(self, symbol, date):
        df = self.get_daily_series(symbol)

        # 🔥 FIX: asegurarse que date no tenga timezone
        if hasattr(date, "tzinfo") and date.tzinfo is not None:
            date = date.replace(tzinfo=None)

        df = df[df.index <= date]

        if df.empty:
            raise Exception(f"Sin datos para {symbol}")

        return df.iloc[-1]["close"]
    
    def get_stock_info(self, symbol, max_retries=2):
        # """Obtiene información del sector, industria, etc. con reintentos."""
        for intento in range(max_retries):
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info
                
                if not info:
                    raise ValueError(f"No se encontró información para {symbol}")
                
                return {
                    "sector": info.get("sector"),
                    "industry": info.get("industry"),
                    "website": info.get("website"),
                }
                    
            except Exception as e:
                print(f"Intento {intento + 1}/{max_retries} - Error obteniendo info de {symbol}: {e}")
                if intento < max_retries - 1:
                    time.sleep(2)
                else:
                    return {
                        "sector": None,
                        "industry": None,
                        "website": None,
                    }