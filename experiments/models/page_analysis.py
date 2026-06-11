from typing import List, Optional
from pydantic import BaseModel

class PageAnalysis(BaseModel):
    pageType: str
    purpose: str
    mainCTA: str

    importantSections: List[str]

    summary: str
    visualLayout: Optional[str] = None
    colorScheme: Optional[str] = None