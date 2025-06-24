from pydantic_settings import BaseSettings
from pydantic import Field
from datetime import datetime


class Settings(BaseSettings):
    google_client_id: str
    google_client_secret: str
    secret_key: str
    url_prefix: str = ""
    host: str = "http://localhost:8000"
    date_format: str = "%d %B %Y"
    copyright_year: int = Field(default_factory=lambda: datetime.now().year)
    post_path_format: str = "/%(year)d/%(month)02d/%(slug)s"
    disqus_shortname: str = "thegrandlocus"

    class Config:
        env_file = ".env"


settings = Settings()
