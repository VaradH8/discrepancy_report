"""
Regenerate equipment_registered.txt from the master Excel file.

The register is the YELLOW-highlighted subset of column D (EquipmentName) in
"Equipment List to Inventive 1.xlsx". Highlighting can't survive a CSV export,
so we read the .xlsx directly and keep only cells with a solid yellow fill.

Usage:
    python tools/extract_register.py "C:\\path\\to\\Equipment List to Inventive 1.xlsx"

Writes backend/equipment_registered.txt (one EquipmentName per line, sorted, unique).
"""
import os, sys
import openpyxl

YELLOW = "FFFFFF00"           # solid fill argb used for the highlighted cells
HEADER = "EquipmentName"
OUT = os.path.join(os.path.dirname(__file__), "..", "equipment_registered.txt")


def extract(xlsx_path):
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    ws = wb.active
    header = [str(c.value).strip() if c.value is not None else "" for c in ws[1]]
    col = header.index(HEADER) + 1  # 1-based column index of EquipmentName
    names = []
    for r in range(2, ws.max_row + 1):
        c = ws.cell(r, col)
        if c.fill.patternType == "solid" and getattr(c.fill.fgColor, "rgb", None) == YELLOW:
            v = str(c.value).strip() if c.value is not None else ""
            if v:
                names.append(v)
    return sorted(set(names)), len(names)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(f"usage: python {sys.argv[0]} <Equipment List to Inventive 1.xlsx>")
    uniq, total = extract(sys.argv[1])
    out = os.path.normpath(OUT)
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(uniq) + "\n")
    print(f"highlighted cells: {total}  unique written: {len(uniq)}  -> {out}")
