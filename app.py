import streamlit as st
import pdfplumber
from docx import Document
import os
import tempfile
import json
import re
from scraper import fetch_job
from rewriter import tailor_resume
from groq import Groq

st.set_page_config(
    page_title="ResumeAI by Tirumalarao",
    page_icon="📄",
    layout="centered"
)

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

YOUR_NAME     = "Tirumalarao Kilari"
YOUR_EMAIL    = "kilaritirumalarao@gmail.com"
YOUR_PHONE    = "512-555-0000"
YOUR_LOCATION = "Pflugerville, TX"
YOUR_LINKEDIN = "linkedin.com/in/tirumalaraokilari-803829273"
YOUR_GITHUB   = "github.com/bizygoodz-web"

st.title("📄 ResumeAI")
st.caption("Built by Tirumalarao Kilari · AI Engineer · Pflugerville TX")
st.markdown("Upload your resume and paste a job URL — AI reads the job, tailors your resume, writes your cover letter, and opens the application ready to submit.")
st.markdown("---")

def extract_text(uploaded_file):
    suffix = "." + uploaded_file.name.split(".")[-1].lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name
    try:
        if suffix == ".pdf":
            with pdfplumber.open(tmp_path) as pdf:
                return "\n".join(p.extract_text() or "" for p in pdf.pages)
        elif suffix == ".docx":
            doc = Document(tmp_path)
            return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    finally:
        os.remove(tmp_path)
    return ""

def generate_cover_letter(job_text: str, tailored: dict) -> str:
    prompt = f"""Write a concise professional cover letter for this job.

Candidate: {YOUR_NAME}, AI Engineer, {YOUR_LOCATION}
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
    return resp.choices[0].message.content.strip()

def generate_common_answers(job_text: str) -> dict:
    prompt = f"""Based on this job description, generate answers to common application questions for {YOUR_NAME}.

JOB:
{job_text[:1000]}

Generate answers for these questions. Keep each answer under 3 sentences.

Respond ONLY with valid JSON:
{{
  "why_this_role": "...",
  "years_experience": "3 years",
  "salary_expectation": "Open to discussion based on the full compensation package",
  "available_start": "Immediately",
  "work_authorization": "Yes, authorized to work in the US",
  "why_qualified": "..."
}}"""
    resp = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500
    )
    raw = resp.choices[0].message.content.strip()
    raw = re.sub(r"^```json\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    try:
        return json.loads(raw)
    except:
        return {}

col1, col2 = st.columns(2)

with col1:
    st.subheader("Your resume")
    uploaded = st.file_uploader("Upload PDF or DOCX", type=["pdf","docx"])
    if uploaded:
        st.success(f"✓ {uploaded.name}")

with col2:
    st.subheader("Job posting URL")
    job_url = st.text_input("Paste any job URL", placeholder="https://boards.greenhouse.io/...")
    if job_url:
        with st.spinner("Reading job page..."):
            try:
                job_text = fetch_job(job_url)
                st.success(f"✓ Job read — {len(job_text):,} chars")
            except Exception as e:
                st.error(f"✗ {e}")
                job_text = None
    else:
        job_text = None

st.markdown("---")

if st.button("✨ Tailor + Prepare Application", use_container_width=True, type="primary"):
    if not uploaded:
        st.error("Please upload your resume first.")
    elif not job_text:
        st.error("Please paste a valid job URL.")
    else:
        with st.spinner("AI is working — tailoring resume, writing cover letter, preparing answers..."):
            try:
                resume_text = extract_text(uploaded)
                tailored    = tailor_resume(resume_text, job_text)
                cover       = generate_cover_letter(job_text, tailored)
                answers     = generate_common_answers(job_text)

                st.markdown("---")
                st.subheader("✅ Application package ready")

                # Scores
                col_a, col_b, col_c = st.columns(3)
                col_a.metric("Score before", f"{tailored['fit_score_before']}%")
                col_b.metric("Score after",  f"{tailored['fit_score_after']}%")
                col_c.metric("Improvement",  f"+{tailored['fit_score_after'] - tailored['fit_score_before']}pts")

                # Keywords
                st.markdown("**Keywords added:**")
                st.markdown(" ".join([f"`{k}`" for k in tailored["missing_keywords"]]))

                # Rewritten bullets
                with st.expander("📝 Rewritten resume bullets", expanded=True):
                    for b in tailored["rewritten_bullets"]:
                        st.markdown(f"• {b}")

                # Cover letter
                with st.expander("✉️ Cover letter — copy and paste", expanded=True):
                    st.text_area("", cover, height=220, label_visibility="collapsed")

                # Pre-filled answers
                if answers:
                    with st.expander("💬 Pre-filled answers to common questions"):
                        for q, a in answers.items():
                            label = q.replace("_", " ").title()
                            st.markdown(f"**{label}:**")
                            st.code(a, language=None)

                # Personal info
                with st.expander("📋 Your info — copy when filling the form"):
                    st.code(f"""Name:      {YOUR_NAME}
Email:     {YOUR_EMAIL}
Phone:     {YOUR_PHONE}
Location:  {YOUR_LOCATION}
LinkedIn:  {YOUR_LINKEDIN}
GitHub:    {YOUR_GITHUB}""", language=None)

                # Open job in new tab
                st.markdown("---")
                st.markdown("### 🚀 Ready to apply?")
                st.markdown(f"Everything is prepared. Click below to open the job application:")
                st.link_button("Open job application →", job_url, use_container_width=True, type="primary")
                st.info("The job page will open. Your cover letter and answers are ready to copy-paste. The whole application should take under 2 minutes.")

                # Download package
                package = f"""RESUMEAI APPLICATION PACKAGE
{'='*50}
JOB URL: {job_url}

FIT SCORE: {tailored['fit_score_before']}% → {tailored['fit_score_after']}%

KEYWORDS ADDED:
{chr(10).join('• ' + k for k in tailored['missing_keywords'])}

REWRITTEN BULLETS:
{chr(10).join('• ' + b for b in tailored['rewritten_bullets'])}

COVER LETTER:
{cover}

COMMON ANSWERS:
{chr(10).join(f'{q.replace("_"," ").upper()}: {a}' for q,a in answers.items())}

YOUR INFO:
Name: {YOUR_NAME}
Email: {YOUR_EMAIL}
Phone: {YOUR_PHONE}
Location: {YOUR_LOCATION}
LinkedIn: {YOUR_LINKEDIN}
GitHub: {YOUR_GITHUB}"""

                st.download_button(
                    "⬇ Download full application package",
                    package,
                    file_name="application_package.txt",
                    mime="text/plain",
                    use_container_width=True
                )

            except Exception as e:
                st.error(f"Something went wrong: {e}")

st.markdown("---")
st.caption("Built by Tirumalarao Kilari · AI Engineer · Pflugerville TX")
