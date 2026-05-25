"""
ResumeAI Auto-Apply
====================
Reads a job URL, tailors your resume, generates a cover letter,
then uses Playwright to automatically fill and submit the application.

Usage:
    python auto_apply.py
"""

import asyncio
import json
import os
import re
import sys
from pathlib import Path

import httpx
from bs4 import BeautifulSoup
from groq import Groq
from playwright.async_api import async_playwright

# ── CONFIG ─────────────────────────────────────────────────────────────────
YOUR_NAME       = "Tirumalarao Kilari"
YOUR_EMAIL      = "kilaritirumalarao@gmail.com"
YOUR_PHONE      = "512-555-0000"          # ← update this
YOUR_LOCATION   = "Pflugerville, TX"
YOUR_LINKEDIN   = "linkedin.com/in/tirumalaraokilari-803829273"
YOUR_GITHUB     = "github.com/bizygoodz-web"
RESUME_PDF_PATH = "resume.pdf"            # ← put your resume PDF in the same folder
GROQ_API_KEY    = os.environ.get("GROQ_API_KEY", "")

client = Groq(api_key=GROQ_API_KEY)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

# ── STEP 1: SCRAPE JOB ─────────────────────────────────────────────────────
def scrape_job(url: str) -> str:
    print(f"\n📋 Reading job: {url}")
    r = httpx.get(url, headers=HEADERS, follow_redirects=True, timeout=15)
    soup = BeautifulSoup(r.text, "html.parser")
    for tag in soup(["script","style","noscript","header","footer","nav","aside"]):
        tag.decompose()
    signals = ["job-description","jobDescription","description","job-details","responsibilities","qualifications"]
    block = None
    for s in signals:
        block = soup.find(id=re.compile(s, re.I)) or soup.find(class_=re.compile(s, re.I))
        if block:
            break
    text = block.get_text("\n", strip=True) if block else soup.get_text("\n", strip=True)
    lines = [l.strip() for l in text.splitlines() if l.strip() and len(l.strip()) > 2]
    result = "\n".join(lines)[:4000]
    print(f"   ✓ Job read — {len(result):,} chars")
    return result

# ── STEP 2: TAILOR RESUME ──────────────────────────────────────────────────
def tailor_resume(resume_text: str, job_text: str) -> dict:
    print("\n🤖 Tailoring resume with AI...")
    prompt = f"""You are an expert resume coach.

JOB DESCRIPTION:
{job_text[:2500]}

RESUME:
{resume_text[:1500]}

Tasks:
1. Find missing keywords from the JD.
2. Rewrite resume bullet points to match.
3. Score 0-100 before and after.

Respond ONLY with valid JSON:
{{
  "fit_score_before": <number>,
  "fit_score_after": <number>,
  "missing_keywords": ["kw1", "kw2"],
  "rewritten_bullets": ["bullet 1", "bullet 2", "bullet 3"],
  "summary": "Two sentence explanation."
}}"""
    resp = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1000
    )
    raw = resp.choices[0].message.content.strip()
    raw = re.sub(r"^```json\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    result = json.loads(raw)
    print(f"   ✓ Score: {result['fit_score_before']}% → {result['fit_score_after']}%")
    return result

# ── STEP 3: GENERATE COVER LETTER ──────────────────────────────────────────
def generate_cover_letter(job_text: str, tailored: dict) -> str:
    print("\n✍️  Generating cover letter...")
    prompt = f"""Write a concise, professional cover letter for this job.

Candidate: {YOUR_NAME}, AI Engineer, Pflugerville TX
Email: {YOUR_EMAIL}
Key strengths: {", ".join(tailored["missing_keywords"][:5])}

JOB:
{job_text[:1500]}

Write 3 short paragraphs. Professional, confident, no fluff. Plain text only."""
    resp = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=600
    )
    letter = resp.choices[0].message.content.strip()
    print("   ✓ Cover letter generated")
    return letter

