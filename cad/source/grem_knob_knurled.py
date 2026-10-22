"""G.R.E.M. big dial knob, diamond-knurled (pyramid texture, inspired by the Ender 3 'Knurled Control Knob' look).
Run: python3 grem_knob_knurled.py <outdir>   ->  grem_knob_large_x1.stl (print orientation: top face DOWN, open side up)
                                                  grem_knob_large_x1_use.stl (as mounted: bore down, used by the blueprint)
Needs: cadquery, trimesh, manifold3d, numpy."""
import sys, os, math, numpy as np, trimesh, cadquery as cq
OUT = sys.argv[1] if len(sys.argv) > 1 else "."
R, DEPTH = 24.0, 0.65          # peak radius (dia 48), pyramid height
COLS, ROWS = 48, 4             # diamond lattice: 48 diamonds around, 4 up the band (square diamonds, pitch ~3.14 mm)
Q = 2 * math.pi * R / COLS     # groove spacing measured around the rim
ZB = 1.5                       # smooth base ring height
HK = ROWS * Q                  # knurl band height (12.57)
ZT = ZB + HK                   # top of the band (about 14.07)
H, TOP_T = 18.0, 4.0           # overall height, top-cap thickness
RV = R - DEPTH                 # valley radius
R_IN = 21.4                    # skirt inner radius
BORE_D, BORE_FLAT = 6.1, 1.75  # same D bore as the small knobs' design

# ---------- knurled skirt (height-field mesh, watertight) ----------
K = 8                                           # samples per diamond
N, M = COLS * K, ROWS * K
th = 2 * np.pi * np.arange(N) / N
zs = ZB + HK * np.arange(M + 1) / M
def hgt(i, j):
    # grooves run along the +45 and -45 degree diagonals (s = arc length, z = height): s+z = k*Q and s-z = k*Q
    sA = (i / K) % COLS; z = j * (HK / M) / Q          # both in units of Q
    A = (sA + z) % 1.0; B = (sA - z) % 1.0
    return min(1 - 2 * abs(A - .5), 1 - 2 * abs(B - .5))
V = []
for j in range(M + 1):
    for i in range(N):
        r = RV + DEPTH * (0 if j in (0, M) else hgt(i, j))
        V.append((r * np.cos(th[i]), r * np.sin(th[i]), zs[j]))
nb = len(V)
for z in (ZB, ZT):                              # inner rings
    for i in range(N): V.append((R_IN * np.cos(th[i]), R_IN * np.sin(th[i]), z))
ib, it = nb, nb + N
F = []
for j in range(M):
    for i in range(N):
        a = j * N + i; b = j * N + (i + 1) % N; c = (j + 1) * N + (i + 1) % N; d = (j + 1) * N + i
        F += [(a, b, c), (a, c, d)]
for i in range(N):                               # bottom annulus (normal -z), top annulus (+z), inner wall (faces axis)
    i2 = (i + 1) % N
    F += [(i, ib + i, ib + i2), (i, ib + i2, i2)]
    t0, t1 = M * N + i, M * N + i2
    F += [(t0, t1, it + i2), (t0, it + i2, it + i)]
    F += [(ib + i, it + i, it + i2), (ib + i, it + i2, ib + i2)]
skirt = trimesh.Trimesh(np.array(V), np.array(F), process=True)
skirt.fix_normals()
if skirt.volume < 0: skirt.invert()
assert skirt.is_watertight, "skirt not watertight"

# ---------- core: top cap, hub, ribs, D-bore, pointer groove (CadQuery) ----------
def cyl(r, z0, z1): return cq.Workplane("XY").workplane(offset=z0).circle(r).extrude(z1 - z0)
def box(x0, x1, y0, y1, z0, z1): return cq.Workplane("XY").box(x1-x0, y1-y0, z1-z0, centered=False).translate((x0, y0, z0))
cap = cyl(RV, ZT - 0.5, H).faces(">Z").edges().chamfer(0.8)
base = cyl(R, 0, ZB + 0.2).cut(cyl(R_IN, -1, ZB + 1)).faces("<Z").edges().chamfer(0.4)
core = cap.union(base).union(cyl(7.2, 0, ZT))
for k in range(6):
    core = core.union(box(5, 22.0, -1.2, 1.2, 0, ZT).rotate((0,0,0), (0,0,1), k * 60))
bore = cyl(BORE_D / 2, -1, 11.0).intersect(box(-4, BORE_FLAT, -4, 4, -1, 12))
core = core.cut(bore)
cq.exporters.export(core, os.path.join(OUT, "_core.stl"), tolerance=0.02, angularTolerance=0.1)
core_m = trimesh.load(os.path.join(OUT, "_core.stl")); os.remove(os.path.join(OUT, "_core.stl"))

# ---------- union ----------
import manifold3d as m3d
def man(t): return m3d.Manifold(m3d.Mesh(vert_properties=np.asarray(t.vertices, np.float32), tri_verts=np.asarray(t.faces, np.uint32)))
u = man(skirt) + man(core_m)
mo = u.to_mesh()
knob = trimesh.Trimesh(np.asarray(mo.vert_properties)[:, :3], np.asarray(mo.tri_verts), process=True)
assert knob.is_watertight and knob.volume > 0
print("knob use-orientation bounds", knob.bounds.round(2).tolist(), "volume cm3", round(knob.volume / 1000, 1), "faces", len(knob.faces))
knob.export(os.path.join(OUT, "grem_knob_large_x1_use.stl"))
pr = knob.copy(); pr.apply_transform(trimesh.transformations.rotation_matrix(math.pi, [1, 0, 0])); pr.apply_translation([0, 0, -pr.bounds[0][2]])
pr.export(os.path.join(OUT, "grem_knob_large_x1.stl"))
