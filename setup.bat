@echo off
echo Installing packages...
pip install playwright groq httpx beautifulsoup4 pdfplumber
playwright install chromium
echo.
echo Setup complete! Now run: python auto_apply.py
pause
