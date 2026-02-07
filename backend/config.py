from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    alpaca_api_key: str = ""
    alpaca_api_secret: str = ""
    alpaca_base_url: str = "https://paper-api.alpaca.markets"
    alpaca_data_url: str = "https://data.alpaca.markets"

    # Signal parameters
    rsi_short: int = 5
    rsi_mid: int = 9
    rsi_long: int = 14
    bollinger_period: int = 20
    bollinger_std: float = 2.0
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    macd_zscore_window: int = 252
    macd_zscore_threshold: float = 2.0
    vix_rsi_period: int = 2
    vix_fear_threshold: float = 90.0
    backtest_years: int = 3
    reversal_window_days: int = 5

    # Performance
    thesis_timeout_ms: int = 800

    model_config = {"env_file": ".env", "env_prefix": "AB_"}


settings = Settings()
