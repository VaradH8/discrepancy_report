# DWG Discrepancy

Upload two DWG drawings (issued reference + new candidate), get the equipment
discrepancy spreadsheet — the same `.xlsx` used to drive revision clouding.

This is the validated notebook pipeline wrapped as a small web service.

---

## What it does

1. Accepts two `.dwg` files (reference + candidate) via a web form.
2. Converts each DWG → DXF server-side (LibreDWG).
3. Extracts equipment tags + datum-point positions with `ezdxf`.
4. Diffs them: **present-in-both / added / removed**, and detects whether the
   candidate is a full layout (movement computable) or a schedule extract.
5. Returns a formatted `.xlsx` (Discrepancy + Summary sheets).

## Architecture

```
 Browser (frontend/index.html)
    │  POST /compare   reference.dwg + candidate.dwg
    ▼
 FastAPI (backend/app.py)
    │  calls
    ▼
 pipeline.compare()  (backend/pipeline.py)
    ├─ dwg2dxf   (LibreDWG native binary)   ← the only non-Python dependency
    ├─ ezdxf     (tag + datum extraction)
    └─ openpyxl  (formatted workbook)
    ▼
 .xlsx download  (+ X-Both / X-Added / X-Removed / X-Movement headers)
```

**Why a backend at all:** browsers cannot read DWG, and conversion needs a
native binary. Everything else is pure Python.

## Run it (Docker — recommended)

The Dockerfile compiles LibreDWG in a build stage, so there is nothing to
install by hand.

```bash
docker build -t dwg-discrepancy .
docker run -p 8000:8000 dwg-discrepancy
# open http://localhost:8000
```

## Run it (local dev)

Requires the `dwg2dxf` binary (LibreDWG) on PATH. On Debian/Ubuntu you can
build it from source (see the Dockerfile's build stage), or install ODA File
Converter and adapt `pipeline.dwg_to_dxf`.

```bash
pip install -r backend/requirements.txt
cd backend
uvicorn app:app --reload --port 8000
```

## API

`POST /compare` — multipart form:
- `reference` : issued/baseline `.dwg`
- `candidate` : new/candidate `.dwg`
- `sheet`     : sheet label (e.g. `SHT_01`)

Returns the `.xlsx` as a download. Summary is mirrored in response headers
(`X-Both`, `X-Added`, `X-Removed`, `X-Movement`).

`POST /crosscheck` — multipart form (cross-reference report, chained from a `/compare`):
- `drawings` : every drawing in the set to check against (repeated `.dwg` files)
- `tags`     : JSON `[{"tag":"P-1001","status":"ADDED"}, ...]` — the added/removed register from a comparison
- `origins`  : JSON list of the original reference/candidate filenames (matches there are flagged `[origin]`, excluded from "exists elsewhere")
- `sheet`    : sheet label for the output filename

For each added/removed tag it reports whether the tag appears in any *other* sheet
(`exists elsewhere`) or is globally new / globally removed. Returns a formatted
`.xlsx` (Cross-Reference + Summary sheets); a slim per-tag result list is mirrored in
the `X-Results` header (`X-New`, `X-Removed-Global`, `X-Sheets` carry the counts).

## Deploy

Production deploy (own VM, public domain, auto-HTTPS via Caddy): see [`deploy/`](deploy/README.md).

## DWG converter options

| Converter | Cost | Robustness | Notes |
|-----------|------|------------|-------|
| LibreDWG (default) | free | good | cannot read OLE-embedded drawings inside a DWG |
| ODA File Converter | free binary | very good | redistribution needs ODA terms |
| Autodesk Platform Services (Model Derivative) | paid | excellent | cloud API, no local binary |

Swap by editing `pipeline.dwg_to_dxf`.

## Known limitation (matters for this dataset)

If the candidate DWG is an **auto-generated schedule/annotation extract**
(tags listed in columns, no datum-point blocks, geometry locked in an
OLE-embedded object), spatial **movement cannot be computed** — only the
added/removed register is reliable. The Summary sheet states this per run.
For movement + clouding, the candidate must be a **full layout** DWG
(equipment drawn in plan, with `KBR_CONTROL POINT_DATUM` markers) like the
issued REV_B files.

## Next step (not yet wired)

When both sides are full layouts, add a `/cloud` endpoint that takes the
discrepancy `.xlsx` and writes revision clouds into the candidate DWG/DXF on a
dedicated layer — the cloud-generation code is already proven separately.
