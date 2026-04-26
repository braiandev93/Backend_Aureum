import yfinance as yf
import pandas as pd

class YahooFinanceClient:
    def __init__(self):
        pass

    def get_daily_series(self, symbol: str) -> pd.DataFrame:
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

    def get_price_on_or_before(self, symbol, date):
        df = self.get_daily_series(symbol)

        # 🔥 FIX: asegurarse que date no tenga timezone
        if hasattr(date, "tzinfo") and date.tzinfo is not None:
            date = date.replace(tzinfo=None)

        df = df[df.index <= date]

        if df.empty:
            raise Exception(f"Sin datos para {symbol}")

        return df.iloc[-1]["close"]
