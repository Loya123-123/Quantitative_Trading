# coding:utf-8
from typing import Dict

import numpy as np
import pandas as pd
from xtquant import xtdata


class MarketDataHandler:
    def __init__(self):
        self.code_list = xtdata.get_stock_list_in_sector('T0')

    def get_df_ex(self, data: Dict, field: str) -> pd.DataFrame:
        """将行情数据转换为DataFrame"""
        _index = data[list(data.keys())[0]].index.tolist()
        _columns = list(data.keys())
        df = pd.DataFrame(index=_index, columns=_columns)
        for i in _columns:
            df[i] = data[i][field]
        return df

    def calculate_volatility(self, symbol: str, window: int = 50) -> Dict:
        """计算波动率分数"""
        data = xtdata.get_market_data_ex([], [symbol], period='5m', count=100)
        bars_close = self.get_df_ex(data, "close")
        bars_close.columns = ['close']
        bars_high = self.get_df_ex(data, "high")
        bars_high.columns = ['high']
        bars_low = self.get_df_ex(data, "low")
        bars_low.columns = ['low']
        bars_volume = self.get_df_ex(data, "volume")
        bars_volume.columns = ['volume']
        bars_pre_close = self.get_df_ex(data, "preClose")
        bars_pre_close.columns = ['preClose']

        bars = pd.concat([bars_close, bars_volume, bars_pre_close, bars_high, bars_low], axis=1)

        # 计算真实波幅(TR)
        bars['tr1'] = bars['high'] - bars['low']
        bars['tr2'] = abs(bars['high'] - bars['preClose'])
        bars['tr3'] = abs(bars['low'] - bars['preClose'])
        bars['tr'] = bars[['tr1', 'tr2', 'tr3']].max(axis=1)
        bars['atr'] = bars['tr'].rolling(14).mean()

        returns = np.log(bars['close'] / bars['preClose'])
        return {
            'symbol': symbol,
            'volatility': returns.std() * 100,
            'spread': bars['atr'].mean() * 1000,
            'volume': bars['volume'].mean()
        }

    def select_etfs(self, etf_list: list, top_n: int = 50) -> Dict:
        """选择最适合网格交易的ETF"""
        with ThreadPoolExecutor() as executor:
            results = list(executor.map(self.calculate_volatility, etf_list))

        scored_1 = sorted(results, key=lambda x: x['volatility'], reverse=True)
        scored_2 = sorted(results, key=lambda x: x['volume'], reverse=True)
        scored_3 = sorted(results, key=lambda x: x['spread'], reverse=True)

        etfs_f_volatility = {s['symbol']: round(float(s['volatility']), 0) for s in scored_1}
        etfs_f_volume = {s['symbol']: round(float(s['volume']), 0) for s in scored_2}
        etfs_f_spread = {s['symbol']: round(float(s['spread']), 0) for s in scored_3}

        scored = list(set([x['symbol'] for x in scored_1]) &
                      set([x['symbol'] for x in scored_2]) &
                      set([x['symbol'] for x in scored_3]))

        net_scored = []
        for s in scored_3:
            if s['symbol'] in scored[:top_n]:
                net_scored.append(round(float(s['spread'])))

        return dict(zip(scored[:top_n], net_scored))
