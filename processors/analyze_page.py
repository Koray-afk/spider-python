from langchain_core.prompts import PromptTemplate
from models.page_analysis import PageAnalysis
from langchain_google_genai import ChatGoogleGenerativeAI
import os
from dotenv import load_dotenv
load_dotenv()

import json

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    api_key=os.getenv("GEMINI_API_KEY"),
    temperature=0
)

structured_llm = llm.with_structured_output(
    PageAnalysis
)


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

Be concise and factual .
"""
)

# print(prompt)
chain = prompt_template | structured_llm


content =open(
    "pages/page-1.txt",
    "r",
    encoding="utf-8"
).read()


analysis = chain.invoke({
    "url": "https://stripe.com",
    "content": content
})

os.makedirs(
    "analysis",
    exist_ok=True
)

with open(
    "analysis/page-1.json",
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        analysis.model_dump(),
        f,
        indent=2
    )

print(analysis)
print(type(analysis))











