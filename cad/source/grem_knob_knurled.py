"""G.R.E.M. big dial knob: 48 mm, fine straight-ridge knurl, smooth flat top cap with a round finger dimple
(style of the Ulanzi D100H dial).  Run: python3 grem_knob_knurled.py <outdir>
  grem_knob_large_x1.stl      print orientation (top face DOWN, open side up, no supports)
  grem_knob_large_x1_use.stl  as mounted (bore down), used by the blueprint
Needs: cadquery, trimesh, manifold3d, numpy."""
import sys, os, math, numpy as np, trimesh, cadquery as cq
OUT = sys.argv[1] if len(sys.argv) > 1 else "."
R = 24.0                        # top cap radius (dia 48)
RPK, DEPTH = 23.6, 0.8          # ridge crest radius, ridge depth
RV = RPK - DEPTH                # groove radius
COLS = 96                       # ridges around (pitch ~1.57 mm)
H, ZT = 18.0, 14.5              # overall height, top of the ridged band (cap 3.5 mm tall)
R_IN = 21.0                     # skirt inner radius
BORE_D, BORE_FLAT = 6.1, 1.75   # D bore, same as the small knobs' design
DIMPLE_D, DIMPLE_DEPTH, DIMPLE_R = 12.0, 1.4, 14.5   # finger dimple on the top face

# ---------- ridged skirt (watertight mesh) ----------
K = 8
N = COLS * K
th = 2 * np.pi * np.arange(N) / N
def hgt(i):
    f = (i / K) % 1.0
    return min(1.0, 2.2 * (1 - 2 * abs(f - .5)))      # flat crest, steep flanks
V = []
for z in (0.0, ZT):
    for i in range(N):
        r = RV + DEPTH * hgt(i); V.append((r * np.cos(th[i]), r * np.sin(th[i]), z))
for z in (0.0, ZT):
    for i in range(N): V.append((R_IN * np.cos(th[i]), R_IN * np.sin(th[i]), z))
ob, ot, ib, it = 0, N, 2 * N, 3 * N
F = []
for i in range(N):
    j = (i + 1) % N
    F += [(ob + i, ob + j, ot + j), (ob + i, ot + j, ot + i)]             # outer wall
    F += [(ob + i, ib + i, ib + j), (ob + i, ib + j, ob + j)]             # bottom annulus
    F += [(ot + i, ot + j, it + j), (ot + i, it + j, it + i)]             # top annulus
    F += [(ib + i, it + i, it + j), (ib + i, it + j, ib + j)]             # inner wall
skirt = trimesh.Trimesh(np.array(V), np.array(F), process=True)
skirt.fix_normals()
if skirt.volume < 0: skirt.invert()
assert skirt.is_watertight, "skirt not watertight"

# ---------- core: cap, hub, ribs, D-bore, dimple (CadQuery) ----------
def cyl(r, z0, z1): return cq.Workplane("XY").workplane(offset=z0).circle(r).extrude(z1 - z0)
def box(x0, x1, y0, y1, z0, z1): return cq.Workplane("XY").box(x1-x0, y1-y0, z1-z0, centered=False).translate((x0, y0, z0))
cap = cyl(R, ZT, H).faces(">Z").edges().fillet(1.2).faces("<Z").edges().chamfer(0.4)
core = cap.union(cyl(RV + 0.3, ZT - 0.6, ZT + 0.1)).union(cyl(7.2, 0, ZT))
for k in range(6):
    core = core.union(box(5, 21.5, -1.2, 1.2, 0, ZT).rotate((0, 0, 0), (0, 0, 1), k * 60))
core = core.cut(cyl(BORE_D / 2, -1, 11.0).intersect(box(-4, BORE_FLAT, -4, 4, -1, 12)))
rs = ((DIMPLE_D / 2) ** 2 + DIMPLE_DEPTH ** 2) / (2 * DIMPLE_DEPTH)
core = core.cut(cq.Workplane("XY").sphere(rs).translate((0, DIMPLE_R, H - DIMPLE_DEPTH + rs)))
cq.exporters.export(core, os.path.join(OUT, "_core.stl"), tolerance=0.02, angularTolerance=0.1)
core_m = trimesh.load(os.path.join(OUT, "_core.stl")); os.remove(os.path.join(OUT, "_core.stl"))

import manifold3d as m3d
def man(t): return m3d.Manifold(m3d.Mesh(vert_properties=np.asarray(t.vertices, np.float32), tri_verts=np.asarray(t.faces, np.uint32)))
mo = (man(skirt) + man(core_m)).to_mesh()
knob = trimesh.Trimesh(np.asarray(mo.vert_properties)[:, :3], np.asarray(mo.tri_verts), process=True)
assert knob.is_watertight and knob.volume > 0
print("knob bounds", knob.bounds.round(2).tolist(), "volume cm3", round(knob.volume / 1000, 1), "faces", len(knob.faces))
knob.export(os.path.join(OUT, "grem_knob_large_x1_use.stl"))
pr = knob.copy(); pr.apply_transform(trimesh.transformations.rotation_matrix(math.pi, [1, 0, 0])); pr.apply_translation([0, 0, -pr.bounds[0][2]])
pr.export(os.path.join(OUT, "grem_knob_large_x1.stl"))
