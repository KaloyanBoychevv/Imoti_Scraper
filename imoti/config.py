from pathlib import Path

BASE_URL = "https://www.imot.bg"
CITY_PATH = "/obiavi/prodazhbi/grad-sofiya"  # sales in Sofia
ENCODING = "cp1251"

# URL slug of the apartment type -> number of rooms (incl. living room)
ROOM_TYPES = {
    "dvustaen": 2,
    "tristaen": 3,
    "chetiristaen": 4,
}

MAX_PER_HOOD = 100
MAX_LIST_PAGES = 50  # safety cap per neighbourhood

# Politeness / retries
DELAY_MIN = 1.0
DELAY_MAX = 2.0
RETRIES = 3
TIMEOUT = 30
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/129.0 Safari/537.36"
)

PROJECT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_DIR / "data" / "imoti.db"
LOG_DIR = PROJECT_DIR / "logs"
