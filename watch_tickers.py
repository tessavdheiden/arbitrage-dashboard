import asyncio
import ccxt.pro as ccxt  # noqa: E402
import dash
from dash import dcc, html, Input, Output
import plotly.graph_objs as go
import threading
from itertools import product
import time
from datetime import datetime, timedelta

# Shared data structures for bids and asks
data = {}

# Symbols and exchanges
symbols = ['ETH/USD', 'BTC/USD', "LTC/USD"]
exchanges = [
    # ccxt.exmo({'options': {'defaultType': 'spot'}}),
    ccxt.cryptocom({'options': {'defaultType': 'spot'}}),
    ccxt.okx({'options': {'defaultType': 'spot'}}),
    # ccxt.myokx({'options': {'defaultType': 'spot'}}),
    # ccxt.whitebit({'options': {'defaultType': 'spot'}}),
    # ccxt.kraken({'options': {'defaultType': 'spot'}}),
]

# Initialize shared data
for symbol in symbols:
    data[symbol] = {exchange: {'timestamps': [], 'bids': [], 'asks': [], 'datetimes': []} for exchange in exchanges}


async def watch_exchange(exchange, symbols, data):
    try:
        while True:
            try: # Connection to X timed out due to a ping-pong keepalive missing on time
                tickers = await exchange.watch_tickers(symbols)

                for symbol in symbols:
                    if symbol not in tickers.keys():
                        continue

                    data[symbol][exchange]['bids'].append(tickers[symbol]['bid'])
                    data[symbol][exchange]['asks'].append(tickers[symbol]['ask'])
                    timestamp = tickers[symbol]['timestamp']

                    if timestamp is None:
                        if tickers[symbol]['info'].get('updated_at') is not None:
                            timestamp = tickers[symbol]['info']['updated_at']
                        else:
                            timestamp = datetime.now().timestamp() * 1000
                    data[symbol][exchange]['timestamps'].append(timestamp)
                    datetime_obj = datetime.fromtimestamp(timestamp / 1000)  # Divide by 1000 for seconds
                    data[symbol][exchange]['datetimes'].append(datetime_obj.strftime('%Y-%m-%d %H:%M:%S'))
                    # print(f"{exchange.name = }, {symbol = }: {tickers[symbol]['bid']}, {tickers[symbol]['ask']}")

            except Exception as e:
                print(f"Error with watch ticker: {exchange.name}: {e}")
    except Exception as e:
        print(f"Error with {exchange.name}: {e}")
    finally:
        await exchange.close()


def start_data_collection():
    async def run():
        await asyncio.gather(*(watch_exchange(ex, symbols, data) for ex in exchanges))

    asyncio.run(run())