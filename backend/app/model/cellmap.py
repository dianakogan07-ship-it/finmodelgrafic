from functools import lru_cache

import yaml
from openpyxl.utils import column_index_from_string, get_column_letter

from .. import settings


@lru_cache
def cell_map() -> dict:
    with open(settings.CELL_MAP, encoding="utf-8") as f:
        return yaml.safe_load(f)


def col_idx(letter: str) -> int:
    """'A' → 1"""
    return column_index_from_string(letter)


def col_letter(idx: int) -> str:
    return get_column_letter(idx)
