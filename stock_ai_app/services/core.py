from services.yahoo_finance_client import YahooFinanceClient
from ai_engines.engines import combined_score
from services.smart_summary import generate_summary

# Instancias compartidas
av_client = YahooFinanceClient()
yahoo_client = YahooFinanceClient()
