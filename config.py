from pydantic_settings import BaseSettings
from pydantic import Field
from datetime import datetime


class Settings(BaseSettings):
    google_client_id: str
    google_client_secret: str
    secret_key: str
    # Comma-separated admin emails. Required for OAuth in production (Cloud Run);
    # if unset in dev, any Google account can sign in for convenience.
    admin_emails: str = ""
    # Comma-separated IPs/CIDRs, or "*" to trust forwarded headers from any client (Cloud Run).
    trusted_proxy_hosts: str = "*"
    url_prefix: str = ""
    host: str = "http://localhost:8000"
    date_format: str = "%-d %B %Y"
    copyright_year: int = Field(default_factory=lambda: datetime.now().year)
    post_path_format: str = "/%(year)d/%(month)02d/%(slug)s"
    posts_per_page: int = 10
    disqus_shortname: str = "thegrandlocus"

    class Config:
        env_file = ".env"


settings = Settings()
