"""G.R.E.M. - full assembly model (every component placed). Run: python3 grem_assembly.py <outdir>
Frame of the finished unit: X = across (standing in FRONT, +X is to your LEFT, because X' = 140 - u), Y = rear->front, Z = up.
"""
import os, sys, math, runpy, itertools, csv
import cadquery as cq

OUT = sys.argv[1] if len(sys.argv) > 1 else "."
HERE = os.path.dirname(os.path.abspath(__file__))
sys.argv = [sys.argv[0], OUT]
G = runpy.run_path(os.path.join(HERE, "grem_cad.py"))
W, D, Z0, T, S, POSTS, zu = G["W"], G["D"], G["Z0"], G["T"], G["S"], G["POSTS"], G["zu"]
body, plate, k_small, k_big = G["body"], G["plate"], G["k_small"], G["k_big"]
ENC = G["ENC"]; MB_HOLES = G["MB_HOLES"]
U = lambda u: W - u
parts = []   # (name, solid, (r,g,b), group, spec)
def add(name, wp, rgb, group, spec=""):
    parts.append((name, wp, rgb, group, spec))

def blk(cu, cv, z0, z1, du, dv):            # box centred on (u,v) in design coords (u measured as in the blueprint)
    return cq.Workplane("XY").box(du, dv, z1 - z0, centered=(True, True, False)).translate((U(cu), cv, z0))
def cyl(cu, cv, z0, z1, d, d_in=0):
    c = cq.Workplane("XY").workplane(offset=z0).center(U(cu), cv).circle(d / 2)
    c = c.circle(d_in / 2) if d_in else c
    return c.extrude(z1 - z0)
def cyl_u(cv, cz, u0, u1, d):                # cylinder along the u axis
    return cq.Workplane("YZ").workplane(offset=U(u1)).center(cv, cz).circle(d / 2).extrude(u1 - u0)
def hexp(cu, cv, z0, z1, af, hole=0):
    h = cq.Workplane("XY").workplane(offset=z0).center(U(cu), cv).polygon(6, af / math.cos(math.radians(30))).extrude(z1 - z0)
    return h.cut(cq.Workplane("XY").workplane(offset=z0 - 1).center(U(cu), cv).circle(hole / 2).extrude(z1 - z0 + 2)) if hole else h

# colours
BLK=(0.09,0.09,0.10); DGR=(0.16,0.17,0.19); PCB=(0.12,0.32,0.62); GRN=(0.15,0.45,0.25); SIL=(0.75,0.77,0.80); GLD=(0.78,0.62,0.25)
RED=(0.7,0.15,0.12); BLU=(0.10,0.33,0.80); CRM=(0.92,0.90,0.84); BRN=(0.55,0.43,0.2)

