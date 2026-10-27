from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Paper Trail"
    database_url: str = "sqlite:///./paper_trail.db"
    max_text_chars: int = 120000
    top_n_sentences: int = 10

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
