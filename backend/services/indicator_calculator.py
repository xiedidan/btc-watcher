"""
Technical Indicator Calculator Service
Calculates technical indicators from OHLCV data using ta library
"""
from typing import Dict, List, Any, Optional
import pandas as pd
import ta
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class IndicatorCalculator:
    """Technical indicator calculation service"""

    def __init__(self):
        """Initialize indicator calculator"""
        pass

    def calculate_ma(
        self,
        ohlcv_data: List[List],
        periods: List[int] = [5, 10, 20, 30]
    ) -> Dict[str, Any]:
        """
        Calculate Moving Averages (MA)

        Args:
            ohlcv_data: OHLCV data [[timestamp, open, high, low, close, volume], ...]
            periods: List of MA periods to calculate

        Returns:
            Dictionary with MA values and parameters
        """
        try:
            # Convert to DataFrame
            df = self._ohlcv_to_dataframe(ohlcv_data)

            # Calculate MAs
            ma_values = {}
            for period in periods:
                ma_key = f"ma{period}"
                df[ma_key] = ta.trend.sma_indicator(df['close'], window=period)
                # 返回完整数组，前端需要绘制完整的MA线
                ma_values[ma_key] = df[ma_key].bfill().tolist()

            result = {
                "indicator_type": "MA",
                "indicator_params": {"periods": periods},
                "indicator_values": ma_values,
                "values": ma_values,  # 添加values字段，与前端期望的格式一致
                "timestamp": self._get_latest_timestamp(ohlcv_data)
            }

            logger.info(f"Calculated MA for periods {periods}, returned {len(ma_values)} arrays with {len(ma_values.get('ma5', []))} data points each")
            return result

        except Exception as e:
            logger.error(f"Failed to calculate MA: {e}")
            raise

    def calculate_macd(
        self,
        ohlcv_data: List[List],
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9
    ) -> Dict[str, Any]:
        """
        Calculate MACD (Moving Average Convergence Divergence)

        Args:
            ohlcv_data: OHLCV data
            fast_period: Fast EMA period
            slow_period: Slow EMA period
            signal_period: Signal line period

        Returns:
            Dictionary with MACD, signal, and histogram values
        """
        try:
            # Convert to DataFrame
            df = self._ohlcv_to_dataframe(ohlcv_data)

            # Calculate MACD
            macd_indicator = ta.trend.MACD(
                df['close'],
                window_fast=fast_period,
                window_slow=slow_period,
                window_sign=signal_period
            )

            macd_line = macd_indicator.macd()
            signal_line = macd_indicator.macd_signal()
            histogram = macd_indicator.macd_diff()

            # 返回完整数组供前端绘制
            macd_values = {
                "macd": macd_line.bfill().tolist(),
                "signal": signal_line.bfill().tolist(),
                "histogram": histogram.fillna(0).tolist()
            }

            result = {
                "indicator_type": "MACD",
                "indicator_params": {
                    "fast_period": fast_period,
                    "slow_period": slow_period,
                    "signal_period": signal_period
                },
                "indicator_values": macd_values,
                "values": macd_values,  # 添加values字段
                "timestamp": self._get_latest_timestamp(ohlcv_data)
            }

            logger.debug(f"Calculated MACD ({fast_period}, {slow_period}, {signal_period})")
            return result

        except Exception as e:
            logger.error(f"Failed to calculate MACD: {e}")
            raise

    def calculate_rsi(
        self,
        ohlcv_data: List[List],
        period: int = 14
    ) -> Dict[str, Any]:
        """
        Calculate RSI (Relative Strength Index)

        Args:
            ohlcv_data: OHLCV data
            period: RSI period

        Returns:
            Dictionary with RSI value
        """
        try:
            # Convert to DataFrame
            df = self._ohlcv_to_dataframe(ohlcv_data)

            # Calculate RSI
            rsi = ta.momentum.rsi(df['close'], window=period)

            # 返回完整数组
            rsi_values = {
                "rsi": rsi.bfill().tolist()
            }

            result = {
                "indicator_type": "RSI",
                "indicator_params": {"period": period},
                "indicator_values": rsi_values,
                "values": rsi_values,  # 添加values字段
                "timestamp": self._get_latest_timestamp(ohlcv_data)
            }

            logger.debug(f"Calculated RSI ({period})")
            return result

        except Exception as e:
            logger.error(f"Failed to calculate RSI: {e}")
            raise

    def calculate_bollinger_bands(
        self,
        ohlcv_data: List[List],
        period: int = 20,
        std_dev: int = 2
    ) -> Dict[str, Any]:
        """
        Calculate Bollinger Bands

        Args:
            ohlcv_data: OHLCV data
            period: MA period
            std_dev: Standard deviation multiplier

        Returns:
            Dictionary with upper, middle, and lower band values
        """
        try:
            # Convert to DataFrame
            df = self._ohlcv_to_dataframe(ohlcv_data)

            # Calculate Bollinger Bands
            bb_indicator = ta.volatility.BollingerBands(
                df['close'],
                window=period,
                window_dev=std_dev
            )

            upper_band = bb_indicator.bollinger_hband()
            middle_band = bb_indicator.bollinger_mavg()
            lower_band = bb_indicator.bollinger_lband()

            # 返回完整数组
            boll_values = {
                "upper": upper_band.bfill().tolist(),
                "middle": middle_band.bfill().tolist(),
                "lower": lower_band.bfill().tolist()
            }

            result = {
                "indicator_type": "BOLL",
                "indicator_params": {
                    "period": period,
                    "std_dev": std_dev
                },
                "indicator_values": boll_values,
                "values": boll_values,  # 添加values字段
                "timestamp": self._get_latest_timestamp(ohlcv_data)
            }

            logger.debug(f"Calculated Bollinger Bands ({period}, {std_dev})")
            return result

        except Exception as e:
            logger.error(f"Failed to calculate Bollinger Bands: {e}")
            raise

    def calculate_volume(
        self,
        ohlcv_data: List[List]
    ) -> Dict[str, Any]:
        """
        Calculate Volume indicators

        Args:
            ohlcv_data: OHLCV data

        Returns:
            Dictionary with volume value
        """
        try:
            # Get latest volume
            latest_volume = ohlcv_data[-1][5] if len(ohlcv_data) > 0 else None

            # Convert to DataFrame for volume MA
            df = self._ohlcv_to_dataframe(ohlcv_data)

            # Calculate Volume MA (20 period)
            volume_ma = df['volume'].rolling(window=20).mean()

            result = {
                "indicator_type": "VOL",
                "indicator_params": {},
                "indicator_values": {
                    "volume": float(latest_volume) if latest_volume is not None else None,
                    "volume_ma20": float(volume_ma.iloc[-1]) if not volume_ma.isna().iloc[-1] else None
                },
                "timestamp": self._get_latest_timestamp(ohlcv_data)
            }

            logger.debug("Calculated Volume indicators")
            return result

        except Exception as e:
            logger.error(f"Failed to calculate Volume: {e}")
            raise

    def calculate_all_indicators(
        self,
        ohlcv_data: List[List],
        ma_periods: List[int] = [5, 10, 20, 30],
        macd_params: Optional[Dict[str, int]] = None,
        rsi_period: int = 14,
        bb_params: Optional[Dict[str, int]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Calculate all supported indicators

        Args:
            ohlcv_data: OHLCV data
            ma_periods: MA periods to calculate
            macd_params: MACD parameters (fast, slow, signal)
            rsi_period: RSI period
            bb_params: Bollinger Bands parameters (period, std_dev)

        Returns:
            Dictionary with all indicator results
        """
        try:
            # Set default parameters
            if macd_params is None:
                macd_params = {"fast_period": 12, "slow_period": 26, "signal_period": 9}

            if bb_params is None:
                bb_params = {"period": 20, "std_dev": 2}

            # Calculate all indicators
            results = {
                "MA": self.calculate_ma(ohlcv_data, ma_periods),
                "MACD": self.calculate_macd(
                    ohlcv_data,
                    macd_params["fast_period"],
                    macd_params["slow_period"],
                    macd_params["signal_period"]
                ),
                "RSI": self.calculate_rsi(ohlcv_data, rsi_period),
                "BOLL": self.calculate_bollinger_bands(
                    ohlcv_data,
                    bb_params["period"],
                    bb_params["std_dev"]
                ),
                "VOL": self.calculate_volume(ohlcv_data)
            }

            logger.info("Calculated all indicators successfully")
            return results

        except Exception as e:
            logger.error(f"Failed to calculate all indicators: {e}")
            raise

    def _ohlcv_to_dataframe(self, ohlcv_data: List[List]) -> pd.DataFrame:
        """
        Convert OHLCV data to pandas DataFrame

        Args:
            ohlcv_data: OHLCV data [[timestamp, open, high, low, close, volume], ...]

        Returns:
            pandas DataFrame with OHLCV columns
        """
        df = pd.DataFrame(
            ohlcv_data,
            columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
        )

        # Convert timestamp to datetime
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')

        # Set datetime as index
        df.set_index('datetime', inplace=True)

        return df

    def _get_latest_timestamp(self, ohlcv_data: List[List]) -> datetime:
        """
        Get latest timestamp from OHLCV data

        Args:
            ohlcv_data: OHLCV data

        Returns:
            Latest timestamp as datetime
        """
        if len(ohlcv_data) > 0:
            timestamp_ms = ohlcv_data[-1][0]
            return datetime.fromtimestamp(timestamp_ms / 1000)
        else:
            return datetime.now()


def get_indicator_calculator() -> IndicatorCalculator:
    """
    Factory function for IndicatorCalculator

    Returns:
        IndicatorCalculator instance
    """
    return IndicatorCalculator()
