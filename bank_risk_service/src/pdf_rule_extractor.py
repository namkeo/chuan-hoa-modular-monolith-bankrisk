"""Regulatory PDF scanning and candidate-rule extraction.

Scans every ``*.pdf`` in (and around) the project folder, extracts text with
PyMuPDF (fast) and pdfplumber (layout) and, when both yield little usable text,
flags ``PDF_PARSE_LOW_CONFIDENCE`` and optionally falls back to OCR
(``pytesseract`` + ``pdf2image``) if those are installed.

For pages with text it searches for the regulatory keywords required by the audit
spec (tỷ lệ an toàn vốn, LDR, nguồn vốn ngắn hạn cho vay trung-dài hạn, giới hạn
cấp tín dụng, trái phiếu Chính phủ, xếp hạng TCTD, …), pulls candidate numeric
thresholds, scores a confidence and writes ``outputs/exports/extracted_rules_review.csv``.

Crucially: candidates with confidence < 0.8 are written as ``REVIEW_REQUIRED`` and
are NEVER auto-applied. The curated ``config/regulatory_rules.yaml`` remains the
source of truth; this module exists to let the auditor cross-check those thresholds
against the actual legal text.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from .utils import DATA_ROOT, EXPORTS_DIR, LOG, normalize_label, strip_accents

# Keyword -> (canonical metric candidate, suggested rule_id) for matching.
KEYWORDS: list[tuple[str, str, str]] = [
    ("ty le an toan von toi thieu", "car_solo", "CAR_SOLO_MIN"),
    ("ty le an toan von cap 1", "car_tier1", "TIER1_MIN"),
    ("ty le an toan von", "car_solo", "CAR_SOLO_MIN"),
    ("ty le kha nang chi tra", "solvency_30d_vnd", "QD682_SOLVENCY_30D_VND"),
    ("ty le du tru thanh khoan", "liquidity_reserve_ratio", "LIQUIDITY_RESERVE_MIN"),
    ("nguon von ngan han", "st_funding_for_mlt_loans", "ST_FUNDING_MLT_LIMIT"),
    ("cho vay trung han va dai han", "st_funding_for_mlt_loans", "ST_FUNDING_MLT_LIMIT"),
    ("du no cho vay so voi tong tien gui", "ldr", "LDR_LIMIT"),
    ("ty le du no cho vay", "ldr", "LDR_LIMIT"),
    ("gioi han cap tin dung", "credit_limit", "CREDIT_LIMIT"),
    ("gop von, mua co phan", "capital_contribution_ratio", "CAPITAL_CONTRIBUTION_LIMIT"),
    ("gop von mua co phan", "capital_contribution_ratio", "CAPITAL_CONTRIBUTION_LIMIT"),
    ("trai phieu chinh phu", "govbond_ratio", "GOVBOND_INVEST_LIMIT"),
    ("xep hang to chuc tin dung", "rating", "RATING"),
    ("no xau", "npl_ratio", "NPL_RATIO_LIMIT"),
    ("no co cau", "restructured_debt", "RESTRUCTURED"),
    ("vamc", "vamc", "VAMC"),
    ("von chu so huu", "equity", "EQUITY"),
    ("tong tai san", "total_assets", "TOTAL_ASSETS"),
    ("nim", "nim", "NIM"),
]

# Percentage near a keyword, e.g. "8%", "85 %", "không thấp hơn 8%".
_PCT_RE = re.compile(r"(\d{1,3}(?:[.,]\d{1,2})?)\s*%")


@dataclass
class PdfExtractResult:
    candidates: pd.DataFrame
    file_status: pd.DataFrame = field(default_factory=pd.DataFrame)
    csv_path: str | None = None


# --------------------------------------------------------------------------- #
# Text extraction
# --------------------------------------------------------------------------- #
def _extract_pages_pymupdf(path: Path) -> list[str]:
    try:
        import fitz  # PyMuPDF
    except ImportError:
        return []
    out = []
    try:
        doc = fitz.open(path)
        for page in doc:
            out.append(page.get_text() or "")
        doc.close()
    except Exception as exc:  # noqa: BLE001
        LOG.warning("PyMuPDF failed on %s: %s", path.name, exc)
    return out


def _extract_pages_pdfplumber(path: Path) -> list[str]:
    try:
        import pdfplumber
    except ImportError:
        return []
    out = []
    try:
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                out.append(page.extract_text() or "")
    except Exception as exc:  # noqa: BLE001
        LOG.warning("pdfplumber failed on %s: %s", path.name, exc)
    return out


def _ocr_pages(path: Path, max_pages: int = 40) -> list[str]:
    """Optional OCR fallback. Returns [] if OCR stack is unavailable."""
    try:
        import fitz  # render to image
        import pytesseract
        from PIL import Image
        import io
    except ImportError:
        LOG.info("OCR stack (pytesseract/Pillow) not installed — skipping OCR for %s", path.name)
        return []
    out = []
    try:
        doc = fitz.open(path)
        for i, page in enumerate(doc):
            if i >= max_pages:
                break
            pix = page.get_pixmap(dpi=200)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            out.append(pytesseract.image_to_string(img, lang="vie") or "")
        doc.close()
    except Exception as exc:  # noqa: BLE001
        LOG.warning("OCR failed on %s: %s", path.name, exc)
        return []
    return out


def _looks_garbled(text: str) -> bool:
    """Heuristic: detect non-unicode (TCVN3/VNI) font garbling.

    Garbled Vietnamese PDFs decode to ASCII-ish noise with almost no real
    diacritics and many implausible letter clusters. We check the share of
    recognizable Vietnamese keywords after de-accenting.
    """
    if not text or len(text) < 50:
        return True
    norm = normalize_label(text)
    hits = sum(1 for kw, _, _ in KEYWORDS if kw in norm)
    # Real legal text hits several keywords; garbled text hits ~none.
    common = sum(norm.count(w) for w in ("ngan hang", "to chuc tin dung", "dieu",
                                         "thong tu", "ty le", "quy dinh"))
    return hits == 0 and common < 2


# --------------------------------------------------------------------------- #
# Candidate extraction
# --------------------------------------------------------------------------- #
def _candidates_from_text(text: str, pdf_file: str, page_no: int) -> list[dict]:
    """Find keyword sentences and any nearby % threshold."""
    rows = []
    # Split into sentence-ish chunks.
    chunks = re.split(r"(?<=[\.\n;])\s+", text)
    for chunk in chunks:
        norm = normalize_label(chunk)
        for kw, metric, rule_id in KEYWORDS:
            if kw in norm:
                pct = _PCT_RE.search(chunk)
                threshold = None
                if pct:
                    threshold = float(pct.group(1).replace(",", "."))
                # Confidence: keyword + explicit % near it is the strongest.
                conf = 0.55
                if threshold is not None:
                    conf += 0.20
                if any(w in norm for w in ("toi thieu", "toi da", "khong thap hon",
                                           "khong vuot qua", "khong duoc thap hon")):
                    conf += 0.15
                conf = round(min(conf, 0.95), 2)
                rows.append({
                    "pdf_file": pdf_file, "page": page_no + 1,
                    "extracted_text": chunk.strip()[:400],
                    "candidate_metric": metric,
                    "candidate_threshold": threshold,
                    "confidence": conf,
                    "suggested_rule_id": rule_id,
                    "status": "REVIEW_REQUIRED" if conf < 0.8 else "CANDIDATE_OK",
                })
                break  # one keyword per chunk is enough
    return rows


# --------------------------------------------------------------------------- #
# Public entry point
# --------------------------------------------------------------------------- #
def extract_rules_from_pdfs(pdf_paths: list[Path], use_ocr: bool = False,
                            write_csv: bool = True) -> PdfExtractResult:
    """Extract candidate rules from a list of PDFs.

    Returns candidate rows + a per-file status table. Always writes the review CSV
    (even if empty) so the auditor has a single artifact to check.
    """
    all_candidates: list[dict] = []
    file_rows: list[dict] = []

    for path in pdf_paths:
        pages = _extract_pages_pymupdf(path)
        if not any(p.strip() for p in pages):
            pages = _extract_pages_pdfplumber(path)
        total_chars = sum(len(p.strip()) for p in pages)
        pages_with_text = sum(1 for p in pages if p.strip())

        garbled = False
        if pages_with_text:
            sample = "\n".join(pages[:8])
            garbled = _looks_garbled(sample)

        status = "OK"
        if total_chars == 0:
            status = "PDF_PARSE_LOW_CONFIDENCE (scanned image — cần OCR)"
        elif garbled:
            status = "PDF_PARSE_LOW_CONFIDENCE (font không Unicode — TCVN3/VNI)"

        # OCR fallback when requested and text is unusable.
        if use_ocr and (total_chars == 0 or garbled):
            LOG.info("Attempting OCR on %s", path.name)
            ocr_pages = _ocr_pages(path)
            if any(p.strip() for p in ocr_pages):
                pages = ocr_pages
                total_chars = sum(len(p.strip()) for p in pages)
                pages_with_text = sum(1 for p in pages if p.strip())
                garbled = _looks_garbled("\n".join(pages[:8]))
                status = "OCR_APPLIED" + (" (vẫn thấp tin cậy)" if garbled else "")

        n_candidates = 0
        if total_chars > 0 and not garbled:
            for i, ptext in enumerate(pages):
                cands = _candidates_from_text(ptext, path.name, i)
                all_candidates.extend(cands)
                n_candidates += len(cands)

        file_rows.append({
            "pdf_file": path.name, "n_pages": len(pages),
            "pages_with_text": pages_with_text, "total_chars": total_chars,
            "status": status, "n_candidates": n_candidates,
            "path": str(path),
        })
        LOG.info("PDF %s: %s | %d candidates", path.name, status, n_candidates)

    cand_cols = ["pdf_file", "page", "extracted_text", "candidate_metric",
                 "candidate_threshold", "confidence", "suggested_rule_id", "status"]
    candidates = pd.DataFrame(all_candidates, columns=cand_cols)
    if not candidates.empty:
        candidates = candidates.sort_values(["confidence", "pdf_file", "page"],
                                            ascending=[False, True, True])
    file_status = pd.DataFrame(file_rows)

    csv_path = None
    if write_csv:
        csv_path = str(EXPORTS_DIR / "extracted_rules_review.csv")
        candidates.to_csv(csv_path, index=False, encoding="utf-8-sig")
        file_status.to_csv(EXPORTS_DIR / "pdf_parse_status.csv", index=False,
                           encoding="utf-8-sig")
        LOG.info("Wrote candidate review CSV -> %s (%d rows)", csv_path, len(candidates))

    return PdfExtractResult(candidates=candidates, file_status=file_status,
                            csv_path=csv_path)


if __name__ == "__main__":
    from .data_loader import scan_pdf_files
    root = DATA_ROOT
    pdfs = scan_pdf_files(root)
    print("Found PDFs:", [p.name for p in pdfs])
    res = extract_rules_from_pdfs(pdfs, use_ocr=False)
    print(res.file_status.to_string())
    print("\nCandidates:", len(res.candidates))
    if not res.candidates.empty:
        print(res.candidates.head(15).to_string())
