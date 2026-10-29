from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "LinkIntel AI"
    app_env: str = "development"
    host: str = "0.0.0.0"
    port: int = 8000
    database_url: str = "sqlite:///./linkintel.db"
    enable_deep_learning: bool = False
    semantic_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    enable_spam_model: bool = True
    spam_model_path: str = "models/spam_risk.joblib"
    
    # Local Ollama GenAI settings
    enable_ollama_explanations: bool = False
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "gemma3:4b"
    
    # Google Gemini GenAI settings
    enable_gemini_explanations: bool = True
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-flash-latest"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