add("Body (printed)", body, DGR, "Printed", "PETG, 140 x 140 x 62")
# ---------------- floor: power ----------------
add("Foam pad - battery holder", blk(52.0,16.5,3,4,78,25), CRM, "Consumables", "78 x 25 x 1")
add("Foam pad - TP4056", blk(102.5,19.4,3,4,17.2,27), CRM, "Consumables", "17 x 27 x 1")
add("Foam pad - XL6009", blk(123.5,51.5,3,4,21,43), CRM, "Consumables", "21 x 43 x 1")
hx,hy=52.0,16.5
add("18650 holder base", blk(hx,hy,4,6,76.6,23), DGR, "Power", "76.6 x 23")
add("18650 holder end wall -", blk(hx-36.3,hy,6,14,4,23), DGR, "Power")
add("18650 holder end wall +", blk(hx+36.3,hy,6,14,4,23), DGR, "Power")
add("18650 holder rail rear", blk(hx,hy-10.5,6,11,68.6,2), DGR, "Power")
add("18650 holder rail front", blk(hx,hy+10.5,6,11,68.6,2), DGR, "Power")
add("18650 cell", cyl_u(hy,15,hx-32.5,hx+32.5,18), BLU, "Power", "dia 18 x 65")
tx,ty=102.5,19.4
add("TP4056 PCB", blk(tx,ty,4,5.6,17,26.8), PCB, "Power", "26.8 x 17")
add("TP4056 USB-C port", blk(tx,ty-11,5.6,8.8,9,7.5), SIL, "Power")
add("TP4056 chips", blk(tx-3,ty+2,5.6,6.8,5,5).union(blk(tx+3,ty+8,5.6,6.8,5,5)).union(blk(tx+4,ty-3,5.6,6.8,4,4)), BLK, "Power")
xx,xy=123.5,51.5
add("XL6009 PCB", blk(xx,xy,4,5.6,21,43), PCB, "Power", "43 x 21")
add("XL6009 inductor", blk(xx,xy-12,5.6,14.6,10,10), BLK, "Power")
add("XL6009 trimmer", blk(xx+6,xy+10,5.6,10.6,6,6), BLU, "Power")
add("XL6009 capacitor", cyl(xx-5,xy+12,5.6,13.6,7.2), BLK, "Power")
add("XL6009 IC", blk(xx-4,xy,5.6,7.6,5,5), BLK, "Power")
# rocker (right wall, u = 140 -> X' = 0)
RV,RZ=40,23
rk_body = cq.Workplane("XY").box(20,21,15,centered=(False,True,True)).translate((0,RV,RZ))
add("Rocker switch body", rk_body, BLK, "Power", "KCD1, hole 21 x 15")
add("Rocker bezel", cq.Workplane("XY").box(1.5,24.5,18.5,centered=(False,True,True)).translate((-1.5,RV,RZ)), BLK, "Power")
add("Rocker rocker", cq.Workplane("XY").box(3,19,12,centered=(False,True,True)).translate((-4.5,RV,RZ)), RED, "Power")
# ---------------- floor: main board ----------------
for k,(u,v) in enumerate(MB_HOLES):
    add(f"Standoff {k+1} (M3 F-F, 5)", hexp(u,v,3,8,5.5,3.0), SIL, "Hardware", "M3 hex 5 mm")
    add(f"Floor screw {k+1} (M3x6)", cyl(u,v,0.2,2.0,5.6).union(cyl(u,v,2.0,8.0,3.0)), SIL, "Hardware", "M3 x 6")
mb = blk(58,65,8,9.6,100,66)
for (u,v) in MB_HOLES: mb = mb.cut(cyl(u,v,7,11,3.2))
add("Main board (perfboard)", mb, GRN, "Electronics", "100 x 66 x 1.6")
Y0=9.6
for dz in (-12.7,12.7):
    add(f"ESP32 socket {'rear' if dz<0 else 'front'}", blk(35.5+1.5,47+dz,Y0,Y0+8.5,56,2.6), BLK, "Electronics")
ez=Y0+8.5
add("ESP32-S3 PCB", blk(35.5,47,ez,ez+1.6,63.1,28), (0.08,0.09,0.11), "Electronics", "63.1 x 28")
add("ESP32 shield", blk(35.5+10,47,ez+1.6,ez+4.6,18,16), SIL, "Electronics")
add("ESP32 USB-C x2", blk(35.5-30,47-5.25,ez+1.6,ez+4.8,8,9.2).union(blk(35.5-30,47+5.25,ez+1.6,ez+4.8,8,9.2)), SIL, "Electronics")
add("ESP32 buttons", blk(35.5-22,47-11,ez+1.6,ez+3.2,4,4).union(blk(35.5-22,47+11,ez+1.6,ez+3.2,4,4)), BLK, "Electronics")
mz=Y0+6
add("MCP23017 breakout (assumed 35 x 22)", blk(31.5,81,mz,mz+1.6,35,22).union(blk(31.5,81,mz+1.6,mz+4.2,9,16)), (0.17,0.20,0.26), "Electronics", "size assumed")
add("MCP23017 headers", blk(31.5,81+10,mz-6,mz,30,2.2), BLK, "Electronics")
add("DRV2605L breakout", blk(69.5,81,mz,mz+1.6,19,18).union(blk(69.5,81,mz+1.6,mz+2.6,4,4)), (0.1,0.11,0.13), "Electronics", "19 x 18")
add("DRV2605L headers", blk(69.5,81+8,mz-6,mz,15,2.2), BLK, "Electronics")
for i in range(6): add(f"Capacitor 100nF #{i+1}", cyl(22+i*8,64.5,Y0,Y0+5,4), (0.88,0.54,0.19), "Electronics")
for i in range(4): add(f"Resistor #{i+1}", blk(70+i*6,66.5,Y0,Y0+2,6,2), (0.8,0.65,0.4), "Electronics")
add("Bulk capacitor", cyl(100,40,Y0,Y0+16,10), (0.14,0.23,0.42), "Electronics", "dia 10 x 16")
# ---------------- lid frame (plate coordinates: X' = 140-u, Y = s, Z up from the plate underside) ----------------
lid=[]
def ladd(name, wp, rgb, group, spec=""): lid.append((name, wp, rgb, group, spec))
def lblk(cu, cs, z0, z1, du, ds): return cq.Workplane("XY").box(du, ds, z1 - z0, centered=(True, True, False)).translate((U(cu), cs, z0))
def lcyl(cu, cs, z0, z1, d, d_in=0):
    c = cq.Workplane("XY").workplane(offset=z0).center(U(cu), cs).circle(d / 2)
    c = c.circle(d_in / 2) if d_in else c
    return c.extrude(z1 - z0)
