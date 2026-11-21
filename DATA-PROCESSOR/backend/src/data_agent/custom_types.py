# custom_types.py: the "shape" of the data passed between steps
# Pydantic checks the shape automatically, so bad data is caught right away
from typing import Any, Literal

from pydantic import BaseModel


# ---------- 1. input after reading ----------
class SheetSummary(BaseModel):
    name: str                      # sheet name in the Excel file
    columns: list[str]             # column names (already cleaned up, see doc_loader)
    dtypes: dict[str, str]         # data type of each column
    n_rows: int
    sample_rows: list[dict[str, Any]]  # a few example rows for the LLM


class InputBundle(BaseModel):
    guide_text: str                # text from the guide (PDF)
    guide_images: list[str]        # image paths (guide photos / scanned PDF pages)
    data_path: str                 # path to the Excel/CSV file
    sheets: list[SheetSummary]


# ---------- 2. LLM output: list of instructions ----------
class Instructions(BaseModel):
    items: list[str]               # each instruction in the guide, one per item
    expected_tables: list[str]     # which tables the guide asks for


# ---------- 3. LLM output: processing plan ----------
OpName = Literal[
    'compute', 'filter', 'select', 'rename', 'sort',
    'round', 'group_agg', 'aggregate', 'linear_fit',
]
AggFunc = Literal['mean', 'sum', 'min', 'max', 'count', 'std', 'median']


class Aggregation(BaseModel):
    column: str                    # column to aggregate
    func: AggFunc                  # function: mean, sum, ...
    output: str                    # name of the resulting column


class RenamePair(BaseModel):
    old: str
    new: str


class Step(BaseModel):
    # one model for all ops (not one model per op),
    # so the schema stays simple and easy for a small local model to follow.
    # the required parameters per op are checked in operations.py
    op: OpName
    new_column: str | None = None          # compute
    expr: str | None = None                # compute (formula) / filter (condition)
    columns: list[str] | None = None       # select / round
    renames: list[RenamePair] | None = None  # rename
    by: list[str] | None = None            # sort / group_agg
    descending: bool | None = None         # sort
    decimals: int | None = None            # round
    aggregations: list[Aggregation] | None = None  # group_agg / aggregate
    x: str | None = None                   # linear_fit
    y: str | None = None                   # linear_fit


class TablePlan(BaseModel):
    id: str                        # unique id, e.g. "result_g"
    title: str                     # title to display
    source: str                    # sheet name OR the id of an earlier table
    steps: list[Step]


class Plan(BaseModel):
    tables: list[TablePlan]


# ---------- 4. final result ----------
class ResultTable(BaseModel):
    id: str
    title: str
    columns: list[str]
    rows: list[list[Any]]
    formulas: list[str]            # steps/formulas used, shown in the UI


class TableSet(BaseModel):
    tables: list[ResultTable]


class CheckItem(BaseModel):
    instruction: str
    done: bool
    note: str


class Review(BaseModel):
    items: list[CheckItem]


class JobResult(BaseModel):
    instructions: Instructions
    plan: Plan
    tables: list[ResultTable]
    review: Review
