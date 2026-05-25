import httpx
from bs4 import BeautifulSoup
import re

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

JOB_SIGNALS = [
    "job-description", "jobDescription", "job_description",
    "job-details", "jobDetails", "description",
    "posting-description", "job-body", "responsibilities",
    "qualifications", "about-the-role", "overview",
]

def fetch_job(url: str) -> str:
    if not url.startswith("http"):
        url = "https://" + url
    try:
        r = httpx.get(url, headers=HEADERS, follow_redirects=True, timeout=15)
        r.raise_for_status()
    except Exception as e:
        raise ValueError(f"Could not fetch the job page: {e}")

    soup = BeautifulSoup(r.text, "html.parser")
    for tag in soup(["script","style","noscript","header","footer","nav","aside","iframe","svg","img","button"]):
        tag.decompose()

    block = None
    for signal in JOB_SIGNALS:
        block = soup.find(id=re.compile(signal, re.I)) or soup.find(class_=re.compile(signal, re.I))
        if block:
            break

    text = block.get_text("\n", strip=True) if block else (soup.find("main") or soup.find("body") or soup).get_text("\n", strip=True)
    lines = [l.strip() for l in text.splitlines() if l.strip() and len(l.strip()) > 2]
    result = "\n".join(lines)

    if len(result) < 100:
        raise ValueError("Could not extract text. The page may require login.")
    return result[:5000]
