"""
Fofoqueiro - Extratores de Conteúdo (Paralelizados)
"""
import httpx
import feedparser
from bs4 import BeautifulSoup
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Fofoqueiro/1.0"

def extract_body_snippet(url: str, max_chars: int = 250) -> str:
    """Acessa a URL da notícia e extrai o corpo de texto limpo (até max_chars)."""
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
            if full_text:
                return full_text[:max_chars].strip() + ("..." if len(full_text) > max_chars else "")
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
    def __init__(self, urls: list[str]):
        self.urls = urls

    def _fetch_url(self, url: str) -> list[dict]:
        cve_results = []
        headers = {"User-Agent": USER_AGENT}
        try:
            with httpx.Client(timeout=15.0, headers=headers) as client:
                r = client.get(url, follow_redirects=True)
                r.raise_for_status()
            feed = feedparser.parse(r.text)
            for entry in feed.entries[:15]:
                cve_results.append({
                    "id": f"cve_{entry.id if hasattr(entry, 'id') else entry.link}",
                    "source": self.source_name,
                    "title": entry.title,
                    "link": entry.link,
                    "summary": entry.get("summary", ""),
                    "published_at": datetime(*entry.published_parsed[:6]).isoformat() if hasattr(entry, "published_parsed") and entry.published_parsed else datetime.utcnow().isoformat()
                })
        except Exception as e:
            print(f"[Fetchers] Erro CVE {url}: {e}")
        return cve_results

    def fetch(self) -> list[dict]:
        results = []
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(self._fetch_url, url) for url in self.urls]
            for future in as_completed(futures):
                results.extend(future.result())
        return results