# ── STEP 4: DETECT FORM TYPE ───────────────────────────────────────────────
def detect_form_type(url: str) -> str:
    url = url.lower()
    if "greenhouse.io" in url or "boards.greenhouse" in url:
        return "greenhouse"
    elif "lever.co" in url:
        return "lever"
    elif "workday.com" in url:
        return "workday"
    elif "linkedin.com" in url:
        return "linkedin"
    elif "indeed.com" in url:
        return "indeed"
    return "generic"

# ── STEP 5: AUTO-FILL FORMS ────────────────────────────────────────────────
async def fill_greenhouse(page, info: dict):
    """Fill Greenhouse application forms."""
    print("   Filling Greenhouse form...")
    await page.wait_for_selector("input", timeout=10000)

    # Fill name fields
    for selector in ['input[name*="first"]', 'input[id*="first"]', 'input[placeholder*="First"]']:
        try:
            await page.fill(selector, info["first_name"])
            break
        except:
            pass

    for selector in ['input[name*="last"]', 'input[id*="last"]', 'input[placeholder*="Last"]']:
        try:
            await page.fill(selector, info["last_name"])
            break
        except:
            pass

    # Fill email
    for selector in ['input[name*="email"]', 'input[type="email"]', 'input[id*="email"]']:
        try:
            await page.fill(selector, info["email"])
            break
        except:
            pass

    # Fill phone
    for selector in ['input[name*="phone"]', 'input[type="tel"]', 'input[id*="phone"]']:
        try:
            await page.fill(selector, info["phone"])
            break
        except:
            pass

    # Upload resume
    try:
        file_input = page.locator('input[type="file"]').first
        await file_input.set_input_files(info["resume_path"])
        print("   ✓ Resume uploaded")
    except Exception as e:
        print(f"   ⚠ Could not upload resume: {e}")

    # Fill cover letter if textarea exists
    try:
        textarea = page.locator('textarea').first
        await textarea.fill(info["cover_letter"])
        print("   ✓ Cover letter filled")
    except:
        pass

async def fill_lever(page, info: dict):
    """Fill Lever application forms."""
    print("   Filling Lever form...")
    await page.wait_for_selector("input", timeout=10000)

    field_map = {
        'input[name="name"]': info["full_name"],
        'input[name="email"]': info["email"],
        'input[name="phone"]': info["phone"],
        'input[name="location"]': info["location"],
        'input[name="urls[LinkedIn]"]': info["linkedin"],
        'input[name="urls[GitHub]"]': info["github"],
    }
    for selector, value in field_map.items():
        try:
            await page.fill(selector, value)
        except:
            pass

    try:
        file_input = page.locator('input[type="file"]').first
        await file_input.set_input_files(info["resume_path"])
        print("   ✓ Resume uploaded")
    except Exception as e:
        print(f"   ⚠ Could not upload resume: {e}")

    try:
        textarea = page.locator('textarea[name="comments"]').first
        await textarea.fill(info["cover_letter"])
    except:
        pass

async def fill_generic(page, info: dict):
    """Generic form filler for any job site."""
    print("   Filling generic form...")
    await page.wait_for_selector("input", timeout=10000)

    # Map common field patterns to values
    patterns = [
        (["first_name","firstname","first-name","fname"], info["first_name"]),
        (["last_name","lastname","last-name","lname"], info["last_name"]),
        (["full_name","fullname","name","applicant_name"], info["full_name"]),
        (["email","e-mail","email_address"], info["email"]),
        (["phone","telephone","mobile","cell"], info["phone"]),
        (["location","city","address"], info["location"]),
        (["linkedin","linkedin_url"], info["linkedin"]),
        (["github","github_url"], info["github"]),
    ]

    for terms, value in patterns:
        for term in terms:
            for attr in ["name","id","placeholder"]:
                try:
                    el = page.locator(f'input[{attr}*="{term}" i]').first
                    await el.fill(value, timeout=2000)
                    break
                except:
                    pass

    try:
        file_input = page.locator('input[type="file"]').first
        await file_input.set_input_files(info["resume_path"])
        print("   ✓ Resume uploaded")
    except Exception as e:
        print(f"   ⚠ Could not upload resume: {e}")

    try:
        textarea = page.locator('textarea').first
        await textarea.fill(info["cover_letter"], timeout=2000)
    except:
        pass

