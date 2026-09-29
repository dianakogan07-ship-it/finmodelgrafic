"""Пересчёт финмодели через Aspose.Cells.

Книга загружается один раз; перед расчётом в памяти правятся формулы,
которые Aspose считает не так, как русский Excel. Файл модели не меняется.
"""
import os
import re

# .NET внутри Aspose не находит ICU сам; без ICU кириллица сравнивается с учётом регистра
os.environ.setdefault("CLR_ICU_VERSION_OVERRIDE", "74.2")

import aspose.cells as ac  # noqa: E402

# SUM('1:<'!X23) — 3D-ссылка по диапазону листов
R3D = re.compile(r"'([^']+):([^']+)'!(\$?[A-Z]{1,3}\$?\d+(?::\$?[A-Z]{1,3}\$?\d+)?)")
# CELL("ИМЯФАЙЛА";A1) — русский аргумент, Aspose понимает только "filename"
RCELL = re.compile(r'CELL\("ИМЯФАЙЛА"', re.I)
# INDIRECT(E195&"!"&...) — лист «1» без кавычек: Excel принимает, Aspose нет
RIND = re.compile(r'INDIRECT\((\$?[A-Z]{1,3}\$?\d+)&"!"')


def _q(name):
    return "'" + name.replace("'", "''") + "'"


def load(path):
    """Возвращает (workbook, число исправленных формул, кэш значений Excel по формулам)."""
    lo = ac.LoadOptions()
    lo.region = ac.CountryCode.RUSSIA  # критерии вида ">0,00000001"
    wb = ac.Workbook(path, lo)
    wb.settings.region = ac.CountryCode.RUSSIA
    names = [wb.worksheets[i].name for i in range(len(wb.worksheets))]

    def expand(m):
        a, b = names.index(m.group(1)), names.index(m.group(2))
        return ",".join(f"{_q(n)}!{m.group(3)}" for n in names[a:b + 1])

    fixed, cache = 0, {}
    for i in range(len(wb.worksheets)):
        ws = wb.worksheets[i]
        for c in ws.cells:
            if not c.is_formula:
                continue
            f = g = c.formula
            cache[(ws.name, c.name)] = c.value
            if ":" in g and R3D.search(g):
                g = R3D.sub(expand, g)
            if "CELL(" in g.upper():
                g = RCELL.sub('CELL("filename"', g)
            if "INDIRECT(" in g:
                g = RIND.sub(lambda m: 'INDIRECT("\'"&' + m.group(1) + '&"\'!"', g)
            if g != f:
                c.formula = g
                fixed += 1
    return wb, fixed, cache


def get(wb, sheet, addr):
    return wb.worksheets.get(sheet).cells.get(addr).value


def put(wb, sheet, addr, value):
    wb.worksheets.get(sheet).cells.get(addr).put_value(value)


def calculate(wb):
    wb.calculate_formula()
