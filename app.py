import streamlit as st
import pandas as pd
import ccxt
import time

# === CONFIG ===
TIMEFRAMES = ['1m', '3m', '5m', '10m', '15m', '20m', '30m', '1h', '2h', '4h', '6h', '8h', '10h', '12h', '16h', '1d', '1w']
BITGET = ccxt.bitget()

# === HELPERS ===
def fetch_ohlcv(symbol, timeframe, limit=100):
    try:
        ohlcv = BITGET.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception:
        return None

def check_cradle_setup(df, index):
    ema10 = df['close'].ewm(span=10).mean()
    ema20 = df['close'].ewm(span=20).mean()

    if index < 2 or index >= len(df):
        return None

    prev = df.iloc[index - 1]
    curr = df.iloc[index]

    ema_zone_low = min(ema10.iloc[index - 1], ema20.iloc[index - 1])
    ema_zone_high = max(ema10.iloc[index - 1], ema20.iloc[index - 1])

    # Bullish Cradle
    if prev['close'] < prev['open'] and ema_zone_low <= prev['close'] <= ema_zone_high and curr['close'] > curr['open']:
        return 'Bullish'
    # Bearish Cradle
    if prev['close'] > prev['open'] and ema_zone_low <= prev['close'] <= ema_zone_high and curr['close'] < curr['open']:
        return 'Bearish'
    return None

def analyze_cradle_setups(symbols, timeframes):
    recent_setups = []
    previous_setups = []

    for tf in timeframes:
        for idx, symbol in enumerate(symbols):
            st.info(f"Scanning {symbol} on {tf} ({idx+1}/{len(symbols)})")
            df = fetch_ohlcv(symbol, tf)
            if df is None or len(df) < 5:
                continue

            # Check last two pairs of candles
            setup_latest = check_cradle_setup(df, -1)
            setup_previous = check_cradle_setup(df, -2)

            if setup_latest:
                recent_setups.append({
                    'Symbol': symbol,
                    'Timeframe': tf,
                    'Setup': setup_latest,
                    'Detected On': 'Latest Candle'
                })
            if setup_previous:
                previous_setups.append({
                    'Symbol': symbol,
                    'Timeframe': tf,
                    'Setup': setup_previous,
                    'Detected On': 'Previous Candle'
                })
            time.sleep(0.3)

    return pd.DataFrame(recent_setups), pd.DataFrame(previous_setups)

# === STREAMLIT UI ===
st.set_page_config(layout="wide")
st.title("📊 Cradle Strategy Screener (Last Two Candle Pairs)")

selected_timeframes = st.multiselect("Select Timeframes to Scan", TIMEFRAMES, default=['1h', '4h', '1d'])
st.write("This screener shows valid Cradle setups detected on the last two candles.")

if st.button("Run Screener"):
    with st.spinner("Scanning Bitget markets... Please wait..."):
        markets = BITGET.load_markets()
        symbols = [s for s in markets if '/USDT:USDT' in s and markets[s]['type'] == 'swap']

        latest_df, previous_df = analyze_cradle_setups(symbols, selected_timeframes)

    if not latest_df.empty:
        st.markdown("### 🟢 Cradle Setups (Latest Candle)")
        st.dataframe(latest_df, use_container_width=True)

    if not previous_df.empty:
        st.markdown("### 🟡 Cradle Setups (Previous Candle)")
        st.dataframe(previous_df, use_container_width=True)

    if latest_df.empty and previous_df.empty:
        st.warning("No valid Cradle setups found.")

    st.success("Scan complete!")
