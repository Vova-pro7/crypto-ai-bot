import numpy as np
from dataclasses import dataclass
from typing import List, Dict
from enum import Enum
import aiohttp
import logging

logger = logging.getLogger(__name__)

class TimeFrame(Enum):
    M1 = "1"
    M5 = "5"
    M15 = "15"
    M30 = "30"
    H1 = "60"
    H4 = "240"
    D1 = "D"
    W1 = "W"

@dataclass
class SignalConfidence:
    signal: str
    confidence: float
    rsi_signal: str
    ma_signal: str
    alligator_signal: str
    details: str

class ConfluenceAnalyzer:
    @staticmethod
    def analyze_confluence(rsi: float, ma_trend: str, alligator_trend: str, price_vs_ma: str) -> SignalConfidence:
        buy_votes = 0
        sell_votes = 0
        total_votes = 4
        
        if rsi < 30:
            buy_votes += 1
            rsi_signal = "🟢 RSI: Oversold (BUY)"
        elif rsi > 70:
            sell_votes += 1
            rsi_signal = "🔴 RSI: Overbought (SELL)"
        else:
            rsi_signal = "➡️ RSI: Neutral"
        
        if ma_trend == "BULLISH":
            buy_votes += 1
            ma_signal = "🟢 MA: Uptrend (BUY)"
        elif ma_trend == "BEARISH":
            sell_votes += 1
            ma_signal = "🔴 MA: Downtrend (SELL)"
        else:
            ma_signal = "➡️ MA: Sideways"
        
        if alligator_trend == "BULLISH":
            buy_votes += 1
            alligator_signal = "🟢 Alligator: Bullish (BUY)"
        elif alligator_trend == "BEARISH":
            sell_votes += 1
            alligator_signal = "🔴 Alligator: Bearish (SELL)"
        else:
            alligator_signal = "➡️ Alligator: Neutral"
        
        if price_vs_ma == "ABOVE":
            buy_votes += 1
            price_signal = "🟢 Price > MA200 (BUY)"
        elif price_vs_ma == "BELOW":
            sell_votes += 1
            price_signal = "🔴 Price < MA200 (SELL)"
        else:
            price_signal = "➡️ Price ≈ MA200"
        
        if buy_votes > sell_votes:
            signal = "🟢 BUY"
        elif sell_votes > buy_votes:
            signal = "🔴 SELL"
        else:
            signal = "➡️ HOLD"
        
        max_votes = max(buy_votes, sell_votes)
        confidence = (max_votes / total_votes) * 100
        
        details = f"""
{rsi_signal}
{ma_signal}
{alligator_signal}
{price_signal}

📊 Confluence: {max_votes}/{total_votes}
"""
        
        return SignalConfidence(signal=signal, confidence=confidence, rsi_signal=rsi_signal, ma_signal=ma_signal, alligator_signal=alligator_signal, details=details)