# ── STEP 6: APPLY ──────────────────────────────────────────────────────────
async def auto_apply(job_url: str, resume_text: str, tailored: dict, cover_letter: str):
    form_type = detect_form_type(job_url)
    print(f"\n🌐 Opening browser — detected form type: {form_type}")

    info = {
        "first_name":   YOUR_NAME.split()[0],
        "last_name":    " ".join(YOUR_NAME.split()[1:]),
        "full_name":    YOUR_NAME,
        "email":        YOUR_EMAIL,
        "phone":        YOUR_PHONE,
        "location":     YOUR_LOCATION,
        "linkedin":     YOUR_LINKEDIN,
        "github":       YOUR_GITHUB,
        "resume_path":  str(Path(RESUME_PDF_PATH).resolve()),
        "cover_letter": cover_letter,
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # headless=False so you can watch
        page = await browser.new_page()
        await page.goto(job_url, timeout=30000)
        print(f"   ✓ Page opened")
        await page.wait_for_timeout(2000)

        if form_type == "greenhouse":
            await fill_greenhouse(page, info)
        elif form_type == "lever":
            await fill_lever(page, info)
        else:
            await fill_generic(page, info)

        print("\n⏸️  PAUSING before submit — review the form in the browser window!")
        print("   Press ENTER here to submit, or Ctrl+C to cancel.")
        input()

        # Click submit button
        submit_selectors = [
            'button[type="submit"]',
            'input[type="submit"]',
            'button:has-text("Submit")',
            'button:has-text("Apply")',
            'button:has-text("Send application")',
        ]
        submitted = False
        for selector in submit_selectors:
            try:
                await page.click(selector, timeout=3000)
                submitted = True
                print("   ✓ Application submitted!")
                break
            except:
                pass

        if not submitted:
            print("   ⚠ Could not find submit button — please click it manually in the browser.")

        await page.wait_for_timeout(3000)
        await browser.close()

# ── MAIN ───────────────────────────────────────────────────────────────────
async def main():
    print("=" * 50)
    print("  ResumeAI Auto-Apply")
    print("=" * 50)

    job_url = input("\nPaste the job application URL: ").strip()
    if not job_url:
        print("No URL entered. Exiting.")
        sys.exit(1)

    # Read resume
    if not Path(RESUME_PDF_PATH).exists():
        print(f"\n⚠ Resume not found at '{RESUME_PDF_PATH}'")
        print("  Put your resume PDF in the same folder as this script and name it 'resume.pdf'")
        sys.exit(1)

    import pdfplumber
    with pdfplumber.open(RESUME_PDF_PATH) as pdf:
        resume_text = "\n".join(p.extract_text() or "" for p in pdf.pages)
    print(f"✓ Resume read — {len(resume_text):,} chars")

    job_text   = scrape_job(job_url)
    tailored   = tailor_resume(resume_text, job_text)
    cover      = generate_cover_letter(job_text, tailored)

    print("\n" + "="*50)
    print("TAILORING RESULTS")
    print("="*50)
    print(f"Fit score: {tailored['fit_score_before']}% → {tailored['fit_score_after']}%")
    print(f"Keywords added: {', '.join(tailored['missing_keywords'][:5])}")
    print(f"\nCover letter preview:\n{cover[:200]}...")
    print("="*50)

    go = input("\nProceed with auto-apply? (yes/no): ").strip().lower()
    if go != "yes":
        print("Cancelled.")
        sys.exit(0)

    await auto_apply(job_url, resume_text, tailored, cover)

    # Log to file
    log = {
        "url": job_url,
        "fit_before": tailored["fit_score_before"],
        "fit_after": tailored["fit_score_after"],
        "keywords": tailored["missing_keywords"],
        "status": "applied"
    }
    with open("applications_log.json", "a") as f:
        f.write(json.dumps(log) + "\n")
    print("\n✅ Application logged to applications_log.json")
    print("\n🎉 Done! Check your email for confirmation.")

if __name__ == "__main__":
    asyncio.run(main())
