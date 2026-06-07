from langchain_core.prompts import PromptTemplate
from models.page_analysis import PageAnalysis
from langchain_google_genai import ChatGoogleGenerativeAI
import os
import re
import json
import glob
from dotenv import load_dotenv

load_dotenv()

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    api_key=os.getenv("GEMINI_API_KEY"),
    temperature=0
)

structured_llm = llm.with_structured_output(PageAnalysis)

prompt_template = PromptTemplate.from_template(
    """
Analyze this webpage.

URL:
{url}

CONTENT:
{content}

Determine:

1. Page Type
2. Purpose
3. Main CTA
4. Summary

Be concise and factual.
"""
)

chain = prompt_template | structured_llm

os.makedirs("analysis", exist_ok=True)

txt_files = sorted(glob.glob("pages/page-*.txt"))

if not txt_files:
    print("No page .txt files found in pages/. Run crawler.py first.")
else:
    for txt_path in txt_files:
        filename = os.path.basename(txt_path)           # e.g. page-3.txt
        page_name = os.path.splitext(filename)[0]       # e.g. page-3

        # Try to extract canonical URL from the matching HTML file
        url = page_name
        html_path = os.path.join("pages", f"{page_name}.html")
        if os.path.exists(html_path):
            with open(html_path, "r", encoding="utf-8") as hf:
                html = hf.read()
            match = re.search(
                r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)["\']',
                html, re.IGNORECASE
            )
            if not match:
                match = re.search(
                    r'<meta[^>]+property=["\']og:url["\'][^>]+content=["\']([^"\']+)["\']',
                    html, re.IGNORECASE
                )
            if match:
                url = match.group(1)

        with open(txt_path, "r", encoding="utf-8") as f:
            content = f.read()

        print(f"Analyzing {txt_path} ...")

        analysis = chain.invoke({
            "url": url,
            "content": content
        })

        output_path = os.path.join("analysis", f"{page_name}.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(analysis.model_dump(), f, indent=2)

        print(f"  -> Saved {output_path}")

    print(f"\nDone. Analyzed {len(txt_files)} page(s).")
