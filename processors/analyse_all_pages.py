# pyrefly: ignore [missing-import]
from langchain_core.messages import HumanMessage
from models.page_analysis import PageAnalysis
# pyrefly: ignore [missing-import]
from langchain_google_genai import ChatGoogleGenerativeAI
import base64
import os
import re
import json
import glob
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv

load_dotenv()

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    api_key=os.getenv("GEMINI_API_KEY"),
    temperature=0
)

structured_llm = llm.with_structured_output(PageAnalysis)

ANALYSIS_PROMPT = """Analyze this webpage using both the scraped text content and the screenshot image.

URL:
{url}

CONTENT:
{content}

Determine:

1. Page Type
2. Purpose
3. Main CTA
4. Important Sections
5. Summary
6. Visual Layout (describe layout structure from the screenshot, e.g. hero section, navbar, grid of cards)
7. Color Scheme (describe dominant colors and styling from the screenshot)

Be concise and factual."""

os.makedirs("analysis", exist_ok=True)

txt_files = sorted(glob.glob("pages/page-*.txt"))

if not txt_files:
    print("No page .txt files found in pages/. Run crawler.py first.")
else:
    for txt_path in txt_files:
        filename = os.path.basename(txt_path)
        page_name = os.path.splitext(filename)[0]

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

        png_path = os.path.join("pages", f"{page_name}.png")
        prompt_text = ANALYSIS_PROMPT.format(url=url, content=content)

        print(f"Analyzing {txt_path} ...")

        if os.path.exists(png_path):
            with open(png_path, "rb") as img_file:
                image_data = base64.b64encode(img_file.read()).decode("utf-8")

            message = HumanMessage(content=[
                {"type": "text", "text": prompt_text},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{image_data}"}
                }
            ])
        else:
            print(f"  Warning: {png_path} not found, analyzing text only.")
            message = HumanMessage(content=prompt_text)

        analysis = structured_llm.invoke([message])

        output_path = os.path.join("analysis", f"{page_name}.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(analysis.model_dump(), f, indent=2)

        print(f"  -> Saved {output_path}")

    print(f"\nDone. Analyzed {len(txt_files)} page(s).")
