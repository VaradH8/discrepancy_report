import os, sys, re, time, glob, tempfile, subprocess
sys.path.insert(0, r"C:\Users\Varad\Downloads\dwg-discrepancy-app\app\backend")
import pipeline
ODA=r"C:\Program Files\ODA\ODAFileConverter 27.1.0\ODAFileConverter.exe"
issued_dir=r"C:\Users\Varad\Downloads\M10A REV C\M10A"        # REV C = issued
new_dir   =r"C:\Users\Varad\Downloads\M10A rev D\M10A\M10A"   # REV D = new
outbase=r"C:\Users\Varad\Downloads\M10A_reports"
reg_out=os.path.join(outbase,"registered_reports_C_to_D"); os.makedirs(reg_out,exist_ok=True)
chg_out=os.path.join(outbase,"changes_C_to_D"); os.makedirs(chg_out,exist_ok=True)
log=open(os.path.join(reg_out,"_progress.log"),"w",encoding="utf-8")
def say(*a):
    m=" ".join(str(x) for x in a); print(m,flush=True); log.write(m+"\n"); log.flush()
def convert(src):
    out=tempfile.mkdtemp(prefix="oda_")
    subprocess.run([ODA,src,out,"ACAD2018","DXF","0","1","*.DWG"],capture_output=True,text=True,timeout=3000)
    return sorted(set(glob.glob(os.path.join(out,"*.dxf"))+glob.glob(os.path.join(out,"*.DXF"))))
def tagset(path): return set(pipeline._scan(path)[0])
master=pipeline.load_master(); say("master register:",len(master))
t=time.time(); Bf=convert(issued_dir); say(f"converted REV C (issued): {len(Bf)} dxf ({time.time()-t:.0f}s)")
t=time.time(); Cf=convert(new_dir);    say(f"converted REV D (new):    {len(Cf)} dxf ({time.time()-t:.0f}s)")
B={}; C={}
for f in Bf:
    n=pipeline.sheet_no_from_name(os.path.basename(f))
    if n and n not in B: t=time.time(); B[n]=tagset(f); say(f"  scan C(issued) SHT-{n}: {len(B[n])} ({time.time()-t:.0f}s)")
for f in Cf:
    n=pipeline.sheet_no_from_name(os.path.basename(f))
    if n and n not in C: t=time.time(); C[n]=tagset(f); say(f"  scan D(new)    SHT-{n}: {len(C[n])} ({time.time()-t:.0f}s)")
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
            if tg in both: r["Status"]="PRESENT IN BOTH"; r["Notes"]="Present in both REV C and REV D."
            elif tg in added:
                lab=scope(tg,"ADDED"); r["Status"]=lab; groups[lab].append(tg)
                r["Notes"]=("Also elsewhere in REV C." if lab.startswith("LOC") else "New in REV D."); r["Match_Confidence"]="HIGH (tag-set)"
            else:
                lab=scope(tg,"REMOVED"); r["Status"]=lab; groups[lab].append(tg)
                r["Notes"]=("Still on other REV C sheets." if lab.startswith("LOC") else "Gone from REV C set."); r["Match_Confidence"]="HIGH (tag-set)"
            rows.append(r)
        for k in groups: groups[k]=sorted(groups[k])
        return rows,groups
    for fm,folder,suffix in ((True,reg_out,"Registered"),(False,chg_out,"Changes")):
        rows,groups=build(fm)
        nboth=sum(1 for r in rows if r["Status"]=="PRESENT IN BOTH")
        stats=dict(both=nboth,added=sorted(r["EquipmentName"] for r in rows if "ADDED" in r["Status"]),
                   removed=sorted(r["EquipmentName"] for r in rows if "REMOVED" in r["Status"]),
                   ref_geom=0,cand_geom=0,ref_datums=0,cand_datums=0,movement_ok=False,warning="",scope=groups)
        pipeline._write(rows,stats,f"SHT_{n}",os.path.join(folder,f"SHT-{n}_{suffix}_C_to_D.xlsx"))
        if fm:
            g=groups
            say(f"SHT-{n}  raw({len(added)}/{len(removed)}/{len(both)})   REG(gA={len(g['GLOBALLY ADDED'])} lA={len(g['LOCALLY ADDED'])} gR={len(g['GLOBALLY REMOVED'])} lR={len(g['LOCALLY REMOVED'])} both={nboth} kept={len(rows)})")
say("\nDONE.",reg_out)
log.close()
