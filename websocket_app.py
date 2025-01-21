import asyncio
import ccxt.pro as ccxt  # noqa: E402
from itertools import product
import time
from datetime import datetime


async def watch_exchange(exchange, symbols, order_sizes, bids, asks):
    try:
        while True:
            try:
                tickers = await exchange.watch_tickers(symbols)

                for symbol in symbols:
                    bids[symbol][exchange] = tickers[symbol]['bid']
                    asks[symbol][exchange] = tickers[symbol]['ask']

                    combinations = [
                        (b_ex, b_p, a_ex, a_p, b_p - a_p)
                        for (b_ex, b_p), (a_ex, a_p) in product(bids[symbol].items(), asks[symbol].items())
                        if b_ex != a_ex and b_p is not None and a_p is not None
                    ]

                    try:
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
                        if profit > 0:
                            ms = int(time.time() * 1000)
                            print(datetime.fromtimestamp(ms / 1000.0).strftime('%Y-%m-%d %H:%M:%S'))
                            print(f"price profit: {profit}")
                            print(f"bid exchange: {max_exchange}")
                            print(f"ask exchange: {min_exchange}")

                    except Exception as e:
                        print("Exception: ", e)
            except Exception as e:
                print(f"Error with watch ticker: {exchange.name}: {e}")
    except Exception as e:
        print(f"Error with {exchange.name}: {e}")
    finally:
        await exchange.close()

async def main():
    exchanges = [
        ccxt.kraken({'options': {'defaultType': 'spot'}}),
        ccxt.cryptocom({'options': {'defaultType': 'spot'}}),
        ccxt.okx({'options': {'defaultType': 'spot'}})
    ]
    symbols = ['ETH/USD']
    order_sizes = {
        "ETH/USD": 0.01,
    }

    bids = {symbol: {ex: None for ex in exchanges} for symbol in symbols}
    asks = {symbol: {ex: None for ex in exchanges} for symbol in symbols}

    await asyncio.gather(*(watch_exchange(ex, symbols, order_sizes, bids, asks) for ex in exchanges))

asyncio.run(main())