ladd("Top plate (printed)", plate, DGR, "Printed", "PETG, 140 x 130 x 3 (+bosses)")
# OLED
ou,os_=70.0,S(21.5)
ladd("OLED glass", lblk(ou,os_,-2.8,0,88,27.8), (0.02,0.03,0.05), "Display")
ladd("OLED PCB", lblk(ou,os_,-3.8,-2.8,100.5,33.5), BLU, "Display", "100.5 x 33.5 x 1")
ladd("OLED header", lblk(ou+45.5,os_,-12.3,-3.8,5.1,20.3), BLK, "Display")
for dx in (-47.5,47.5):
    for dy in (-14.25,14.25):
        ladd(f"OLED insert {'L' if dx<0 else 'R'}{'R' if dy<0 else 'F'}", lcyl(ou+dx,os_+dy,-2.8,1.2,4.2,3.0), GLD, "Hardware", "M3 insert")
# keys
for r in range(3):
    for c in range(3):
        u=G["KEY_U0"]+c*G["KEY_PITCH"]; s=S(G["KEY_V0"])+r*G["KEY_PITCH"]; n=r*3+c+1
        ladd(f"MX switch {n}", lblk(u,s,-5.5,3,14,14).union(lblk(u,s,3,8,15.6,15.6)).union(lblk(u,s,-7.75,-5.5,4,4)), (0.23,0.24,0.27), "Controls", "MX")
        ladd(f"Keycap {n}", lblk(u,s,8.5,16,18,18), (0.92,0.9,0.84) if (r,c)==(0,2) else (0.28,0.3,0.33), "Controls", "18 x 18 x 7.5")
# encoders + knobs
for k,(u,s) in enumerate(ENC):
    big = (k==4); nm = "large" if big else f"small {k+1}"
    ladd(f"KY-040 PCB ({nm})", lblk(u+3.8,s+2.1,-8.1,-6.5,26.2,18.63), GRN, "Controls", "26.2 x 18.6")
    ladd(f"KY-040 header ({nm})", lblk(u+14.7,s+1.1,-16.65,-8.15,2.6,12.7), BLK, "Controls")
    ladd(f"Encoder body ({nm})", lblk(u,s,-6.5,0,12,12), SIL, "Controls")
    ladd(f"Encoder bushing ({nm})", lcyl(u,s,0,5.5,7.0,6.0), SIL, "Controls")
    shaft = lcyl(u,s,0,16.5,6.0).intersect(cq.Workplane("XY").box(10,10,20,centered=(False,True,False)).translate((U(u)-8.5,s,0)))
    ladd(f"Encoder shaft ({nm})", shaft, (0.6,0.62,0.66), "Controls", "dia 6 D-shaft (4.5 across flats), assumed 11.5 above the bushing")
    nut = cq.Workplane("XY").workplane(offset=3).center(U(u),s).polygon(6,10/math.cos(math.radians(30))).extrude(2).cut(cq.Workplane("XY").workplane(offset=2).center(U(u),s).circle(3.5).extrude(4))
    ladd(f"M7 nut ({nm})", nut, SIL, "Hardware")
    kn = (k_big if big else k_small).translate((U(u),s,6.0))
    ladd(f"Knob ({nm})", kn, DGR, "Printed", "PETG")
