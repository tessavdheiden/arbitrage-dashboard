# From https://github.com/ccxt/ccxt/blob/master/examples/bots/py/spot-arbitrage-bot.py
# -*- coding: utf-8 -*-
import pandas as pd
from dash import Dash, dcc, html, Input, Output
import plotly.graph_objs as go
import asyncio
import os
from datetime import datetime
import threading
import sys
import time
from itertools import product

root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.append(root + '/python')

import ccxt.async_support as ccxt  # noqa: E402

print('CCXT Version:', ccxt.__version__)

# options
wait_time = 5  # seconds to wait between each check
max_length = 10
save_frequency = 50

# exchanges you want to use to look for arbitrage opportunities
exchanges = [
    ccxt.kraken(),
    ccxt.coinbase(),
    ccxt.bitstamp(),
]

# symbols you want to trade
symbols = [
    "BTC/USD",
    "LTC/USD",
    "ETH/USD",
]

# order sizes for each symbol, adjust it to your liking
order_sizes = {
    "BTC/USD": 0.001,
    "LTC/USD": 0.01,
    "ETH/USD": 0.01,
}

# Shared data storage
wallet = {"time": [], "value": []}
market_data = {symbol: {"time": [], "profit": []} for symbol in symbols}

# Create Dash app
app = Dash(__name__)

app.layout = html.Div([
    html.Div([
        dcc.Graph(id='live-graph'),
    ], style={'width': '100%', 'height': '50%'}),  # First graph (top plot)

    html.Div([
        dcc.Graph(id='wallet-graph'),
    ], style={'width': '100%', 'height': '50%'}),  # Second graph (bottom plot)
    dcc.Interval(
        id='interval-component',
        interval=1000,  # Update every 1000 ms (1 second)
        n_intervals=0
    )
])


async def get_last_prices():
    tasks = [exchange.fetch_tickers(symbols) for exchange in exchanges]
    results = await asyncio.gather(*tasks)
    return results


async def bot():
    prices = await get_last_prices()

    money = wallet['value'][-1] if len(wallet['value']) > 0 else 0.
    for symbol in symbols:
        ms = int(time.time() * 1000)
        timestamp = datetime.fromtimestamp(ms / 1000.0).strftime('%Y-%m-%d %H:%M:%S')

        # Extract bid and ask prices for the current symbol
        bids = {ex: px[symbol]['bid'] for ex, px in zip(exchanges, prices)}
        asks = {ex: px[symbol]['ask'] for ex, px in zip(exchanges, prices)}

        # Generate combinations of bids and asks from different exchanges
        combinations = [
            (b_ex, b_p, a_ex, a_p, b_p - a_p)
            for (b_ex, b_p), (a_ex, a_p) in product(bids.items(), asks.items())
            if b_ex != a_ex and b_p is not None and a_p is not None
        ]

        # Find the combination with the maximum spread
        max_exchange, max_price, min_exchange, min_price, price_profit = max(combinations, key=lambda x: x[4])

        order_size = order_sizes[symbol]

        # calculate min exchange taker fee
        # warning: you need to manually check if there are special campaign fees
        min_exchange_fee = min_exchange.fees['trading']['taker']
        min_fee = order_size * min_price * min_exchange_fee

        # calculate max exchange taker fee
        # warning: you need to manually check if there are special campaign fees
        max_exchange_fee = max_exchange.fees['trading']['taker']
        max_fee = order_size * max_price * max_exchange_fee

        profit = (price_profit * order_size) - min_fee - max_fee

        market_data[symbol]['time'].append(timestamp)
        market_data[symbol]['profit'].append(profit)

        money += profit if profit > 0 else 0

    ms = int(time.time() * 1000)
    wallet["time"].append(datetime.fromtimestamp(ms / 1000.0).strftime('%Y-%m-%d %H:%M:%S'))
    wallet["value"].append(money)


def save_data():
    all_data = [
        {"symbol": symbol, "time": t, "profit": p}
        for symbol, data in market_data.items()
        for t, p in zip(data["time"], data["profit"])
    ]

    df = pd.DataFrame(all_data)
    df.to_csv("market_data.csv", index=False)
    print(f"Market data saved to disk at {len(df)} entries.")

    df_wallet = pd.DataFrame(wallet)
    df_wallet.to_csv("wallet_data.csv", index=False)
    print(f"Wallet data saved to disk at {len(df_wallet)} entries.")


async def data_generator():
    print("Starting bot")
    i = 0
    while True:
        try:
            await bot()
        except Exception as e:
            print("Exception: ", e)

        # Save the database to disk periodically (every `save_frequency` entries)
        if i % save_frequency == 0:
            # Convert to DataFrame
            save_data()

        i += 1
        await asyncio.sleep(wait_time)


# Dash callback to update the graph
@app.callback(
    [Output('live-graph', 'figure'),
     Output('wallet-graph', 'figure')],
    Input('interval-component', 'n_intervals')
)
def update_graph(n_intervals):
    global max_length_achieved
    figure = go.Figure()
    if len(market_data[symbols[0]]['time']) < max_length:
        return figure, go.Figure()

    for symbol in symbols:
        figure.add_trace(go.Scatter(
            x=market_data[symbol]['time'][-max_length:],
            y=market_data[symbol]['profit'][-max_length:],
            mode='lines+markers',
            name=symbol  # Legend
        ))

    figure.update_layout(
        title=f'Profit for Cryptos Across Markets',
        xaxis_title='Date',
        yaxis_title='Profit in USD',
        legend_title='Exchange',
        template='plotly',
    )

    # Create the figure for the wallet data
    wallet_figure = go.Figure()

    # Plot the wallet data
    wallet_figure.add_trace(go.Scatter(
        x=wallet['time'][-max_length:],
        y=wallet['value'][-max_length:],
        mode='lines+markers',
        name='Wallet',
    ))

    wallet_figure.update_layout(
        title='Wallet Value Over Time',
        xaxis_title='Date',
        yaxis_title='Wallet Value in USD',
        legend_title='Wallet',
        template='plotly',
        xaxis=dict(type='category')  # Change this if necessary
    )
    return figure, wallet_figure

# Start the async loop in a separate thread
def start_data_generation_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(data_generator())


def run_server():
    app.run_server(debug=True, use_reloader=False)

def check_ready():
    while True:
        print(f"{datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')}: Waiting for sufficient amount of data.")
        if len(market_data[symbols[0]]['time']) >= max_length:
            print('Open http://localhost:8050/')
            return
        time.sleep(wait_time)


if __name__ == '__main__':
    # Create the threads
    thread1 = threading.Thread(target=start_data_generation_loop)
    thread2 = threading.Thread(target=run_server)
    thread3 = threading.Thread(target=check_ready)

    # Start the threads
    thread1.start()
    thread2.start()
    thread3.start()