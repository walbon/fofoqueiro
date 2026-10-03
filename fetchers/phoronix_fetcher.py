"""
Phoronix Fetcher for Fofoqueiro
"""
import feedparser
from datetime import datetime
from . import extract_body_snippet
import config

class PhoronixFetcher:
    source_name = "phoronix"

    def __init__(self, rss_url: str = None, limit: int = 30):
        self.rss_url = rss_url or config.PHRONIX_RSS_URL
        self.limit = limit

    def fetch(self) -> list[dict]:
        results = []
        try:
            feed = feedparser.parse(self.rss_url)
            entries = feed.entries[:self.limit]
            for entry in entries:
                title = entry.get("title", "")
                link = entry.get("link", "")
                # Published date
                published = entry.get("published") or entry.get("updated")
                if published:
                    try:
                        # feedparser returns a struct time in published_parsed
                        if hasattr(entry, "published_parsed") and entry.published_parsed:
                            published = datetime(*entry.published_parsed[:6]).isoformat()
                        elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                            published = datetime(*entry.updated_parsed[:6]).isoformat()
                        else:
                            published = datetime.utcnow().isoformat()
                    except Exception:
                        published = datetime.utcnow().isoformat()
                else:
                    published = datetime.utcnow().isoformat()

                # Summary from entry
                summary = entry.get("summary", "")

                # Optionally extract a richer snippet from the article page
                # Limit to 250 chars similar to other fetchers
                if link:
                    snippet = extract_body_snippet(link, max_chars=250)
                    if snippet:
                        summary = snippet

                results.append({
                    "id": f"phoronix_{hash(link)}",
                    "source": self.source_name,
                    "title": title,
                    "link": link,
                    "summary": summary,
                    "published_at": published
                })
        except Exception as e:
            print(f"[Fetchers] Erro Phoronix: {e}")
        return results