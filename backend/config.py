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

    # Database
    database_url: str = "postgresql+asyncpg://alphabeta:alphabeta@localhost:5432/alphabeta"
    database_url_sync: str = "postgresql://alphabeta:alphabeta@localhost:5432/alphabeta"

    # JWT Auth
    jwt_secret_key: str = "super-secret-change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # External API keys (v2.0 integrations)
    fmp_api_key: str = ""  # Financial Modeling Prep
    quiver_api_key: str = ""  # Quiver Quantitative
    finnhub_api_key: str = ""  # Finnhub
    benzinga_api_key: str = ""  # Benzinga
    plaid_client_id: str = ""  # Plaid
    plaid_secret: str = ""
    plaid_env: str = "sandbox"  # sandbox | development | production

    model_config = {"env_file": ".env", "env_prefix": "AB_"}


settings = Settings()