# motor
mu,ms=G["MOTOR_U"],S(G["MOTOR_V"])
ladd("Motor foam", lcyl(mu,ms,-0.8,0,11.6), CRM, "Consumables")
ladd("Coin motor", lcyl(mu,ms,-3.8,-0.8,10), SIL, "Haptics", "dia 10 x 3")
# lid screws (M3x8) + post inserts
for k,(u,v) in enumerate(POSTS):
    s=S(v)
    ladd(f"Lid screw {k+1} (M3x8)", lcyl(u,s,1.2,3.0,5.6).union(lcyl(u,s,-6.8,1.2,3.0)), SIL, "Hardware", "M3 x 8")
def tilt_body(wp,u,v):
    return wp.rotate((0,0,0),(1,0,0),-math.degrees(T)).translate((U(u),v,zu(v)))
for k,(u,v) in enumerate(POSTS):
    ins = cq.Workplane("XY").workplane(offset=-5.7).circle(2.1).circle(1.5).extrude(5.7)
    add(f"Post insert {k+1} (M3)", tilt_body(ins,u,v), GLD, "Hardware", "M3 heat-set")
LID_T = lambda wp: wp.rotate((0,0,0),(1,0,0),-math.degrees(T)).translate((0,0,Z0))
for (n,wp,c,g,sp) in lid:
    # plate / knob etc were built with X' already mirrored (plate) or via U(); plate itself is already mirrored in grem_cad
    add(n, LID_T(wp), c, g, sp)

# ---------------- export + checks ----------------
assy = cq.Assembly(name="GREM")
for (n,wp,c,g,sp) in parts:
    assy.add(wp, name=n, color=cq.Color(*c))
assy.save(os.path.join(OUT,"grem_full_assembly.step"))
comp = cq.Compound.makeCompound([p[1].val() for p in parts])
cq.exporters.export(cq.Workplane().add(comp), os.path.join(OUT,"grem_full_assembly.stl"), tolerance=0.05, angularTolerance=0.2)

# interference
bbs=[p[1].val().BoundingBox() for p in parts]
hits=[]
for i,j in itertools.combinations(range(len(parts)),2):
    a,b=bbs[i],bbs[j]
    if a.xmax<=b.xmin or b.xmax<=a.xmin or a.ymax<=b.ymin or b.ymax<=a.ymin or a.zmax<=b.zmin or b.zmax<=a.zmin: continue
    try: v=parts[i][1].val().intersect(parts[j][1].val()).Volume()
    except Exception as e: v=-1
    if v>0.5 or v<0: hits.append((v,parts[i][0],parts[j][0]))
hits.sort(reverse=True)
with open(os.path.join(OUT,"grem_interference_report.txt"),"w") as f:
    f.write("Pairs of parts that overlap by more than 0.5 mm3 (volume in mm3):\n")
    for v,a,b in hits: f.write(f"{v:10.1f}  {a}  <->  {b}\n")
    if not hits: f.write("none\n")
print(len(parts),"parts;",len(hits),"overlapping pairs")
for h in hits[:40]: print("%8.1f  %s  <->  %s"%h)
# BOM
from collections import Counter
cnt=Counter(); info={}
for (n,wp,c,g,sp) in parts:
    key=n.split(" #")[0]
    cnt[key]+=1; info[key]=(g,sp)

# ---------------- renders (VTK offscreen) ----------------
import vtk
from vtk.util.numpy_support import numpy_to_vtk
import numpy as np
LIDNAMES = {n for (n,_,_,_,_) in lid} | {n for n in [p[0] for p in parts] if n.startswith("Lid screw")}
def mesh_of(wp, dz=0.0):
    v,t = wp.val().tessellate(0.1, 0.3)
    pts = np.array([(p.x,p.y,p.z+dz) for p in v],float)
    return pts, np.array(t,int)
