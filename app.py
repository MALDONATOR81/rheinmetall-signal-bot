import os
from datetime import datetime, timezone
import requests
import pandas as pd
import yfinance as yf
from indicators import ema, rsi

# --- PING INICIO ---
import os, requests, datetime as dt
def _ping():
    t, c = os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if t and c:
        requests.get(f"https://api.telegram.org/bot{t}/sendMessage",
                     params={"chat_id": c, "text": f"✅ Cron ejecutado {dt.datetime.utcnow().isoformat()}Z"})
# Llama al ping al arrancar:
_ping()
# --- FIN PING ---

# Variables de entorno (en Render las pondrás en Environment)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

TICKERS = [t.strip() for t in os.getenv("TICKERS", "RHM.DE").split(",") if t.strip()]
INTERVAL = os.getenv("INTERVAL", "1h")     # 1m,5m,15m,30m,1h,1d
PERIOD = os.getenv("PERIOD", "60d")
RSI_PERIOD = int(os.getenv("RSI_PERIOD", "14"))
RSI_BUY = float(os.getenv("RSI_BUY", "30"))
RSI_SELL = float(os.getenv("RSI_SELL", "70"))
EMA_SHORT = int(os.getenv("EMA_SHORT", "20"))
EMA_LONG = int(os.getenv("EMA_LONG", "50"))

def fmt_pct(x: float) -> str:
    return f"{x:+.2f}%"

def send_telegram(text: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[WARN] TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID no configurados. Mensaje:\n", text)
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        r = requests.post(url, json=payload, timeout=15)
        if r.status_code != 200:
            print("[ERROR] Telegram status:", r.status_code, r.text)
    except Exception as e:
        print("[ERROR] Envío Telegram:", e)

def get_data(ticker: str) -> pd.DataFrame:
    df = yf.download(tickers=ticker, period=PERIOD, interval=INTERVAL, progress=False, auto_adjust=True)
    if not isinstance(df, pd.DataFrame) or df.empty:
        raise ValueError(f"Datos vacíos para {ticker}")
    return df.dropna().copy()

def build_signals(df: pd.DataFrame):
    close = df["Close"]
    df["EMA_S"] = ema(close, EMA_SHORT)
    df["EMA_L"] = ema(close, EMA_LONG)
    df["RSI"] = rsi(close, RSI_PERIOD)

    if len(df) < max(EMA_LONG, RSI_PERIOD) + 2:
        return None

    last = df.iloc[-1]
    prev = df.iloc[-2]

    signals = []
    if prev["RSI"] < RSI_BUY and last["RSI"] >= RSI_BUY:
        signals.append("BUY_RSI")
    if prev["RSI"] > RSI_SELL and last["RSI"] <= RSI_SELL:
        signals.append("SELL_RSI")

    if prev["EMA_S"] <= prev["EMA_L"] and last["EMA_S"] > last["EMA_L"]:
        signals.append("BUY_EMA")
    if prev["EMA_S"] >= prev["EMA_L"] and last["EMA_S"] < last["EMA_L"]:
        signals.append("SELL_EMA")

    price_now = float(last["Close"])
    price_prev = float(prev["Close"])
    pct = 100.0 * (price_now / price_prev - 1.0)

    return {
        "price_now": price_now,
        "pct_last_bar": pct,
        "rsi_now": float(last["RSI"]),
        "rsi_prev": float(prev["RSI"]),
        "ema_s_now": float(last["EMA_S"]),
        "ema_l_now": float(last["EMA_L"]),
        "signals": signals
    }

def run_for_ticker(ticker: str):
    try:
        df = get_data(ticker)
        info = build_signals(df)
        if not info:
            print(f"[{ticker}] Insuficientes datos para señales.")
            return
        if not info["signals"]:
            print(f"[{ticker}] Sin señales. RSI={info['rsi_now']:.1f}")
            return

        now_ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        lines = [
            f"📈 *{ticker}* | {now_ts}",
            f"Precio: {info['price_now']:.2f}  ({fmt_pct(info['pct_last_bar'])} vs vela anterior)",
            f"RSI: {info['rsi_prev']:.1f} → {info['rsi_now']:.1f}",
            f"EMA{EMA_SHORT}: {info['ema_s_now']:.2f} | EMA{EMA_LONG}: {info['ema_l_now']:.2f}",
            "—"*20
        ]
        for s in info["signals"]:
            if s.startswith("BUY"):
                lines.append("🟢 Señal *BUY*: " + s.replace("_", " "))
            else:
                lines.append("🔴 Señal *SELL*: " + s.replace("_", " "))

        send_telegram("\n".join(lines))

    except Exception as e:
        print(f"[ERROR] {ticker} -> {e}")

def main():
    print(f"[START] Tickers: {TICKERS}  Interval={INTERVAL}  Period={PERIOD}")
    for t in TICKERS:
        run_for_ticker(t)
    print("[DONE]")

if __name__ == "__main__":
    main()

from flask import Flask, request, abort

app = Flask(__name__)

@app.get("/")
def home():
    return {"status": "ok", "service": "rheinmetall-signal-bot"}

@app.post("/tv")
def tv_webhook():
    secret = os.getenv("TV_WEBHOOK_SECRET")
    if secret and request.headers.get("X-TRADINGVIEW-SECRET") != secret:
        abort(401)

    p = request.get_json(silent=True) or {}
    sym = p.get("symbol") or "?"
    price = p.get("price") or "?"
    sig = (p.get("signal") or "ALERTA").upper()
    tf  = p.get("tf") or "?"
    ts  = p.get("time") or ""

    msg = f"🔔 {sym} {sig} @ {price} ({tf})\n⏱ {ts}"
    send_telegram(msg)
    return {"ok": True}

if __name__ == "__main__":
    # si corres localmente
    main()   # ejecuta tu lógica normal
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "10000")))
