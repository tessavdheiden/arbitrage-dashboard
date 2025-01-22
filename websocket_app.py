import asyncio
import ccxt.pro as ccxt  # noqa: E402
import dash
from dash import dcc, html, Input, Output
import plotly.graph_objs as go
import threading
from itertools import product
import time
from datetime import datetime

# Shared data structures for bids and asks
bids = {}
asks = {}

# Symbols and exchanges
symbols = ['ETH/USD', 'BTC/USD', "LTC/USD"]
exchanges = [
    ccxt.kraken({'options': {'defaultType': 'spot'}}),
    ccxt.cryptocom({'options': {'defaultType': 'spot'}}),
    ccxt.okx({'options': {'defaultType': 'spot'}})
]

# Initialize shared data
for symbol in symbols:
    bids[symbol] = {exchange: None for exchange in exchanges}
    asks[symbol] = {exchange: None for exchange in exchanges}



async def watch_exchange(exchange, symbols, bids, asks):
    try:
        while True:
            try: # Connection to X timed out due to a ping-pong keepalive missing on time
                tickers = await exchange.watch_tickers(symbols)

                for symbol in symbols:
                    if symbol not in tickers.keys():
                        continue

                    bids[symbol][exchange] = tickers[symbol]['bid']
                    asks[symbol][exchange] = tickers[symbol]['ask']
                    # print(f"{exchange.name = }, {symbol = }: {tickers[symbol]['bid']}, {tickers[symbol]['ask']}")

            except Exception as e:
                print(f"Error with watch ticker: {exchange.name}: {e}")
    except Exception as e:
        print(f"Error with {exchange.name}: {e}")
    finally:
        await exchange.close()

# Dash app setup
app = dash.Dash(__name__)

app.layout = html.Div([
    dcc.Dropdown(
        id='symbol-dropdown',
        options=[{'label': symbol, 'value': symbol} for symbol in symbols],
        value='ETH/USD'
    ),
    dcc.Graph(id='bids-asks-graph'),
    dcc.Interval(
        id='interval-component',
        interval=2000,  # Update every 2 seconds
        n_intervals=0
    )
])


@app.callback(
    Output('bids-asks-graph', 'figure'),
    [Input('symbol-dropdown', 'value'),
     Input('interval-component', 'n_intervals')]
)
def update_graph(selected_symbol, _):
    # Create the figure
    figure = go.Figure()

    # Extract data for the selected symbol
    symbol_bids = bids[selected_symbol]
    symbol_asks = asks[selected_symbol]

    # Prepare data for the graph
    exchanges_list = [ex for ex in symbol_bids.keys()]
    bid_values = [symbol_bids[ex] if symbol_bids[ex] else 0 for ex in exchanges_list]
    ask_values = [symbol_asks[ex] if symbol_asks[ex] else 0 for ex in exchanges_list]

    combinations = [
        (b_ex, b_p, a_ex, a_p, b_p - a_p)
        for (b_ex, b_p), (a_ex, a_p) in product(symbol_bids.items(), symbol_asks.items())
        if b_ex != a_ex and b_p is not None and a_p is not None
    ]

    max_exchange, max_price, min_exchange, min_price, price_profit = max(combinations, key=lambda x: x[4])

    figure.add_trace(go.Bar(
        x=[e.name for e in exchanges_list] + [f"best bid/ask: {max_exchange.name}/{min_exchange.name}"],
        y=bid_values + [max_price],
        name='Bids',
        marker_color='blue'
    ))
    figure.add_trace(go.Bar(
        x=[e.name for e in exchanges_list] + [f"best bid/ask: {max_exchange.name}/{min_exchange.name}"],
        y=ask_values + [min_price],
        name='Asks',
        marker_color='red'
    ))

    figure.update_layout(
        title=f'Bids and Asks for {selected_symbol}',
        xaxis_title='Exchange',
        yaxis_title='Price',
        barmode='group'
    )

    return figure


def start_data_collection():
    async def run():
        await asyncio.gather(*(watch_exchange(ex, symbols, bids, asks) for ex in exchanges))

    asyncio.run(run())

def run_server():
    app.run_server(debug=True, use_reloader=False)

# async def main():
#
#     await asyncio.gather(*(watch_exchange(ex, symbols, order_sizes, bids, asks) for ex in exchanges))
#
# asyncio.run(main())

if __name__ == '__main__':
    thread1 = threading.Thread(target=start_data_collection)
    thread2 = threading.Thread(target=run_server)
    thread1.start()
    thread2.start()