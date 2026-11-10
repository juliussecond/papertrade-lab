import os
import sqlite3
from datetime import datetime, timezone

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

st.set_page_config(page_title="PaperTrade Lab", page_icon="📈", layout="wide")

DB = "papertrade.db"
START_CASH = 10_000.0
FEE = 0.001
SLIPPAGE = 0.0005

def connect():
    return sqlite3.connect(DB, check_same_thread=False)

def setup():
    with connect() as c:
        c.execute("CREATE TABLE IF NOT EXISTS account (id INTEGER PRIMARY KEY, cash REAL)")
        c.execute("""CREATE TABLE IF NOT EXISTS positions
                     (symbol TEXT PRIMARY KEY, qty REAL, avg_price REAL)""")
        c.execute("""CREATE TABLE IF NOT EXISTS trades
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, time TEXT, symbol TEXT,
                      side TEXT, qty REAL, price REAL, fee REAL)""")
        if c.execute("SELECT COUNT(*) FROM account").fetchone()[0] == 0:
            c.execute("INSERT INTO account VALUES (1, ?)", (START_CASH,))

def cash():
    with connect() as c:
        return float(c.execute("SELECT cash FROM account WHERE id=1").fetchone()[0])

def positions():
    with connect() as c:
        rows = c.execute("SELECT symbol, qty, avg_price FROM positions ORDER BY symbol").fetchall()
    return pd.DataFrame(rows, columns=["Symbol", "Stück", "Ø Kaufkurs"])

def trades():
    with connect() as c:
        rows = c.execute("SELECT time, symbol, side, qty, price, fee FROM trades ORDER BY id DESC").fetchall()
    return pd.DataFrame(rows, columns=["Zeit (UTC)", "Symbol", "Seite", "Stück", "Ausführungskurs", "Gebühr"])

@st.cache_data(ttl=60)
def get_prices(symbol, api_key):
    if not api_key:
        return None, "API-Key fehlt."
    try:
        r = requests.get(
            "https://api.twelvedata.com/time_series",
            params={"symbol": symbol, "interval": "1day", "outputsize": 100,
                    "apikey": api_key, "format": "JSON"},
            timeout=15,
        )
        r.raise_for_status()
        j = r.json()
        if "values" not in j:
            return None, j.get("message", "Keine Kursdaten erhalten.")
        d = pd.DataFrame(j["values"])
        d["datetime"] = pd.to_datetime(d["datetime"])
        for col in ["open", "high", "low", "close"]:
            d[col] = pd.to_numeric(d[col], errors="coerce")
        return d.sort_values("datetime").dropna(subset=["close"]), None
    except Exception as e:
        return None, str(e)

def order(symbol, side, qty, price):
    qty = float(qty)
    fill = price * (1 + SLIPPAGE if side == "KAUF" else 1 - SLIPPAGE)
    value = qty * fill
    fee = value * FEE
    current_cash = cash()
    p = positions()
    found = p[p["Symbol"] == symbol]
    with connect() as c:
        if side == "KAUF":
            if value + fee > current_cash:
                raise ValueError("Nicht genug virtuelles Guthaben.")
            if found.empty:
                new_qty, avg = qty, fill
            else:
                old_qty = float(found.iloc[0]["Stück"])
                old_avg = float(found.iloc[0]["Ø Kaufkurs"])
                new_qty = old_qty + qty
                avg = (old_qty * old_avg + qty * fill) / new_qty
            c.execute("UPDATE account SET cash=? WHERE id=1", (current_cash - value - fee,))
            c.execute("""INSERT INTO positions VALUES (?,?,?)
                         ON CONFLICT(symbol) DO UPDATE SET qty=excluded.qty, avg_price=excluded.avg_price""",
                      (symbol, new_qty, avg))
        else:
            if found.empty or float(found.iloc[0]["Stück"]) < qty:
                raise ValueError("Nicht genug virtuelle Stücke zum Verkaufen.")
            old_qty = float(found.iloc[0]["Stück"])
            remaining = old_qty - qty
            c.execute("UPDATE account SET cash=? WHERE id=1", (current_cash + value - fee,))
            if remaining < 1e-8:
                c.execute("DELETE FROM positions WHERE symbol=?", (symbol,))
            else:
                c.execute("UPDATE positions SET qty=? WHERE symbol=?", (remaining, symbol))
        c.execute("INSERT INTO trades(time,symbol,side,qty,price,fee) VALUES(?,?,?,?,?,?)",
                  (datetime.now(timezone.utc).isoformat(timespec="seconds"),
                   symbol, side, qty, fill, fee))

setup()
st.title("📈 PaperTrade Lab")
st.caption("Echte Kursdaten · virtuelles Depot · keine Echtgeld-Orders")

