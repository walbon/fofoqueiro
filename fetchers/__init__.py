"""
Fofoqueiro - Extratores de Conteúdo (Paralelizados)
"""
import httpx
import feedparser
from bs4 import BeautifulSoup
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import re

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Fofoqueiro/1.0"

def extract_body_snippet(url: str, max_words: int = 200, max_chars: int | None = None) -> str:
    """Acessa a URL da notícia e extrai o corpo de texto limpo (até max_words).

    Usa max_words por padrão (200). Opcionalmente limita por max_chars
    (mantido por compatibilidade com chamadas antigas)."""
    if not url or not url.startswith("http") or "ycombinator.com" in url or "reddit.com" in url:
        return ""
    try:
        headers = {"User-Agent": USER_AGENT}
        with httpx.Client(timeout=5.0, follow_redirects=True, headers=headers) as client:
            resp = client.get(url)
            if resp.status_code != 200:
                return ""
            soup = BeautifulSoup(resp.text, "html.parser")
            for tag in soup(["script", "style", "nav", "header", "footer", "aside", "noscript", "form"]):
                tag.decompose()

            paragraphs = [p.get_text(strip=True) for p in soup.find_all("p") if len(p.get_text(strip=True)) > 30]
            full_text = " ".join(paragraphs)
            if not full_text:
                return ""
            words = full_text.split()
            if len(words) > max_words:
                full_text = " ".join(words[:max_words]) + "..."
            if max_chars is not None and len(full_text) > max_chars:
                full_text = full_text[:max_chars].strip() + "..."
            return full_text
    except Exception:
        pass
    return ""

class BaseFetcher:
    source_name = "unknown"
    def fetch(self) -> list[dict]:
        raise NotImplementedError

class HNFetcher(BaseFetcher):
    source_name = "hackernews"
    def __init__(self, top_url: str, item_url: str, limit: int = 30):
        self.top_url = top_url
        self.item_url = item_url
        self.limit = limit

    def _fetch_single_item(self, client: httpx.Client, item_id: int) -> dict | None:
        try:
            ir = client.get(self.item_url.format(item_id))
            if ir.status_code == 200:
                data = ir.json()
                if data and data.get("type") == "story" and not data.get("deleted"):
                    link = data.get("url") or f"https://news.ycombinator.com/item?id={item_id}"
                    ts = data.get("time", 0)
                    pub_at = datetime.utcfromtimestamp(ts).isoformat() if ts else datetime.utcnow().isoformat()
                    
                    # Tenta extrair trecho diretamente da página externa se for link válido
                    snippet = extract_body_snippet(link, max_chars=250) if data.get("url") else data.get("text", "")

                    return {
                        "id": f"hn_{item_id}",
                        "source": self.source_name,
                        "title": data.get("title", ""),
                        "link": link,
                        "summary": snippet,
                        "tabcoins": data.get("score", 0),
                        "comment_count": data.get("descendants", 0),
                        "published_at": pub_at
                    }
        except Exception:
            pass
        return None

    def fetch(self) -> list[dict]:
        results = []
        try:
            headers = {"User-Agent": USER_AGENT}
            with httpx.Client(timeout=15.0, headers=headers) as client:
                r = client.get(self.top_url)
                r.raise_for_status()
                top_ids = r.json()[:self.limit]
                
                # Fetch HN items in parallel
                with ThreadPoolExecutor(max_workers=10) as executor:
                    futures = [executor.submit(self._fetch_single_item, client, item_id) for item_id in top_ids]
                    for future in as_completed(futures):
                        res = future.result()
                        if res:
                            results.append(res)
        except Exception as e:
            print(f"[Fetchers] Erro HackerNews: {e}")
        return results

class RedditFetcher(BaseFetcher):
    source_name = "reddit"
    def __init__(self, subreddits: list[str]):
        self.subreddits = subreddits

    def _fetch_sub(self, sub: str) -> list[dict]:
        sub_results = []
        url = f"https://www.reddit.com/r/{sub}/hot.rss"
        headers = {'User-Agent': f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Fofoqueiro/{sub}"}
        try:
            with httpx.Client(timeout=15.0, headers=headers) as client:
                r = client.get(url, follow_redirects=True)
                r.raise_for_status()
            
            feed = feedparser.parse(r.text)
            for entry in feed.entries[:10]:
                sub_results.append({
                    "id": f"rd_{entry.id.split('_')[-1]}",
                    "source": self.source_name,
                    "category": f"r/{sub}",
                    "title": entry.title,
                    "link": entry.link,
                    "summary": entry.get("summary", ""),
                    "published_at": datetime(*entry.published_parsed[:6]).isoformat() if hasattr(entry, "published_parsed") and entry.published_parsed else datetime.utcnow().isoformat()
                })
        except Exception as e:
            print(f"[Fetchers] Erro Reddit r/{sub}: {e}")
        return sub_results

    def fetch(self) -> list[dict]:
        results = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(self._fetch_sub, sub) for sub in self.subreddits]
            for future in as_completed(futures):
                results.extend(future.result())
        return results

