"""Agent 1: assign element IDs and catalog page purpose via Gemini."""

from __future__ import annotations

import json
from pathlib import Path

from dotenv import load_dotenv

from html_cleaner import clean_html_for_llm, discover_page_html_files
from models.page_spec import ElementSpec, PageSpec
from processors.element_ids import assign_element_ids
from services.gemini_service import catalog_element_batch, catalog_page_summary

load_dotenv()

BATCH_SIZE = 25


def _slug_from_html_path(html_path: Path, pages_dir: Path) -> str:
    rel = html_path.relative_to(pages_dir)
    if rel.name == "index.html":
        return rel.parent.name
    return rel.stem


def _page_name(slug: str) -> str:
    return slug.replace("-", " ").title()


def _parse_json(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


def catalog_one_page(
    html_path: Path,
    pages_dir: Path,
    output_dir: Path,
    png_path: Path | None = None,
) -> PageSpec:
    slug = _slug_from_html_path(html_path, pages_dir)
    meta_path = pages_dir / f"{slug}.meta"
    page_url = meta_path.read_text(encoding="utf-8").strip() if meta_path.exists() else "unknown"

    raw_html = html_path.read_text(encoding="utf-8")
    annotated_full, records = assign_element_ids(raw_html, prefix="el")
    cleaned = clean_html_for_llm(annotated_full)

    annotated_dir = output_dir / "annotated"
    annotated_dir.mkdir(parents=True, exist_ok=True)
    annotated_path = annotated_dir / f"{slug}.html"
    annotated_path.write_text(annotated_full, encoding="utf-8")

    if png_path is None:
        candidate = pages_dir / f"{slug}.png"
        png_path = candidate if candidate.exists() else None

    png_str = str(png_path) if png_path else None
    summary_raw = catalog_page_summary(
        page_slug=slug,
        page_url=page_url,
        element_count=len(records),
        html_snippet=cleaned,
        png_path=png_str,
    )
    page_data = _parse_json(summary_raw)

    cataloged_items: list[dict] = []
    record_dicts = [r.__dict__ for r in records]
    total_batches = (len(record_dicts) + BATCH_SIZE - 1) // BATCH_SIZE
    for batch_idx in range(0, len(record_dicts), BATCH_SIZE):
        batch = record_dicts[batch_idx : batch_idx + BATCH_SIZE]
        batch_num = batch_idx // BATCH_SIZE + 1
        print(f"       batch {batch_num}/{total_batches} ({len(batch)} elements)", flush=True)
        raw_spec = catalog_element_batch(
            annotated_html=cleaned,
            element_records=batch,
            page_slug=slug,
            page_url=page_url,
            png_path=png_str if batch_idx == 0 else None,
        )
        batch_data = _parse_json(raw_spec)
        if isinstance(batch_data, list):
            cataloged_items.extend(batch_data)
        else:
            cataloged_items.extend(batch_data.get("elements", []))

    elements = []
    by_id = {r.id: r for r in records}
    for item in cataloged_items:
        eid = item.get("id", "")
        rec = by_id.get(eid)
        elements.append(
            ElementSpec(
                id=eid,
                tag=item.get("tag") or (rec.tag if rec else "unknown"),
                text=item.get("text") or (rec.text if rec else ""),
                role=item.get("role", "unknown"),
                purpose=item.get("purpose", "Unknown purpose"),
                expected_action=item.get("expected_action", "unknown"),
                expected_target=item.get("expected_target"),
                href=item.get("href") or (rec.href if rec else None),
            )
        )

    seen = {e.id for e in elements}
    for rec in records:
        if rec.id not in seen:
            elements.append(
                ElementSpec(
                    id=rec.id,
                    tag=rec.tag,
                    text=rec.text,
                    role="unknown",
                    purpose="Purpose not inferred",
                    expected_action="unknown",
                    href=rec.href,
                )
            )

    spec = PageSpec(
        page_slug=slug,
        page_name=page_data.get("page_name") or _page_name(slug),
        page_url=page_url,
        page_purpose=page_data.get("page_purpose", "Unknown page purpose"),
        summary=page_data.get("summary", ""),
        elements=sorted(elements, key=lambda e: e.id),
    )

    specs_dir = output_dir / "specs"
    specs_dir.mkdir(parents=True, exist_ok=True)
    spec_path = specs_dir / f"{slug}.json"
    spec_path.write_text(spec.model_dump_json(indent=2), encoding="utf-8")
    return spec


def catalog_all_pages(
    pages_dir: str = "pages",
    output_dir: str = "analysis",
    skip_existing: bool = True,
) -> list[PageSpec]:
    pages_path = Path(pages_dir)
    out_path = Path(output_dir)
    html_files = discover_page_html_files(pages_path)
    if not html_files:
        raise FileNotFoundError(f"No HTML files under {pages_path}")

    specs: list[PageSpec] = []
    for i, html_file in enumerate(html_files, 1):
        slug = _slug_from_html_path(html_file, pages_path)
        spec_file = out_path / "specs" / f"{slug}.json"
        if skip_existing and spec_file.exists():
            print(f"  [{i}/{len(html_files)}] ⏩ Skipping {slug}", flush=True)
            specs.append(PageSpec.model_validate_json(spec_file.read_text(encoding="utf-8")))
            continue

        print(f"  [{i}/{len(html_files)}] 📋 Cataloging {slug}", flush=True)
        try:
            spec = catalog_one_page(html_file, pages_path, out_path)
            specs.append(spec)
            print(f"       ✅ {len(spec.elements)} elements → {spec_file}", flush=True)
        except Exception as exc:
            print(f"       ⚠ Failed {slug}: {exc}", flush=True)

    print(f"\n✅ Cataloged {len(specs)} pages → {out_path / 'specs'}/", flush=True)
    return specs


if __name__ == "__main__":
    print("[*] Cataloging pages (Agent 1)...")
    catalog_all_pages()
