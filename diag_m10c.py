import os, sys, re, glob, tempfile, subprocess
sys.path.insert(0, r"C:\Users\Varad\Downloads\dwg-discrepancy-app\app\backend")
import pipeline
ODA=r"C:\Program Files\ODA\ODAFileConverter 27.1.0\ODAFileConverter.exe"
def convert(src):
    out=tempfile.mkdtemp(prefix="oda_")
    subprocess.run([ODA,src,out,"ACAD2018","DXF","0","1","*.DWG"],capture_output=True,text=True,timeout=3000)
    return sorted(set(glob.glob(os.path.join(out,"*.dxf"))+glob.glob(os.path.join(out,"*.DXF"))))
master=pipeline.load_master()
B={}; C={}
for f in convert(r"C:\Users\Varad\Downloads\M10C REV C\M10C"):
    n=pipeline.sheet_no_from_name(os.path.basename(f))
    if n and n not in B: B[n]=set(pipeline._scan(f)[0])
for f in convert(r"C:\Users\Varad\Downloads\M10C rev D\M10C\M10C"):
    n=pipeline.sheet_no_from_name(os.path.basename(f))
    if n and n not in C: C[n]=set(pipeline._scan(f)[0])
print("Per sheet: every tag in D but NOT in C (raw ADDED), and whether the register kept it\n")
for n in sorted(set(B)&set(C)):
    added=sorted(C[n]-B[n])
    print(f"SHT-{n}: {len(added)} raw added")
    for tg in added:
        inreg = pipeline._norm(tg) in master
        print(f"   {'KEPT (in register)   ' if inreg else 'DROPPED (not in 909) '} {tg}")
    print()