def actor(pts, tri, rgb, opacity=1.0):
    P = vtk.vtkPoints(); P.SetData(numpy_to_vtk(pts,deep=True))
    cells = vtk.vtkCellArray()
    for a,b,c in tri:
        cells.InsertNextCell(3); cells.InsertCellPoint(a); cells.InsertCellPoint(b); cells.InsertCellPoint(c)
    pd = vtk.vtkPolyData(); pd.SetPoints(P); pd.SetPolys(cells)
    nm = vtk.vtkPolyDataNormals(); nm.SetInputData(pd); nm.SetFeatureAngle(40); nm.SplittingOn(); nm.Update()
    m = vtk.vtkPolyDataMapper(); m.SetInputConnection(nm.GetOutputPort())
    a = vtk.vtkActor(); a.SetMapper(m); pr = a.GetProperty(); pr.SetColor(*rgb); pr.SetOpacity(opacity); pr.SetSpecular(0.25); pr.SetSpecularPower(25)
    return a
def render(fname, lift=0.0, cam=(1.0,-1.25,0.85), hide_lid=False, size=(1500,1000), zoom=1.0, clip=None):
    rw = vtk.vtkRenderWindow(); rw.SetOffScreenRendering(1); rw.SetSize(*size); rw.SetMultiSamples(8)
    r = vtk.vtkRenderer(); r.SetBackground(0.96,0.96,0.97); rw.AddRenderer(r)
    for (n,wp,c,g,sp) in parts:
        is_lid = n in LIDNAMES
        if hide_lid and is_lid: continue
        pts,tri = mesh_of(wp, lift if is_lid else 0.0)
        r.AddActor(actor(pts,tri,c))
    r.GetActiveCamera().SetViewUp(0,0,1)
    cx,cy,cz = 70,63,25+lift*0.4
    d = 330/zoom
    r.GetActiveCamera().SetFocalPoint(cx,cy,cz); r.GetActiveCamera().SetPosition(cx+cam[0]*d, cy+cam[1]*d, cz+cam[2]*d)
    r.ResetCameraClippingRange()
    light = vtk.vtkLight(); light.SetLightTypeToHeadlight(); r.AddLight(light)
    rw.Render()
    w = vtk.vtkWindowToImageFilter(); w.SetInput(rw); w.Update()
    pw = vtk.vtkPNGWriter(); pw.SetFileName(os.path.join(OUT,fname)); pw.SetInputConnection(w.GetOutputPort()); pw.Write()
# standing in front: camera at +Y; X' increases to the viewer's left, so look from +Y with slight rotation
render("grem_render_assembled.png", cam=(-0.8,1.15,0.75))
render("grem_render_lid_lifted.png", lift=75, cam=(-0.8,1.15,0.9))
render("grem_render_inside_top.png", hide_lid=True, cam=(0.0,0.35,1.6), zoom=1.1)
render("grem_render_rear.png", cam=(0.7,-1.2,0.6))
print("renders done")

# ---------------- bill of materials ----------------
from collections import OrderedDict
bom = OrderedDict()
for (n,wp,c,g,sp) in parts:
    key = n.split(" #")[0]
    for tag in (" 1"," 2"," 3"," 4"," 5"," 6"," 7"," 8"," 9"):
        pass
    import re
    key = re.sub(r"\s*(\(small \d\)|\d+|[LR][RF])(?=\s*(\(|$))","",key).strip() if key.startswith(("Standoff","Floor screw","Lid screw","Post insert","OLED insert","MX switch","Keycap","Capacitor","Resistor")) else key
    if key not in bom: bom[key]=[g,0,sp]
    bom[key][1]+=1
with open(os.path.join(OUT,"grem_assembly_BOM.csv"),"w",newline="",encoding="utf-8-sig") as f:
    w=csv.writer(f); w.writerow(["Group","Part","Qty in model","Spec / size"])
    for k,(g,q,sp) in bom.items(): w.writerow([g,k,q,sp])
print("BOM lines:",len(bom))
