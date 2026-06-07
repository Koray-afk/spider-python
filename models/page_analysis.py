from typing import List
from pydantic import BaseModel

class PageAnalysis(BaseModel):
    pageType: str
    purpose: str
    mainCTA: str

    importantSections: List[str]

    summary: str