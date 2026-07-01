"""
DWG Discrepancy — web service.
Serves the frontend and exposes POST /compare which runs the validated pipeline
(DWG->DXF via LibreDWG, tag/datum extraction, diff) and returns a formatted .xlsx.
"""
import os, json, tempfile
from typing import List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from pipeline import compare, cross_reference, compare_registered, load_master

app = FastAPI(title="DWG Discrepancy")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

HERE = os.path.dirname(__file__)
FRONTEND = os.path.normpath(os.path.join(HERE, "..", "frontend", "index.html"))


@app.get("/", response_class=HTMLResponse)
def index():
    with open(FRONTEND, encoding="utf-8") as f:
        return f.read()


@app.get("/health")
def health():
    import shutil
    return {"ok": True, "dwg2dxf": bool(shutil.which("dwg2dxf")), "master_count": len(load_master())}


def _save(upload: UploadFile, folder: str) -> str:
    if not upload.filename.lower().endswith(".dwg"):
        raise HTTPException(400, f"{upload.filename}: expected a .dwg file")
    path = os.path.join(folder, os.path.basename(upload.filename))
    with open(path, "wb") as f:
        f.write(upload.file.read())
    return path


@app.post("/compare")
def compare_endpoint(
    reference: UploadFile = File(..., description="Issued / baseline DWG"),
    candidate: UploadFile = File(..., description="New / candidate DWG"),
    sheet: str = Form("SHT"),
):
    """Returns the discrepancy .xlsx as a download, with a summary in headers."""
    tmp = tempfile.mkdtemp(prefix="dwgcmp_")
    try:
        ref = _save(reference, tmp)
        cand = _save(candidate, tmp)
        out = os.path.join(tmp, f"{sheet}_Discrepancy.xlsx")
        try:
            xlsx, stats = compare(ref, cand, sheet_name=sheet, out_xlsx=out)
        except RuntimeError as e:
            raise HTTPException(422, str(e))
        return FileResponse(
            xlsx,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=f"{sheet}_Discrepancy.xlsx",
            headers={
                "X-Both": str(stats["both"]),
                "X-Added": ",".join(stats["added"]) or "-",
                "X-Removed": ",".join(stats["removed"]) or "-",
                "X-Pos": json.dumps({**stats["added_pos"], **stats["removed_pos"]}, separators=(",", ":")),
                "X-Movement": "yes" if stats["movement_ok"] else "no",
                "X-Warning": stats.get("warning", "") or "-",
                "Access-Control-Expose-Headers": "X-Both,X-Added,X-Removed,X-Pos,X-Movement,X-Warning",
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/registered")
def registered_endpoint(
    reference: UploadFile = File(..., description="Issued / baseline DWG"),
    candidate: UploadFile = File(..., description="New / candidate DWG"),
    sheet: str = Form("SHT"),
    scope: str = Form("{}", description='JSON {EquipmentName: "GLOBALLY ADDED"|...} from the cross-reference'),
):
    """Same discrepancy diff as /compare, but rows whose EquipmentName is not in
    the bundled master register (Equipment List to Inventive) are dropped, and
    each ADDED/REMOVED row's Status is replaced by the cross-reference verdict
    (GLOBALLY/LOCALLY ADDED|REMOVED) supplied in `scope`."""
    try:
        scope_map = json.loads(scope)
    except (ValueError, TypeError) as e:
        raise HTTPException(400, f"bad scope JSON: {e}")
    tmp = tempfile.mkdtemp(prefix="dwgreg_")
    try:
        ref = _save(reference, tmp)
        cand = _save(candidate, tmp)
        out = os.path.join(tmp, f"{sheet}_Discrepancy_Registered.xlsx")
        try:
            xlsx, stats, dropped = compare_registered(
                ref, cand, sheet_name=sheet, out_xlsx=out, scope=scope_map)
        except RuntimeError as e:
            raise HTTPException(422, str(e))
        return FileResponse(
            xlsx,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=f"{sheet}_Discrepancy_Registered.xlsx",
            headers={
                "X-Kept": str(stats["kept"]),
                "X-Dropped": str(stats["dropped"]),
                "X-Master": str(stats["master_count"]),
                "X-Both": str(stats["both"]),
                "X-Added": ",".join(stats["added"]) or "-",
                "X-Removed": ",".join(stats["removed"]) or "-",
                "X-Scope": json.dumps(stats["scope"], separators=(",", ":")),
                "X-Dropped-Names": json.dumps(dropped[:300], separators=(",", ":")),
                "Access-Control-Expose-Headers":
                    "X-Kept,X-Dropped,X-Master,X-Both,X-Added,X-Removed,X-Scope,X-Dropped-Names",
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/crosscheck")
def crosscheck_endpoint(
    drawings: List[UploadFile] = File(..., description="Every drawing in the set to check against"),
    tags: str = Form(..., description='JSON: [{"tag":"P-1001","status":"ADDED"}, ...]'),
    origins: str = Form("[]", description="JSON list of filenames that are the original reference/candidate"),
    positions: str = Form("{}", description='JSON {tag:[x,y]} positions carried from the comparison'),
    sheet: str = Form("SHT"),
):
    """
    Cross-reference each ADDED/REMOVED tag (from a prior /compare) against the whole
    drawing set. Returns an .xlsx; summary mirrored in headers.
    """
    try:
        tag_list = json.loads(tags)
        origin_names = {os.path.basename(o) for o in json.loads(origins)}
        pos_map = json.loads(positions)
    except (ValueError, TypeError) as e:
        raise HTTPException(400, f"bad tags/origins/positions JSON: {e}")
    if not tag_list:
        raise HTTPException(400, "no tags to cross-check — run a comparison first")
    if not drawings:
        raise HTTPException(400, "upload at least one drawing to check against")

    tmp = tempfile.mkdtemp(prefix="dwgxref_")
    try:
        items = []
        for up in drawings:
            path = _save(up, tmp)
            items.append((os.path.basename(up.filename), path))
        origin_list = json.loads(origins)
        origin_labels = [lbl for lbl, _ in items if lbl in origin_names]
        ref_name = os.path.basename(origin_list[0]) if len(origin_list) > 0 else None
        cand_name = os.path.basename(origin_list[1]) if len(origin_list) > 1 else None
        out = os.path.join(tmp, f"{sheet}_CrossReference.xlsx")
        try:
            xlsx, summary = cross_reference(
                tag_list, items, origin_labels,
                added_origin=cand_name, removed_origin=ref_name, sheet_label=sheet,
                home_pos_map=pos_map, out_xlsx=out)
        except RuntimeError as e:
            raise HTTPException(422, str(e))
        # Slim payload for the UI table — full positions live in the .xlsx.
        slim = [{
            "tag": r["tag"], "status": r["status"], "verdict": r["verdict"],
            "exists_elsewhere": r["exists_elsewhere"],
            "home": r["home_sheet"] + (f" @ ({r['home_pos'][0]},{r['home_pos'][1]})" if r["home_pos"] else ""),
            "found": [f"{sht}@({x},{y})" for sht, x, y in r["elsewhere"]],
        } for r in summary["results"]]
        return FileResponse(
            xlsx,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=f"{sheet}_CrossReference.xlsx",
            headers={
                "X-Results": json.dumps(slim, separators=(",", ":")),
                "X-New": str(summary["globally_new"]),
                "X-Removed-Global": str(summary["globally_removed"]),
                "X-Sheets": str(len(summary["drawings"])),
                "Access-Control-Expose-Headers": "X-Results,X-New,X-Removed-Global,X-Sheets",
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
