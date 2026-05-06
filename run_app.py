from app import app
import webbrowser
webbrowser.open("http://127.0.0.1:5000")
import yfinance
import pandas
import numpy
import requests
import lxml
import bs4
import html5lib




if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)
