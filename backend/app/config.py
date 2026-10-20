from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    gtex_api_base: str = "https://gtexportal.org/api/v2"
    gtex_dataset_id: str = "gtex_v8"
    msigdb_organism: str = "Human"
    request_timeout: int = 30
    # Minimum number of tissues in which BOTH genes of a pair must be observed
    # for their Pearson r to be computed (env: MIN_OBSERVATIONS). Missing values
    # are never imputed; pairs below this are reported as null and excluded
    # from the pathway score. Pearson r on 2 points is always +/-1, so >= 3.
    min_observations: int = 3

    class Config:
        env_file = ".env"


settings = Settings()
