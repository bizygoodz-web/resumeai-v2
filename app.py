import streamlit as st
import pdfplumber
from docx import Document
import os
import tempfile
from scraper import fetch_job
from rewriter import tailor_resume

st.set_page_config(
    page_title="ResumeAI by Tirumalarao",
    page_icon="📄",
    layout="centered"
)

st.title("📄 ResumeAI")
st.caption("Built by Tirumalarao Kilari · AI Engineer · Pflugerville TX")
st.markdown("Upload your resume and paste a job URL — we read the job and tailor your resume automatically.")
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

col1, col2 = st.columns(2)

with col1:
    st.subheader("Your resume")
    uploaded = st.file_uploader("Upload PDF or DOCX", type=["pdf","docx"])
    if uploaded:
        st.success(f"✓ {uploaded.name}")

with col2:
    st.subheader("Job posting URL")
    job_url = st.text_input("Paste any job URL", placeholder="https://linkedin.com/jobs/view/...")
    if job_url:
        with st.spinner("Reading job page..."):
            try:
                job_text = fetch_job(job_url)
                st.success(f"✓ Job read — {len(job_text):,} chars")
                with st.expander("Preview job text"):
                    st.text(job_text[:500] + "...")
            except Exception as e:
                st.error(f"✗ {e}")
                job_text = None
    else:
        job_text = None

st.markdown("---")

if st.button("✨ Tailor my resume", use_container_width=True, type="primary"):
    if not uploaded:
        st.error("Please upload your resume first.")
    elif not job_text:
        st.error("Please paste a job URL and wait for it to load.")
    else:
        with st.spinner("Tailoring your resume with AI..."):
            try:
                resume_text = extract_text(uploaded)
                result = tailor_resume(resume_text, job_text)

                st.markdown("---")
                st.subheader("Your tailored resume")

                col_a, col_b, col_c = st.columns(3)
                col_a.metric("Score before", f"{result['fit_score_before']}%")
                col_b.metric("Score after", f"{result['fit_score_after']}%")
                col_c.metric("Improvement", f"+{result['fit_score_after'] - result['fit_score_before']}pts")

                st.markdown("**Missing keywords added:**")
                st.markdown(" ".join([f"`{k}`" for k in result["missing_keywords"]]))

                st.markdown("**Rewritten bullet points:**")
                for bullet in result["rewritten_bullets"]:
                    st.markdown(f"• {bullet}")

                st.markdown("**What changed:**")
                st.info(result["summary"])

                output = f"""RESUMEAI RESULTS
{'='*40}
Fit score: {result['fit_score_before']}% → {result['fit_score_after']}% (+{result['fit_score_after'] - result['fit_score_before']}pts)

MISSING KEYWORDS:
{chr(10).join('• ' + k for k in result['missing_keywords'])}

REWRITTEN BULLETS:
{chr(10).join('• ' + b for b in result['rewritten_bullets'])}

SUMMARY:
{result['summary']}"""

                st.download_button(
                    "⬇ Download results",
                    output,
                    file_name="tailored_resume.txt",
                    mime="text/plain",
                    use_container_width=True
                )

            except Exception as e:
                st.error(f"Something went wrong: {e}")

st.markdown("---")
st.caption("Built by [Tirumalarao Kilari](https://linkedin.com/in/tirumalaraokilari-803829273) · [GitHub](https://github.com/bizygoodz-web)")
