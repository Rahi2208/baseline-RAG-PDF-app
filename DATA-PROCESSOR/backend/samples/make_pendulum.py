# make_pendulum.py: builds the first sample (simple pendulum lab) for tests & evaluation
# run from the backend folder: uv run python samples/make_pendulum.py
import json
import math
from pathlib import Path

import pandas as pd
import pymupdf

OUT = Path(__file__).parent / 'pendulum'
OUT.mkdir(exist_ok=True)

# ---------- 1. raw data (Excel) ----------
data = pd.DataFrame({
    'Trial': [1, 2, 3, 4, 5],
    'String Length (m)': [0.3, 0.5, 0.7, 0.9, 1.1],
    'Time 10 Swings (s)': [11.02, 14.15, 16.83, 19.01, 21.10],
})
data.to_excel(OUT / 'data.xlsx', sheet_name='Data', index=False)

# ---------- 2. guide (PDF) ----------
GUIDE = """DATA PROCESSING GUIDE - SIMPLE PENDULUM LAB

The raw data is in the Excel file (sheet Data).

Processing steps:
1. Calculate the period of one swing: T = t / 10, where t = time for 10 swings.
2. Calculate the gravitational acceleration: g = 4 x pi^2 x L / T^2, where L = string length.
3. Round T and g to 3 decimal places.

Table 1 - Calculation Results, with columns in this order:
| Trial | L (m) | T (s) | g (m/s2) |

Table 2 - Summary, containing:
- mean g (rounded to 3 decimals)
- percent error against the literature g of 9.8 m/s2:
  error = |mean g - 9.8| / 9.8 x 100 (rounded to 2 decimals)
"""
doc = pymupdf.open()
page = doc.new_page()
page.insert_textbox(pymupdf.Rect(50, 50, 550, 800), GUIDE, fontsize=11)
doc.save(OUT / 'guide.pdf')

# ---------- 3. the correct answer (calculated by hand, NOT using the app) ----------
rows = []
for p, L, t in data.itertuples(index=False):
    T = round(t / 10, 3)
    g = round(4 * math.pi ** 2 * L / (t / 10) ** 2, 3)
    rows.append([p, L, T, g])
g_mean = round(sum(r[3] for r in rows) / len(rows), 3)
error = round(abs(g_mean - 9.8) / 9.8 * 100, 2)

expected = {'tables': [
    {'title': 'Calculation Results', 'columns': ['Trial', 'L (m)', 'T (s)', 'g (m/s2)'], 'rows': rows},
    {'title': 'Summary', 'columns': ['mean g', 'error (%)'], 'rows': [[g_mean, error]]},
]}
(OUT / 'expected.json').write_text(json.dumps(expected, indent=2))
print('sample created at', OUT)