class MultiTimeframeAnalyzer:
    def __init__(self):
        self.bybit_url = "https://api.bybit.com/v5/market"
        self.confluence = ConfluenceAnalyzer()
    
    async def get_klines(self, symbol: str, interval: str, limit: int = 100) -> List[dict]:
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.bybit_url}/kline"
                params = {'category': 'spot', 'symbol': f'{symbol}USDT', 'interval': interval, 'limit': limit}
                
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        klines = []
                        if data.get('result', {}).get('list'):
                            for k in reversed(data['result']['list']):
                                klines.append({'time': int(k[0]), 'open': float(k[1]), 'high': float(k[2]), 'low': float(k[3]), 'close': float(k[4]), 'volume': float(k[5])})
                        return klines
        except Exception as e:
            logger.error(f"Error: {e}")
        return []
    
    @staticmethod
    def calculate_rsi(prices: List[float], period: int = 14) -> float:
        if len(prices) < period + 1:
            return None
        prices = np.array(prices[-period-1:], dtype=float)
        deltas = np.diff(prices)
        seed = deltas[:period]
        up = seed[seed >= 0].sum() / period
        down = -seed[seed < 0].sum() / period
        rs = up / down if down else 0
        rsi = 100 - (100 / (1 + rs)) if down else 100
        for delta in deltas[period:]:
            if delta >= 0:
                up = (up * (period - 1) + delta) / period
                down = down * (period - 1) / period
            else:
                up = up * (period - 1) / period
                down = (-delta * (period - 1) + down) / period
            rs = up / down if down else 0
            rsi = 100 - (100 / (1 + rs))
        return round(rsi, 2)
    
    @staticmethod
    def calculate_ma(prices: List[float], period: int) -> float:
        if len(prices) < period:
            return None
        return round(np.mean(prices[-period:]), 2)
    
    def analyze_single_timeframe(self, klines: List[dict], tf_name: str) -> Dict:
        if len(klines) < 50:
            return None
        closes = [k['close'] for k in klines]
        highs = [k['high'] for k in klines]
        lows = [k['low'] for k in klines]
        current_price = closes[-1]
        rsi = self.calculate_rsi(closes)
        ma20 = self.calculate_ma(closes, 20)
        ma50 = self.calculate_ma(closes, 50)
        ma200 = self.calculate_ma(closes, 200)
        if ma20 and ma50:
            ma_trend = "BULLISH" if ma20 > ma50 else "BEARISH" if ma20 < ma50 else "NEUTRAL"
        else:
            ma_trend = "NEUTRAL"
        hl_avg = [(highs[i] + lows[i]) / 2 for i in range(len(highs))]
        jaw = np.mean(hl_avg[-13:]) if len(hl_avg) >= 13 else None
        teeth = np.mean(hl_avg[-8:]) if len(hl_avg) >= 8 else None
        lips = np.mean(hl_avg[-5:]) if len(hl_avg) >= 5 else None
        if jaw and teeth and lips:
            alligator_trend = "BULLISH" if jaw > teeth > lips else "BEARISH" if jaw < teeth < lips else "NEUTRAL"
        else:
            alligator_trend = "NEUTRAL"
        if ma200:
            price_vs_ma = "ABOVE" if current_price > ma200 else "BELOW" if current_price < ma200 else "EQUAL"
        else:
            price_vs_ma = "EQUAL"
        confluence = self.confluence.analyze_confluence(rsi, ma_trend, alligator_trend, price_vs_ma)
        return {'timeframe': tf_name, 'price': current_price, 'rsi': rsi, 'ma20': ma20, 'ma50': ma50, 'ma200': ma200, 'ma_trend': ma_trend, 'alligator_trend': alligator_trend, 'confluence': confluence}
    
    async def multi_timeframe_analysis(self, symbol: str) -> str:
        timeframes = [(TimeFrame.M5, "📱 5 хв"), (TimeFrame.M15, "📊 15 хв"), (TimeFrame.M30, "📈 30 хв"), (TimeFrame.H1, "🕐 1 година"), (TimeFrame.H4, "⏰ 4 години"), (TimeFrame.D1, "📅 1 день")]
        results = []
        message = f"<b>🔍 Мультітаймфрейм аналіз {symbol}</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        for tf_enum, tf_label in timeframes:
            try:
                klines = await self.get_klines(symbol, tf_enum.value, limit=200)
                if not klines:
                    continue
                analysis = self.analyze_single_timeframe(klines, tf_label)
                if analysis:
                    results.append(analysis)
                    conf = analysis['confluence']
                    message += f"{tf_label}\n├─ Ціна: <code>${analysis['price']:,.2f}</code>\n├─ RSI: <code>{analysis['rsi']}</code>\n├─ MA20/50/200: <code>${analysis['ma20']:.2f} / ${analysis['ma50']:.2f} / ${analysis['ma200']:.2f}</code>\n├─ Signal: <b>{conf.signal}</b>\n└─ Confidence: <b>{conf.confidence:.0f}%</b> 📊\n\n"
            except Exception as e:
                logger.error(f"Error: {e}")
                continue
        if results:
            strongest = max(results, key=lambda x: x['confluence'].confidence)
            message += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n<b>🎯 Найсильніший сигнал:</b>\nТаймфрейм: <b>{strongest['timeframe']}</b>\nСигнал: <b>{strongest['confluence'].signal}</b>\nВпевненість: <b>{strongest['confluence'].confidence:.0f}%</b>\n\n<b>Деталі:</b>\n{strongest['confluence'].details}"
        else:
            message += "❌ Не вдалось аналізувати"
        return message
    
    async def quick_scan(self, symbol: str) -> str:
        timeframes = [(TimeFrame.M15, "15 хв"), (TimeFrame.H1, "1 год"), (TimeFrame.D1, "1 день")]
        message = f"<b>⚡ Швидкий скан {symbol}</b>\n━━━━━━━━━━━\n"
        for tf_enum, tf_label in timeframes:
            try:
                klines = await self.get_klines(symbol, tf_enum.value, limit=200)
                analysis = self.analyze_single_timeframe(klines, tf_label)
                if analysis:
                    conf = analysis['confluence']
                    message += f"{tf_label}: {conf.signal} ({conf.confidence:.0f}%)\n"
            except:
                continue
        return message
