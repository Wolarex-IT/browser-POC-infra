from os import environ

BROWSER_NETWORK = environ.get("BROWSER_NETWORK", "cloak_net")
BROWSER_IMAGE = "cloakhq/cloakbrowser:latest"
CONTAINER_LABEL = "browser-poc-cloak"
CDP_PORT = 9222
CONNECT_RETRIES = 20
CONNECT_DELAY = 2
NAV_TIMEOUT = 15000
NAV_WAIT_UNTIL = "domcontentloaded"
MAX_RENDER_ATTEMPTS = 2
DATABASE_URL = environ.get(
    "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/browser_poc"
)
SYNC_DATABASE_URL = environ.get(
    "SYNC_DATABASE_URL", "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/browser_poc"
)
CELERY_BROKER_URL = environ.get("CELERY_BROKER_URL", "amqp://guest:guest@127.0.0.1:5672//")
RENDER_TASK = "render"
