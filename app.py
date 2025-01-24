import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objs as go
import threading
from datetime import datetime, timedelta

from watch_tickers import start_data_collection, data, exchanges

# Define colors for each exchange
colors = ["blue","green","red","orange", "purple"]
color_to_rgba = {
    "blue": "rgba(0, 0, 255, 0.3)",
    "green": "rgba(0, 255, 0, 0.3)",
    "red": "rgba(255, 0, 0, 0.3)",
    "orange": "rgba(255, 165, 0, 0.3)",
    "purple": "rgba(128, 0, 128, 0.3)"
}
exchange_colors = {ex: color for ex, color in zip(exchanges, colors)}

# Initialize Dash app
app = dash.Dash(__name__)

# Layout
app.layout = html.Div([
    dcc.Dropdown(
        id='pair-dropdown',
        options=[{'label': pair, 'value': pair} for pair in data.keys()],
        value="ETH/USD",
        placeholder="Select Trading Pair"
    ),
    dcc.Graph(id='filled-plot'),
    dcc.Interval(
        id='interval-component',
        interval=2000,  # Update every 2 seconds
        n_intervals=0
    )
])

# Callback to update the plot
@app.callback(
    Output('filled-plot', 'figure'),
    [Input('pair-dropdown', 'value'),
     Input('interval-component', 'n_intervals')]
)
def update_chart(selected_pair, _):
    traces = []

    # Retrieve data for the selected trading pair
    pair_data = data[selected_pair]

    now = datetime.now()

    # Loop through exchanges and create bid/ask fill areas
    for exchange, values in pair_data.items():
        if len(values['datetimes']) == 0:
            continue
        time = [datetime.strptime(dt, '%Y-%m-%d %H:%M:%S') for dt in values['datetimes']]
        bids = values['bids']
        asks = values['asks']

        # Filter data to include only points within the last minute
        last_minute_filter = [(t, b, a) for t, b, a in zip(time, bids, asks) if t >= now - timedelta(minutes=1)]
        if not last_minute_filter:
            continue

        # Unpack filtered data
        time, bids, asks = zip(*last_minute_filter)

        # Get the color for this exchange
        color = exchange_colors.get(exchange, "gray")

        # Add ask line
        traces.append(go.Scatter(
            x=time,
            y=asks,
            mode='lines+markers',
            name=f"{exchange} - Ask",
            line=dict(color=color)
        ))

        # Add bid line
        traces.append(go.Scatter(
            x=time,
            y=bids,
            fill="tonexty",
            mode='lines+markers',
            name=f"{exchange} - Bid",
            line=dict(color=color),
            fillcolor=color_to_rgba.get(color, "rgba(0, 0, 0, 0.3)")
        ))

    # Create the figure
    figure = {
        'data': traces,
        'layout': go.Layout(
            title=f"Bid-Ask Spread for {selected_pair}",
            xaxis={'title': 'Time'},
            yaxis={'title': 'Price'},
            hovermode='x unified',  # Show all hover info at once
        )
    }
    return figure


def run_server():
    app.run_server(debug=True, use_reloader=False)


# Run the app
if __name__ == '__main__':
    thread1 = threading.Thread(target=run_server)
    thread2 = threading.Thread(target=start_data_collection)
    thread1.start()
    thread2.start()

