import asyncio
import httpx
from bs4 import BeautifulSoup
from src.data.cache import cache
from src.data.rate_limiter import rate_limiter


async def scrape_url(url: str, selector: str = None) -> dict:
    cache_key = f"scrape:{url}:{selector}"
    cached = cache.get(cache_key, ttl=300)
    if cached:
        return cached

    await rate_limiter.acquire("scraper")
    async with httpx.AsyncClient(follow_redirects=True) as client:
        resp = await client.get(
            url,
            timeout=15,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
        )
        resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    if selector:
        elements = soup.select(selector)
        text = "\n".join(el.get_text(strip=True) for el in elements)
    else:
        text = soup.get_text(separator="\n", strip=True)

    title = soup.title.string if soup.title else ""
    result = {
        "url": url,
        "title": title,
        "text": text[:5000],
        "status": resp.status_code,
    }
    cache.set(cache_key, result)
    return result


async def scrape_multiple(urls: list[str], selector: str = None) -> list[dict]:
    tasks = [scrape_url(u, selector) for u in urls]
    return await asyncio.gather(*tasks, return_exceptions=True)
