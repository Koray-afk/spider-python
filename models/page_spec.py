from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, ConfigDict


ExpectedAction = Literal[
    "navigate", "submit", "toggle", "open_modal", "filter", "display", "unknown", "none"
]


class ElementSpec(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    tag: str
    text: str = ""
    role: str = "unknown"
    purpose: str
    expected_action: ExpectedAction = "unknown"
    expected_target: Optional[str] = None
    href: Optional[str] = None


class PageSpec(BaseModel):
    model_config = ConfigDict(extra="ignore")

    page_slug: str
    page_name: str
    page_url: str = "unknown"
    page_purpose: str
    summary: str = ""
    elements: list[ElementSpec] = Field(default_factory=list)
