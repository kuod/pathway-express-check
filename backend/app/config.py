from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    gtex_api_base: str = "https://gtexportal.org/api/v2"
    gtex_dataset_id: str = "gtex_v8"
    msigdb_organism: str = "Human"
    request_timeout: int = 30

    class Config:
        env_file = ".env"


settings = Settings()