class CVEFetcher(BaseFetcher):
    source_name = "cve"
    def __init__(self, urls: list[str], theme_keywords: list | None = None):
        self.urls = urls
        self.theme_keywords = theme_keywords or []

    def _matches_theme(self, title: str, summary: str) -> bool:
        """Retorna True se algum keyword aparecer no título ou resumo."""
        if not self.theme_keywords:
            return True
        text = (title + " " + summary).lower()
        return any(kw.lower() in text for kw in self.theme_keywords)

    def _fetch_url(self, url: str) -> list[dict]:
        cve_results = []
        headers = {"User-Agent": USER_AGENT}
        try:
            with httpx.Client(timeout=15.0, headers=headers) as client:
                r = client.get(url, follow_redirects=True)
                r.raise_for_status()
            feed = feedparser.parse(r.text)
            for entry in feed.entries[:15]:
                title = entry.title
                summary = entry.get("summary", "")
                if not self._matches_theme(title, summary):
                    continue
                cve_results.append({
                    "id": f"cve_{entry.id if hasattr(entry, 'id') else entry.link}",
                    "source": self.source_name,
                    "title": title,
                    "link": entry.link,
                    "summary": summary,
                    "published_at": datetime(*entry.published_parsed[:6]).isoformat() if hasattr(entry, "published_parsed") and entry.published_parsed else datetime.utcnow().isoformat()
                })
        except Exception as e:
            print(f"[Fetchers] Erro CVE {url}: {e}")
        return cve_results

#
# --- LWN.net fetcher ---
#

class LWNFetcher(BaseFetcher):
    source_name = "lwn"
    def __init__(self, rss_url: str = "https://lwn.net/headlines/rss", limit: int = 30):
        self.rss_url = rss_url
        self.limit = limit

    def fetch(self) -> list[dict]:
        results = []
        try:
            headers = {"User-Agent": USER_AGENT}
            with httpx.Client(timeout=15.0, headers=headers) as client:
                r = client.get(self.rss_url)
                r.raise_for_status()
            feed = feedparser.parse(r.text)
            entries = feed.entries[:self.limit]
            for entry in entries:
                link = entry.link
                results.append({
                    "id": f"lwn_{entry.get('id', entry.link).split('/')[-1]}",
                    "source": self.source_name,
                    "title": entry.title,
                    "link": link,
                    "summary": entry.get("summary", ""),
                    "published_at": entry.get("published", datetime.utcnow().isoformat())
                })
        except Exception as e:
            print(f"[Fetchers] Erro LWN: {e}")
        return results

#
# --- linux-cve-announce fetcher with theme filtering ---
#

DEFAULT_THEME_KEYWORDS = [
    "drm", "gpu", "i3c", "cxl", "mdio", "vc4", "panthor",
    "clk", "plat-dma", "pwm", "regulator", "gpio",
    "usb", "ssusb", "xhci", "dwc3",
    "net", "ipv6", "llc", "clustering",
    "sched", "fair", "tick", "irq", "preempt",
    "pci", "acpi", "firmware", "uefi",
]

class LinuxCVEAnnounceFetcher(BaseFetcher):
    source_name = "linux-cve-announce"
    def __init__(self, base_url: str = "https://marc.info", theme_keywords: list | None = None, max_months_back: int = 3, limit_per_month: int = 50):
        self.base_url = base_url
        self.theme_keywords = theme_keywords or DEFAULT_THEME_KEYWORDS
        self.max_months_back = max_months_back
        self.limit_per_month = limit_per_month

    def _extract_tags_and_cve(self, title: str) -> tuple[list, list]:
        cves = re.findall(r'CVE-\d{4}-\d+', title)
        tags = []
        # Pega o corpo depois de "CVE-XXXX-XXXX:"
        m = re.match(r'CVE-\d{4}-\d+:\s*(.+)', title)
        if m:
            body = m.group(1)
            segments = re.split(r'[:/]', body)[:4]
            seen = set()
            for seg in segments:
                clean = seg.strip().lower()
                if clean and clean not in seen:
                    seen.add(clean)
                    tags.append(clean)
        return cves, tags

    def _parse_month_page(self, html: str) -> list[dict]:
        messages = []
        entries = re.findall(r'<a href="(\?l=[^"]+w=2)"[^>]*>([^<]{30,150})</a>', html)
        for href, title in entries:
            cves, tags = self._extract_tags_and_cve(title)
            if not cves:
                continue
            # compara tags extraídas vs keywords
            if not any(kw.lower() in tags for kw in self.theme_keywords):
                continue
            messages.append({
                "id": f"cve-ann-{href.split('m=')[-1].split('&')[0]}",
                "source": self.source_name,
                "title": title.strip(),
                "link": f"{self.base_url}{href}",
                "summary": "",
                "published_at": datetime.utcnow().isoformat(),
                "cves": cves
            })
        return messages

    def fetch(self) -> list[dict]:
        results = []
        now = datetime.utcnow()
        for i in range(self.max_months_back):
            month = now.month - i
            year = now.year
            if month <= 0:
                month += 12
                year -= 1
            url = f"{self.base_url}/?l=linux-cve-announce&b={year}{month:02d}&w=2"
            try:
                headers = {"User-Agent": USER_AGENT}
                with httpx.Client(timeout=20.0, headers=headers) as client:
                    r = client.get(url)
                    if r.status_code != 200:
                        continue
                    messages = self._parse_month_page(r.text)
                    results.extend(messages)
                    if len(results) >= self.limit_per_month:
                        break
            except Exception as e:
                print(f"[Fetchers] Erro linux-cve-announce {url}: {e}")
                continue
        seen = set()
        unique = []
        for m in results:
            if m["id"] not in seen:
                seen.add(m["id"])
                unique.append(m)
        return unique[:self.limit_per_month]
