# doc_loader.py: reads the input files
#   guide (PDF/image) -> text + images for the LLM
#   data (Excel/CSV)  -> pandas DataFrame + column summary for the LLM
import json
import logging
import re
import shutil
from pathlib import Path
from typing import Literal

import pandas as pd
import pymupdf

from data_agent import config
from data_agent.custom_types import InputBundle, SheetSummary

logger = logging.getLogger(__name__)

GUIDE_EXTENSIONS = {'.pdf', '.png', '.jpg', '.jpeg', '.webp'}
DATA_EXTENSIONS = {'.xlsx', '.csv'}
SAMPLE_ROWS = 5          # example rows given to the LLM (not all the data!)
MIN_TEXT_CHARS = 50      # pages with less text than this are treated as scans
RENDER_DPI = 110         # resolution when rendering PDF pages to images


def classify(filename: str) -> Literal['guide', 'data'] | None:
    # guess the file type from its extension
    ext = Path(filename).suffix.lower()
    if ext in GUIDE_EXTENSIONS:
        return 'guide'
    if ext in DATA_EXTENSIONS:
        return 'data'
    return None


def normalize_column(name: object) -> str:
    # "String Length (m)" -> "string_length_m"
    # so column names are safe to use in formulas (no spaces / symbols)
    text = str(name).strip().lower()
    text = re.sub(r'[^0-9a-z]+', '_', text).strip('_')
    if not text:
        text = 'column'
    if text[0].isdigit():
        text = f'c_{text}'
    return text


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    seen: dict[str, int] = {}
    new_names = []
    for col in df.columns:
        name = normalize_column(col)
        if name in seen:  # duplicate name -> add a number: value, value_2
            seen[name] += 1
            name = f'{name}_{seen[name]}'
        else:
            seen[name] = 1
        new_names.append(name)
    df = df.copy()
    df.columns = new_names
    return df


def read_data(path: str) -> dict[str, pd.DataFrame]:
    # return {sheet_name: DataFrame}; a CSV counts as one sheet named "data"
    p = Path(path)
    if p.suffix.lower() == '.csv':
        sheets = {'data': pd.read_csv(p)}
    else:
        sheets = pd.read_excel(p, sheet_name=None)  # None = read all sheets
    return {
        normalize_column(name): _normalize_columns(df.dropna(how='all'))
        for name, df in sheets.items()
    }


def summarize_sheets(sheets: dict[str, pd.DataFrame]) -> list[SheetSummary]:
    summaries = []
    for name, df in sheets.items():
        # to_json -> json.loads: easy way to turn numpy/NaN types into plain JSON types
        sample = json.loads(df.head(SAMPLE_ROWS).to_json(orient='records'))
        summaries.append(SheetSummary(
            name=name,
            columns=list(df.columns),
            dtypes={col: str(dtype) for col, dtype in df.dtypes.items()},
            n_rows=len(df),
            sample_rows=sample,
        ))
    return summaries


def load_guide(path: str, out_dir: Path) -> tuple[str, list[str]]:
    # PDF -> extract the text; scanned / image pages are also rendered to PNG
    # image (photo) -> used as is
    p = Path(path)
    if p.suffix.lower() != '.pdf':
        return '', [str(p)]

    texts: list[str] = []
    images: list[str] = []
    with pymupdf.open(p) as doc:
        for i, page in enumerate(doc):
            if i >= config.MAX_GUIDE_PAGES:
                logger.warning('guide %s truncated at %s pages', p.name, config.MAX_GUIDE_PAGES)
                break
            text = page.get_text().strip()
            if text:
                texts.append(f'--- {p.name} page {i + 1} ---\n{text}')
            if len(text) < MIN_TEXT_CHARS or page.get_images():
                img_path = out_dir / f'{p.stem}_page{i + 1}.png'
                page.get_pixmap(dpi=RENDER_DPI).save(img_path)
                images.append(str(img_path))
    return '\n\n'.join(texts), images


def load_inputs(guide_paths: list[str], data_path: str, work_dir: str) -> InputBundle:
    out_dir = Path(work_dir) / 'rendered'
    shutil.rmtree(out_dir, ignore_errors=True)  # clear leftovers from the previous run (on retry)
    out_dir.mkdir(parents=True)

    all_text: list[str] = []
    all_images: list[str] = []
    for gp in guide_paths:
        text, images = load_guide(gp, out_dir)
        if text:
            all_text.append(text)
        all_images.extend(images)

    sheets = read_data(data_path)
    logger.info('input: %s guide(s), %s image(s), sheets=%s',
                len(guide_paths), len(all_images), list(sheets))
    return InputBundle(
        guide_text='\n\n'.join(all_text),
        guide_images=all_images,
        data_path=data_path,
        sheets=summarize_sheets(sheets),
    )
