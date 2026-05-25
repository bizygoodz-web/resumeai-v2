from groq import Groq
import os
import json
import re

def tailor_resume(resume_text: str, job_text: str) -> dict:
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

    prompt = f"""You are an expert resume coach and ATS specialist.

JOB DESCRIPTION:
{job_text[:3000]}

CANDIDATE RESUME:
{resume_text[:2000]}

Tasks:
1. Find the top keywords/skills the JD requires that the resume underrepresents.
2. Rewrite the resume bullet points to naturally incorporate those keywords.
3. Give a fit score 0-100 before and after.
4. Write a 2-sentence summary of what changed.

Respond ONLY with valid JSON, no markdown fences:
{{
  "fit_score_before": <number>,
  "fit_score_after": <number>,
  "missing_keywords": ["keyword1", "keyword2"],
  "rewritten_bullets": ["bullet 1", "bullet 2", "bullet 3"],
  "summary": "Two sentence explanation."
}}"""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1500
    )

    raw = response.choices[0].message.content.strip()
    raw = re.sub(r"^```json\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    return json.loads(raw)
