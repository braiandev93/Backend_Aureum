from datetime import datetime, timedelta
from services.core import av_client, combined_score, yahoo_client

SCORE_CACHE = {}
SCORE_LAST_REFRESH = None

def refresh_scores(sector_cache):
    global SCORE_CACHE, SCORE_LAST_REFRESH

    if SCORE_LAST_REFRESH and datetime.utcnow() - SCORE_LAST_REFRESH < timedelta(hours=24):
        return

    SCORE_CACHE = {}

    for sector, symbols in sector_cache.items():
        for symbol in symbols:
            try:
                df = av_client.get_daily_series(symbol)
                scores = combined_score(df, datetime.utcnow(), symbol, yahoo_client)
                SCORE_CACHE[symbol] = {
                    "total": scores.get("total", 0),
                    "ia1": scores.get("ia1"),
                    "ia2": scores.get("ia2"),
                    "ia3": scores.get("ia3"),
                    "ia4": scores.get("ia4"),
                    "ia5": scores.get("ia5"),
                    "ia6": scores.get("ia6"),
                }
            except Exception:
                continue

    SCORE_LAST_REFRESH = datetime.utcnow()
