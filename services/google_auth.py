from authlib.integrations.starlette_client import OAuth
from config import settings

oauth = OAuth()

oauth.register(
    name="google",
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_id=settings.google_client_id,
    client_secret=settings.google_client_secret,
    client_kwargs={"scope": "openid email profile"},
)


def refresh_google_token():
    # Token refresh logic here
    pass
