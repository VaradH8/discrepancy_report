import os, sys, re, time, glob, csv, tempfile, subprocess
sys.path.insert(0, r"C:\Users\Varad\Downloads\dwg-discrepancy-app\app\backend")
import pipeline
ODA=r"C:\Program Files\ODA\ODAFileConverter 27.1.0\ODAFileConverter.exe"

# NEW RULE: allow-list = the WHOLE EquipmentName column of the latest list (not the yellow subset)
allow=set()
with open(r"C:\Users\Varad\Downloads\Equipment List to Inventive (4).csv", encoding="cp1252", errors="replace") as f:
    r=csv.reader(f); hdr=next(r); i=hdr.index("EquipmentName")
    for row in r:
        if len(row)>i and row[i].strip(): allow.add(pipeline._norm(row[i]))

JOBS=[
 dict(name="M10A", tag="C_to_D",
      issued=r"C:\Users\Varad\Downloads\M10A REV C\M10A",
      new=r"C:\Users\Varad\Downloads\M10A rev D\M10A\M10A"),
 dict(name="M10C", tag="C_to_D",
      issued=r"C:\Users\Varad\Downloads\M10C REV C\M10C",
      new=r"C:\Users\Varad\Downloads\M10C rev D\M10C\M10C"),
 dict(name="M01", tag="B_to_C",
      issued=r"C:\Users\Varad\Downloads\M01\M01 - Copy\M01 REV B",
      new=r"C:\Users\Varad\Downloads\M01\M01 - Copy\M01 Extraction file"),
 dict(name="M07B", tag="B_to_C",
      issued=r"C:\Users\Varad\Downloads\M07B 1\M07B - Copy\M07B REV B",
      new=r"C:\Users\Varad\Downloads\M07B 1\M07B - Copy\M07B EXTRACT FILE"),
]
outroot=r"C:\Users\Varad\Music\registered"; os.makedirs(outroot,exist_ok=True)
log=open(os.path.join(outroot,"_progress.log"),"w",encoding="utf-8")
def say(*a):
    m=" ".join(str(x) for x in a); print(m,flush=True); log.write(m+"\n"); log.flush()
say("allow-list = FULL column of Equipment List to Inventive (4).csv:", len(allow), "names")
def convert(src):
    out=tempfile.mkdtemp(prefix="oda_")
    subprocess.run([ODA,src,out,"ACAD2018","DXF","0","1","*.DWG"],capture_output=True,text=True,timeout=3000)
    return sorted(set(glob.glob(os.path.join(out,"*.dxf"))+glob.glob(os.path.join(out,"*.DXF"))))
for job in JOBS:
    outdir=os.path.join(outroot,job["name"]); os.makedirs(outdir,exist_ok=True)
    say(f"\n===== {job['name']} ({job['tag']}) =====")
    t=time.time(); Bf=convert(job["issued"]); say(f"converted issued: {len(Bf)} dxf ({time.time()-t:.0f}s)")
    t=time.time(); Cf=convert(job["new"]);    say(f"converted new:    {len(Cf)} dxf ({time.time()-t:.0f}s)")
    B={}; C={}
    for f in Bf:
        n=pipeline.sheet_no_from_name(os.path.basename(f))
        if n and n not in B: B[n]=set(pipeline._scan(f)[0])
    for f in Cf:
        n=pipeline.sheet_no_from_name(os.path.basename(f))
        if n and n not in C: C[n]=set(pipeline._scan(f)[0])
    B_sheets={}
    for n,s in B.items():
        for tg in s: B_sheets.setdefault(tg,set()).add(n)
    un_i, un_c = sorted(set(B)-set(C)), sorted(set(C)-set(B))
    if un_i or un_c: say("unpaired issued:",un_i,"| unpaired candidate:",un_c)
    say("SHEET  RAW(add/rem/both)   REG(gA lA gR lR both kept)")
    for n in sorted(set(B)&set(C)):
        Bn,Cn=B[n],C[n]
        both,added,removed=Bn&Cn,Cn-Bn,Bn-Cn
        def scope(tg,status):
            if status=="ADDED":  return "LOCALLY ADDED" if tg in B_sheets else "GLOBALLY ADDED"
            return "LOCALLY REMOVED" if (B_sheets.get(tg,set())-{n}) else "GLOBALLY REMOVED"
        rows=[]; groups={k:[] for k in pipeline.SCOPE_LABELS}
        for tg in sorted(Bn|Cn):
            if pipeline._norm(tg) not in allow: continue
            r={k:"" for k in pipeline.COLS}; r["EquipmentName"]=tg; r["Sheet"]=f"SHT_{n}"
            if tg in both: r["Status"]="PRESENT IN BOTH"; r["Notes"]="Present in both revisions."
            elif tg in added:
                lab=scope(tg,"ADDED"); r["Status"]=lab; groups[lab].append(tg)
                r["Notes"]=("Also elsewhere in issued set." if lab.startswith("LOC") else "New in the new revision."); r["Match_Confidence"]="HIGH (tag-set)"
            else:
                lab=scope(tg,"REMOVED"); r["Status"]=lab; groups[lab].append(tg)
                r["Notes"]=("Still on other issued sheets." if lab.startswith("LOC") else "Gone from issued set."); r["Match_Confidence"]="HIGH (tag-set)"
            rows.append(r)
        for k in groups: groups[k]=sorted(groups[k])
        nboth=sum(1 for r in rows if r["Status"]=="PRESENT IN BOTH")
        stats=dict(both=nboth,added=sorted(r["EquipmentName"] for r in rows if "ADDED" in r["Status"]),
                   removed=sorted(r["EquipmentName"] for r in rows if "REMOVED" in r["Status"]),
                   ref_geom=0,cand_geom=0,ref_datums=0,cand_datums=0,movement_ok=False,warning="",scope=groups)
        pipeline._write(rows,stats,f"SHT_{n}",os.path.join(outdir,f"SHT-{n}_Registered_{job['tag']}.xlsx"))
        g=groups
        say(f"SHT-{n}  raw({len(added)}/{len(removed)}/{len(both)})   REG(gA={len(g['GLOBALLY ADDED'])} lA={len(g['LOCALLY ADDED'])} gR={len(g['GLOBALLY REMOVED'])} lR={len(g['LOCALLY REMOVED'])} both={nboth} kept={len(rows)})")
say("\nALL DONE ->", outroot)
log.close()
