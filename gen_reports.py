import re, time, os, sys, ezdxf
sys.path.insert(0, r"C:\Users\Varad\Downloads\dwg-discrepancy-app\app\backend")
import pipeline
TAG=pipeline.TAG
base=r"C:\Users\Varad\Documents\akshay_delivery"
outdir=os.path.join(base,"discrepancy_reports"); os.makedirs(outdir,exist_ok=True)
log=open(os.path.join(outdir,"_progress.log"),"w",encoding="utf-8")
def say(*a):
    m=" ".join(str(x) for x in a); print(m,flush=True); log.write(m+"\n"); log.flush()
def tagset(path):
    doc=ezdxf.readfile(path); out=set()
    for sp in [doc.modelspace()]+[b for b in doc.blocks]:
        for e in sp:
            t=e.dxftype(); s=None
            if t=="TEXT": s=e.dxf.text
            elif t=="MTEXT":
                try: s=e.plain_text()
                except: s=getattr(e,'text','')
            elif t in ("ATTRIB","ATTDEF"): s=e.dxf.text
            if s and TAG.match(s.strip()): out.add(s.strip())
    return out
say("SHEET  BOTH ADDED REMOVED")
for n in ("01","02","03","04","05","06"):
    b=os.path.join(base,"REV B","REV B",f"I-DE-3010.2S-1414-942-S2N-001_SHT-{n}_REV B.dxf")
    c=os.path.join(base,"REV C","REV C",f"I-DE-3010.2S-1414-942-S2N-001_SHT-{n}_REV C.dxf")
    if not (os.path.exists(b) and os.path.exists(c)): say("skip",n); continue
    t0=time.time(); B=tagset(b); C=tagset(c)
    both,added,removed=B&C,C-B,B-C
    rows=[]
    for tg in sorted(B|C):
        r={k:"" for k in pipeline.COLS}; r["EquipmentName"]=tg; r["Sheet"]=f"SHT_{n}"
        if tg in added: r["Status"]="ADDED"; r["Notes"]="New equipment in REV C."; r["Match_Confidence"]="HIGH (tag-set)"
        elif tg in removed: r["Status"]="REMOVED"; r["Notes"]="In REV B, absent from REV C."; r["Match_Confidence"]="HIGH (tag-set)"
        else: r["Status"]="PRESENT IN BOTH"; r["Notes"]="Present in both revisions."
        rows.append(r)
    stats=dict(both=len(both),added=sorted(added),removed=sorted(removed),ref_geom=0,cand_geom=0,ref_datums=0,cand_datums=0,movement_ok=False,warning="")
    out=os.path.join(outdir,f"SHT-{n}_Discrepancy_REVB_to_REVC.xlsx")
    pipeline._write(rows,stats,f"SHT_{n}",out)
    say(f"SHT-{n}  {len(both):4} {len(added):5} {len(removed):6}  ({time.time()-t0:.0f}s)")
say("ALL DONE ->", outdir)
log.close()
