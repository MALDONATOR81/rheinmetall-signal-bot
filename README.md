# Rheinmetall Signals Bot (Telegram + Render Cron)

Bot que consulta **Rheinmetall (RHM.DE)** (o los tickers que definas) con `yfinance`, calcula **RSI(14)** y **EMA(20/50)** y envía señales **BUY/SELL** a **Telegram** cuando hay cruces en la última vela cerrada.

## Variables de entorno necesarias (en Render → Environment)
- `TELEGRAM_BOT_TOKEN` → token de tu bot (de @BotFather).
- `TELEGRAM_CHAT_ID` → tu chat_id numérico.
- `TICKERS` → ej. `RHM.DE` o `RHM.DE,NOC,PLUG`.
- `INTERVAL` → `30m`, `1h`, `1d`...
- `PERIOD` → `60d`, `1y`...
- `RSI_PERIOD` → normalmente `14`.
- `RSI_BUY` → `30` (o `25` si quieres menos ruido).
- `RSI_SELL` → `70` (o `75` si quieres menos ruido).
- `EMA_SHORT` → `20`.
- `EMA_LONG` → `50`.

## Ejecución local
```bash
pip install -r requirements.txt
python app.py
