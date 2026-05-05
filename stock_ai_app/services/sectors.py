import yfinance as yf
from datetime import datetime, timedelta
from services.sp500 import load_sp500_symbols

SECTOR_CACHE = {}
SECTOR_LAST_REFRESH = None

def refresh_sector_universe():
    global SECTOR_CACHE, SECTOR_LAST_REFRESH

    if SECTOR_LAST_REFRESH and datetime.utcnow() - SECTOR_LAST_REFRESH < timedelta(hours=24):
        return

    symbols = load_sp500_symbols()
    sector_map = {}

    for symbol in symbols:
        try:
            info = yf.Ticker(symbol).info or {}
            sector = info.get("sector") or "Unknown"
            sector_map.setdefault(sector, []).append(symbol)
        except:
            continue

    SECTOR_CACHE = sector_map
    SECTOR_LAST_REFRESH = datetime.utcnow()
