"""
Fofoqueiro – Configuração central
"""
import os
import json
from dotenv import load_dotenv

load_dotenv()

# ── Paths ──────────────────────────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(PROJECT_ROOT, "fofoqueiro.db")
USER_FEEDS_PATH = os.path.join(PROJECT_ROOT, "user_feeds.json")

# ── 9router (OpenAI-compatible) ────────────────────────────────────────
NINEROUTER_BASE_URL = os.getenv("NINEROUTER_BASE_URL", "http://127.0.0.1:20128/v1")
NINEROUTER_API_KEY  = os.getenv("NINEROUTER_API_KEY", "")
NINEROUTER_MODEL    = os.getenv("NINEROUTER_MODEL", "free")

# ── Default subreddits (the user can add more via UI / user_feeds.json) ──
DEFAULT_SUBREDDITS = ["linux", "netsec", "programming", "technology"]

# ── Hacker News ────────────────────────────────────────────────────────
HN_TOP_STORIES_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_ITEM_URL        = "https://hacker-news.firebaseio.com/v0/item/{}.json"
HN_FETCH_LIMIT     = 30  # quantos top stories buscar por ciclo

# ── Linux Kernel CVE / Security Advisories ─────────────────────────────
# Feeds RSS oficiais de distribuidores e kernel
CVE_FEEDS = [
    "https://ubuntu.com/security/notices/rss.xml",                # Canonical (Ubuntu Security Notices - USN)
    "https://access.redhat.com/security/data/metrics/rhsa.rss",   # Red Hat (RHSA)
    "https://alas.aws.amazon.com/AL2023/alas.rss",                # Amazon Linux 2023 (ALAS)
    "https://www.kernel.org/feeds/kdist.xml",                     # Linux Kernel Releases
    "https://www.cisa.gov/cybersecurity-advisories/all.xml",      # CISA Advisories
]

# ── LWN.net ───────────────────────────────────────────────────────────────
LWN_RSS_URL = "https://lwn.net/headlines/rss"

# ── Theme keywords para linux-cve-announce (filtros de relevância) ────────
THEME_KEYWORDS = [
    "drm", "gpu", "i3c", "cxl", "mdio", "vc4", "panthor",
    "clk", "plat-dma", "pwm", "regulator", "gpio",
    "usb", "ssusb", "xhci", "dwc3",
    "net", "ipv6", "llc", "clustering",
    "sched", "fair", "tick", "irq", "preempt",
    "pci", "acpi", "firmware", "uefi",
]

# ── Scheduler ──────────────────────────────────────────────────────────
WORKER_INTERVAL_MINUTES = 60  # a cada 1 hora

# ── Streamlit ──────────────────────────────────────────────────────────
STREAMLIT_PAGE_TITLE = "Fofoqueiro – Agregador de Inteligência & Notícias"
STREAMLIT_PAGE_ICON  = "📰"

# ── Helpers ────────────────────────────────────────────────────────────
def load_user_subreddits() -> list[str]:
    """Carrega subreddits extras definidos pelo usuário em user_feeds.json."""
    if os.path.exists(USER_FEEDS_PATH):
        with open(USER_FEEDS_PATH, "r") as f:
            data = json.load(f)
            return data.get("subreddits", [])
    return []

def save_user_subreddits(subreddits: list[str]):
    """Persiste a lista de subreddits do usuário."""
    data = {}
    if os.path.exists(USER_FEEDS_PATH):
        with open(USER_FEEDS_PATH, "r") as f:
            data = json.load(f)
    data["subreddits"] = sorted(set(subreddits))
    with open(USER_FEEDS_PATH, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_all_subreddits() -> list[str]:
    """Retorna subreddits default + os do usuário, sem duplicatas."""
    extras = load_user_subreddits()
    return sorted(set(DEFAULT_SUBREDDITS + extras))
