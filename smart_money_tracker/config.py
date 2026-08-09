import os

from dotenv import load_dotenv

load_dotenv()

# SEC EDGAR требует identity в виде "Имя email@example.com" в каждом запросе
# (fair access policy: https://www.sec.gov/os/webmaster-faq#developers).
# Без него запросы будут отклоняться.
EDGAR_IDENTITY = os.environ.get("EDGAR_IDENTITY", "")

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
