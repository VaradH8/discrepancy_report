import os, sys, re, time, glob, tempfile, subprocess
sys.path.insert(0, r"C:\Users\Varad\Downloads\dwg-discrepancy-app\app\backend")
import pipeline
ODA=r"C:\Program Files\ODA\ODAFileConverter 27.1.0\ODAFileConverter.exe"
JOBS=[
 dict(name="M01",
      issued=r"C:\Users\Varad\Downloads\M01\M01 - Copy\M01 REV B",
      new=r"C:\Users\Varad\Downloads\M01\M01 - Copy\M01 Extraction file",
      outbase=r"C:\Users\Varad\Downloads\M01_reports"),
 dict(name="M07B",
      issued=r"C:\Users\Varad\Downloads\M07B 1\M07B - Copy\M07B REV B",
      new=r"C:\Users\Varad\Downloads\M07B 1\M07B - Copy\M07B EXTRACT FILE",
      outbase=r"C:\Users\Varad\Downloads\M07B_reports"),
]
def convert(src):
    out=tempfile.mkdtemp(prefix="oda_")
    subprocess.run([ODA,src,out,"ACAD2018","DXF","0","1","*.DWG"],capture_output=True,text=True,timeout=3000)
    return sorted(set(glob.glob(os.path.join(out,"*.dxf"))+glob.glob(os.path.join(out,"*.DXF"))))
master=pipeline.load_master()
for job in JOBS:
    reg_out=os.path.join(job["outbase"],"registered_reports_B_to_C"); os.makedirs(reg_out,exist_ok=True)
    chg_out=os.path.join(job["outbase"],"changes_B_to_C"); os.makedirs(chg_out,exist_ok=True)
    log=open(os.path.join(reg_out,"_progress.log"),"w",encoding="utf-8")
    def say(*a):
        m=" ".join(str(x) for x in a); print(m,flush=True); log.write(m+"\n"); log.flush()
    say(f"===== {job['name']} ===== master:",len(master))
    t=time.time(); Bf=convert(job["issued"]); say(f"converted issued: {len(Bf)} dxf ({time.time()-t:.0f}s)")
    t=time.time(); Cf=convert(job["new"]);    say(f"converted new:    {len(Cf)} dxf ({time.time()-t:.0f}s)")
    B={}; C={}
    for f in Bf:
        n=pipeline.sheet_no_from_name(os.path.basename(f))
        if n and n not in B: t=time.time(); B[n]=set(pipeline._scan(f)[0]); say(f"  scan B SHT-{n}: {len(B[n])} ({time.time()-t:.0f}s)")
    for f in Cf:
        n=pipeline.sheet_no_from_name(os.path.basename(f))
        if n and n not in C: t=time.time(); C[n]=set(pipeline._scan(f)[0]); say(f"  scan C SHT-{n}: {len(C[n])} ({time.time()-t:.0f}s)")
    B_sheets={}
    for n,s in B.items():
        for tg in s: B_sheets.setdefault(tg,set()).add(n)
    say("unpaired issued:",sorted(set(B)-set(C)),"| unpaired candidate:",sorted(set(C)-set(B)))
    say("\nSHEET  RAW(add/rem/both)   REG(gA lA gR lR both kept)")
    for n in sorted(set(B)&set(C)):
        Bn,Cn=B[n],C[n]
        both,added,removed=Bn&Cn,Cn-Bn,Bn-Cn
        def scope(tg,status):
            if status=="ADDED":  return "LOCALLY ADDED" if tg in B_sheets else "GLOBALLY ADDED"
            return "LOCALLY REMOVED" if (B_sheets.get(tg,set())-{n}) else "GLOBALLY REMOVED"
        def build(fm):
            rows=[]; groups={k:[] for k in pipeline.SCOPE_LABELS}
            for tg in sorted(Bn|Cn):
                if fm and pipeline._norm(tg) not in master: continue
                r={k:"" for k in pipeline.COLS}; r["EquipmentName"]=tg; r["Sheet"]=f"SHT_{n}"
                if tg in both: r["Status"]="PRESENT IN BOTH"; r["Notes"]="Present in both revisions."
                elif tg in added:
                    lab=scope(tg,"ADDED"); r["Status"]=lab; groups[lab].append(tg)
                    r["Notes"]=("Also elsewhere in issued set." if lab.startswith("LOC") else "New in the extract."); r["Match_Confidence"]="HIGH (tag-set)"
                else:
                    lab=scope(tg,"REMOVED"); r["Status"]=lab; groups[lab].append(tg)
                    r["Notes"]=("Still on other issued sheets." if lab.startswith("LOC") else "Gone from issued set."); r["Match_Confidence"]="HIGH (tag-set)"
                rows.append(r)
            for k in groups: groups[k]=sorted(groups[k])
            return rows,groups
        for fm,folder,suffix in ((True,reg_out,"Registered"),(False,chg_out,"Changes")):
            rows,groups=build(fm)
            nboth=sum(1 for r in rows if r["Status"]=="PRESENT IN BOTH")
            stats=dict(both=nboth,added=sorted(r["EquipmentName"] for r in rows if "ADDED" in r["Status"]),
                       removed=sorted(r["EquipmentName"] for r in rows if "REMOVED" in r["Status"]),
                       ref_geom=0,cand_geom=0,ref_datums=0,cand_datums=0,movement_ok=False,warning="",scope=groups)
            pipeline._write(rows,stats,f"SHT_{n}",os.path.join(folder,f"SHT-{n}_{suffix}_B_to_C.xlsx"))
            if fm:
                g=groups
                say(f"SHT-{n}  raw({len(added)}/{len(removed)}/{len(both)})   REG(gA={len(g['GLOBALLY ADDED'])} lA={len(g['LOCALLY ADDED'])} gR={len(g['GLOBALLY REMOVED'])} lR={len(g['LOCALLY REMOVED'])} both={nboth} kept={len(rows)})")
    say(f"\n{job['name']} DONE ->",job["outbase"])
    log.close()
print("ALL MODULES DONE")
