import logging
from app.config.config import settings

# Configure logging format
LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format=LOG_FORMAT,
    filename="app.log",          # <--- writes logs to a file
    filemode="a"                 # append mode ("w" for overwrite each run)
)

logger = logging.getLogger("ai-paper-posts")