with st.sidebar:
    st.header("Datenquelle")
    api_key = st.text_input("Twelve Data API-Key", type="password",
                            help="Nur lokal eingeben. Für eine veröffentlichte App besser als Secret hinterlegen.")
    symbol = st.text_input("Symbol", "AAPL").strip().upper()
    st.caption("Beispiele: AAPL, MSFT, NVDA, SPY. Verfügbarkeit hängt vom Datenpaket ab.")
    if st.button("Demo-Konto zurücksetzen"):
        with connect() as c:
            c.execute("DELETE FROM positions")
            c.execute("DELETE FROM trades")
            c.execute("UPDATE account SET cash=? WHERE id=1", (START_CASH,))
        st.cache_data.clear()
        st.rerun()

if not symbol:
    st.warning("Bitte ein Börsensymbol eingeben.")
    st.stop()

data, error = get_prices(symbol, api_key)
if data is None or data.empty:
    st.info("Gib links einen Twelve Data API-Key ein, um Marktdaten abzurufen.")
    st.write("Du kannst einen API-Key bei [Twelve Data](https://twelvedata.com/) erhalten. Prüfe dort die aktuellen Tarif- und Nutzungsbedingungen.")
    if error:
        st.caption(f"Status: {error}")
    st.stop()

data["SMA20"] = data["close"].rolling(20).mean()
data["SMA50"] = data["close"].rolling(50).mean()
last = data.iloc[-1]
last_price = float(last["close"])

p = positions()
cash_now = cash()
market_value = 0.0
for _, row in p.iterrows():
    quote, _ = get_prices(row["Symbol"], api_key)
    if quote is not None and not quote.empty:
        market_value += float(row["Stück"]) * float(quote.iloc[-1]["close"])
equity = cash_now + market_value

a, b, c, d = st.columns(4)
a.metric("Virtuelles Gesamtvermögen", f"${equity:,.2f}", f"{equity-START_CASH:+,.2f} $")
b.metric("Virtuelles Guthaben", f"${cash_now:,.2f}")
c.metric(f"{symbol} letzter Datenkurs", f"${last_price:,.2f}")
d.metric("Kurs-Datum", str(last["datetime"]))

st.subheader(f"{symbol} – Kursverlauf")
fig = go.Figure()
fig.add_trace(go.Candlestick(x=data["datetime"], open=data["open"], high=data["high"],
                             low=data["low"], close=data["close"], name="Kurs"))
fig.add_trace(go.Scatter(x=data["datetime"], y=data["SMA20"], name="SMA 20"))
fig.add_trace(go.Scatter(x=data["datetime"], y=data["SMA50"], name="SMA 50"))
fig.update_layout(template="plotly_dark", height=430, xaxis_rangeslider_visible=False,
                  margin=dict(l=5, r=5, t=25, b=5))
st.plotly_chart(fig, use_container_width=True)

st.subheader("Virtueller Order-Bereich")
st.caption("Orders werden nur in der lokalen Demo-Datenbank verbucht. Es gibt keine Verbindung zu einem Broker.")
left, right = st.columns(2)
with left:
    qty = st.number_input("Stückzahl", min_value=0.001, value=1.0, step=1.0)
    st.write(f"Geschätzter Orderwert: **${qty * last_price:,.2f}** (vor Gebühren/Slippage)")
with right:
    st.write(f"Simulierte Gebühr: {FEE*100:.2f}% · Slippage-Annahme: {SLIPPAGE*100:.2f}%")
    buy_col, sell_col = st.columns(2)
    if buy_col.button("Virtuell kaufen", use_container_width=True):
        try:
            order(symbol, "KAUF", qty, last_price)
            st.success("Virtueller Kauf verbucht.")
            st.rerun()
        except ValueError as e:
            st.error(str(e))
    if sell_col.button("Virtuell verkaufen", use_container_width=True):
        try:
            order(symbol, "VERKAUF", qty, last_price)
            st.success("Virtueller Verkauf verbucht.")
            st.rerun()
        except ValueError as e:
            st.error(str(e))

st.subheader("Portfolio")
st.dataframe(p, use_container_width=True, hide_index=True)
st.subheader("Trade-Historie")
t = trades()
if t.empty:
    st.write("Noch keine virtuellen Trades.")
else:
    st.dataframe(t, use_container_width=True, hide_index=True)

st.caption("Hinweis: Kursdaten können verzögert sein und sind nicht zwingend vollständige Echtzeitdaten. Das Demo-Konto ist eine Lernsimulation; Ausführungspreise, Liquidität und Orderbuch werden nicht realistisch nachgebildet.")
