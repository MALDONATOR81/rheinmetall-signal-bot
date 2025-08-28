from dataclasses import dataclass
import pandas as pd
from indicators import ema, rsi, atr

@dataclass
class StrategyConfig:
    ema_fast: int = 20
    ema_slow: int = 50
    rsi_len: int = 14
    rsi_buy_min: float = 45.0
    rsi_buy_max: float = 60.0
    rsi_sell: float = 70.0
    atr_len: int = 14
    risk_tp: float = 1.8
    risk_sl: float = 1.2

class RheinmetallStrategy:
    def __init__(self, cfg: StrategyConfig):
        self.cfg = cfg
        self.position = None  # None / 'long'
        self.entry_price = None
        self.sl = None
        self.tp = None

    def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        out['ema_fast'] = ema(out['Close'], self.cfg.ema_fast)
        out['ema_slow'] = ema(out['Close'], self.cfg.ema_slow)
        out['rsi'] = rsi(out['Close'], self.cfg.rsi_len)
        out['atr'] = atr(out, self.cfg.atr_len)
        return out

    def decide(self, row: pd.Series) -> tuple[str, dict]:
        signal = 'hold'
        info = {}
        price = float(row['Close'])

        if self.position is None:
            if row['ema_fast'] > row['ema_slow'] and self.cfg.rsi_buy_min <= row['rsi'] <= self.cfg.rsi_buy_max:
                atr_val = max(float(row['atr']), 0.01)
                self.position = 'long'
                self.entry_price = price
                self.sl = price - self.cfg.risk_sl * atr_val
                self.tp = price + self.cfg.risk_tp * atr_val
                signal = 'buy'
                info = {
                    'price': price, 'rsi': float(row['rsi']),
                    'ema_fast': float(row['ema_fast']), 'ema_slow': float(row['ema_slow']),
                    'atr': atr_val, 'sl': self.sl, 'tp': self.tp
                }
        else:  # in long
            if price >= self.tp:
                signal = 'sell_tp'
            elif price <= self.sl:
                signal = 'sell_sl'
            elif row['rsi'] >= self.cfg.rsi_sell:
                signal = 'sell_rsi'

            if signal.startswith('sell'):
                info = {'price': price, 'entry': self.entry_price, 'sl': self.sl, 'tp': self.tp, 'rsi': float(row['rsi'])}
                self.position = None
                self.entry_price = self.sl = self.tp = None

        return signal, info
