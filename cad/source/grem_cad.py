"""G.R.E.M. (Grading, Rendering & Editing Machine) - parametric CAD (CadQuery). Units: mm.
Body frame: X = left-right (u), Y = rear->front (v), Z = up.
Plate frame (printed flat): X = u, Y = s (distance along slope from rear edge), Z = thickness (0 = underside, 3 = top face).
"""
import math, os, sys
import cadquery as cq

OUT = sys.argv[1] if len(sys.argv) > 1 else "."
# ---------------- parameters ----------------
W, D, H = 140.0, 126.0, 65.0          # outer plan size, rear height (incl. plate)
WALL, FLOOR, PT = 3.0, 3.0, 3.0       # wall, floor, plate thickness
T = math.atan(33.0 / 126.0); cT, sT = math.cos(T), math.sin(T)
Z0 = H - PT / cT                      # plate-underside height at v=0
zu = lambda v: Z0 - 33.0 / 126.0 * v  # plate-underside height at plan depth v
S = lambda v: v / cT                  # plan depth -> distance along plate
INS_D = 4.2                           # M3 heat-set insert hole
KEY_HOLE, KEY_RELIEF = 14.1, 15.6     # MX plate cutout / underside clip relief
ENC_HOLE = 7.2                        # KY-040 bushing hole
POSTS = [(8, 8), (132, 8), (8, 118), (132, 118)]

def box(x0, x1, y0, y1, z0, z1):
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))
def cylz(x, y, z0, z1, d):
    return cq.Workplane("XY").workplane(offset=z0).center(x, y).circle(d / 2).extrude(z1 - z0)

# ---------------- body ----------------
prof = [(0, 0), (D, 0), (D, zu(D)), (0, Z0)]
outer = cq.Workplane("YZ").polyline(prof).close().extrude(W)
outer = outer.edges("|Z").fillet(3.0)
cav = box(WALL, W - WALL, WALL, D - WALL, FLOOR, 90).edges("|Z").fillet(1.0)
body = outer.cut(cav)

# corner posts (merge into walls), kept below the plate-underside plane
for (u, v) in POSTS:
    body = body.union(cylz(u, v, FLOOR, 90, 9.0).intersect(outer))

# insert holes, axis tilted to the plate normal
def tilt(wp):  # rotate a +Z feature so +Z -> plate normal
    return wp.rotate((0, 0, 0), (1, 0, 0), -math.degrees(T))
for (u, v) in POSTS:
    h = cq.Workplane("XY").workplane(offset=-7.0).circle(INS_D / 2).extrude(7.5)
    body = body.cut(tilt(h).translate((u, v, zu(v))))

def frame(cx, cy, iw, idp, rim, h, notches=()):
    o = box(cx - iw/2 - rim, cx + iw/2 + rim, cy - idp/2 - rim, cy + idp/2 + rim, FLOOR - 0.01, FLOOR + h)
    i = box(cx - iw/2, cx + iw/2, cy - idp/2, cy + idp/2, FLOOR - 0.01, FLOOR + h + 1)
    f = o.cut(i)
    for (nx, ny, nw, nd) in notches:
        f = f.cut(box(nx - nw/2, nx + nw/2, ny - nd/2, ny + nd/2, FLOOR, FLOOR + h + 1))
    return f

# 18650 holder (76.6 long) -> pocket 79.4 x 26.4, lead notches at both ends
hx, hy = 52.0, 16.5
body = body.union(frame(hx, hy, 79.4, 26.4, 1.5, 4.0,
        [(hx - 39.7 - 0.75, hy, 3.0, 10), (hx + 39.7 + 0.75, hy, 3.0, 10)]))
# TP4056 (17 x 26.8): open at USB end (rear) and pad end (front)
tx, ty = 102.5, 19.4
body = body.union(frame(tx, ty, 17.4, 27.2, 1.2, 3.0,
        [(tx, ty - 13.6 - 0.6, 12, 3), (tx, ty + 13.6 + 0.6, 12, 3)]))
# XL6009 (43 x 21): open at both ends
xx, xy = 123.5, 51.5
body = body.union(frame(xx, xy, 21.4, 43.4, 1.2, 3.0,
        [(xx, xy - 21.7 - 0.6, 14, 3), (xx, xy + 21.7 + 0.6, 14, 3)]))
# MCP23017 breakout area marker frame (40 x 25 reserved, low corner guides only - refine after it arrives)
# main-board standoff holes (M3 screw from below, counterbored)
MB_HOLES = [(11, 36.5), (105, 36.5), (11, 93.5), (105, 93.5)]
for (u, v) in MB_HOLES:
    body = body.cut(cylz(u, v, -1, FLOOR + 1, 3.2))
    body = body.cut(cylz(u, v, -1, 2.0, 6.2))
# wall cutouts
body = body.cut(box(tx - 6, tx + 6, -1, WALL + 1, 8 - 3, 8 + 3))              # TP4056 USB-C, rear
body = body.cut(box(-1, WALL + 1, 47 - 12, 47 + 12, 22 - 4, 22 + 4))          # ESP32 USB-C x2, left
body = body.cut(box(W - WALL - 1, W + 1, 40 - 10.5, 40 + 10.5, 23 - 7.5, 23 + 7.5))  # rocker 21x15, right
body = body.cut(box(W - WALL - 1, W - WALL + 1.5, 40 - 12, 40 + 12, 23 - 9, 23 + 9)) # inside recess -> 1.5 mm panel

# ---------------- top plate (printed top-face DOWN) ----------------
PL = D / cT
plate = box(0, W, 0, PL, 0, PT).edges("|Z").fillet(3.0)
plate = plate.faces(">Z").edges().chamfer(0.6)           # top edge chamfer
for (u, v) in POSTS:
    s = S(v)
    plate = plate.cut(cylz(u, s, -1, PT + 1, 3.4))
    plate = plate.cut(cylz(u, s, PT - 1.8, PT + 1, 6.2))     # screw-head counterbore
# OLED window + M3 insert bosses on underside
ou, os_ = 70.0, S(21.5)
plate = plate.cut(box(ou - 0.8 - 40.5, ou - 0.8 + 40.5, os_ - 11.5, os_ + 11.5, -1, PT + 1))
for dx in (-47.5, 47.5):
    for dy in (-14.25, 14.25):
        plate = plate.union(cylz(ou + dx, os_ + dy, -2.8, 0.01, 7.0))
        plate = plate.cut(cylz(ou + dx, os_ + dy, -2.9, 1.2, INS_D))
# MX keys 3x3, true 19.05 pitch along the plate
for r in range(3):
    for c in range(3):
        u = 22 + c * 19.05; s = S(72) + r * 19.05
        plate = plate.cut(box(u - KEY_HOLE/2, u + KEY_HOLE/2, s - KEY_HOLE/2, s + KEY_HOLE/2, -1, PT + 1))
        plate = plate.cut(box(u - KEY_RELIEF/2, u + KEY_RELIEF/2, s - KEY_RELIEF/2, s + KEY_RELIEF/2, -1, 1.5))
# encoders: 4 small dials + 1 large
ENC = [(21 + i * 29, S(46)) for i in range(4)] + [(108, S(92))]
for (u, s) in ENC:
    plate = plate.cut(cylz(u, s, -1, PT + 1, ENC_HOLE))
# coin-motor retaining ring on the underside
mu, ms = 108, S(110)
ring = cylz(mu, ms, -3.5, 0.01, 14.0).cut(cylz(mu, ms, -4, 1, 12.0))
plate = plate.union(ring)

# ---------------- knobs ----------------
BORE_D, BORE_FLAT = 6.1, 1.75         # D-shaft bore: dia 6.1, flat 1.75 from the axis (4.8 across the flats)
def knob(dia, height, grooves, name):
    k = cq.Workplane("XY").circle(dia / 2).extrude(height)
    k = k.faces(">Z").edges().chamfer(1.0)
    gd, gw = 0.8, 1.2
    for i in range(grooves):
        a = 360.0 * i / grooves
        g = box(dia / 2 - gd, dia / 2 + 1, -gw / 2, gw / 2, 3.5, height + 1).rotate((0, 0, 0), (0, 0, 1), a)
        k = k.cut(g)
    # nut recess + D-shaft bore (circle 6.2, flat at x=+2.4), open at the bottom
    k = k.cut(cylz(0, 0, -1, 3.5, 13.5))
    bore = cylz(0, 0, -1, 11.0, BORE_D).intersect(box(-4, BORE_FLAT, -4, 4, -1, 12))
    k = k.cut(bore)
    # indicator line on top
    k = k.cut(box(-0.6, 0.6, dia * 0.18, dia / 2 - 1.2, height - 0.6, height + 1))
    return k

def export(obj, name):
    cq.exporters.export(obj, os.path.join(OUT, name + ".step"))
    cq.exporters.export(obj, os.path.join(OUT, name + ".stl"), tolerance=0.02, angularTolerance=0.1)

k_small = knob(24, 14, 24, "small")
k_big = knob(38, 18, 36, "big")

# ---------------- test tile ----------------
tile = box(0, 100, 0, 66, 0, PT).edges("|Z").fillet(2.0)
for i, d in enumerate((14.0, 14.1, 14.2)):
    u = 18 + i * 20
    tile = tile.cut(box(u - d/2, u + d/2, 14 - d/2, 14 + d/2, -1, PT + 1))
    tile = tile.cut(box(u - KEY_RELIEF/2, u + KEY_RELIEF/2, 14 - KEY_RELIEF/2, 14 + KEY_RELIEF/2, -1, 1.5))
for i, d in enumerate((7.0, 7.2, 7.4)):
    tile = tile.cut(cylz(18 + i * 20, 38, -1, PT + 1, d))
tile = tile.cut(box(78 - 10.5, 78 + 10.5, 14 - 7.5, 14 + 7.5, -1, PT + 1))          # rocker 21x15
tile = tile.cut(box(78 - 12, 78 + 12, 14 - 9, 14 + 9, 1.5, PT + 1))                   # 1.5 mm panel behind
tile = tile.cut(cylz(78, 38, -1, PT + 1, 3.4)).cut(cylz(78, 38, PT - 1.8, PT + 1, 6.2))  # screw hole + head recess
tile = tile.cut(cylz(90, 38, -1, PT + 1, 4.2))                                       # insert-size check hole
# lettering sample (raised 0.6 mm) - same text/size as the front wall
BRAND = "G.R.E.M."
def lettering(plane, size=12.0, raise_mm=0.6):
    return cq.Workplane(plane).text(BRAND, size, raise_mm, font="DejaVu Sans", kind="bold", halign="center", valign="center")
tile = tile.union(lettering(cq.Plane(origin=(50, 57, PT - 0.01), xDir=(1, 0, 0), normal=(0, 0, 1)), 9.0))
# stubs: six bore variants, N slots on the rim = variant number
#   1: round 5.9   2: round 6.0   3: D 4.6 AF   4: D 4.8 AF   5: D 5.0 AF   6: D 5.2 AF   (D bores are dia 6.1)
STUB_VARIANTS = [("round", 5.9), ("round", 6.0), ("D", 4.6), ("D", 4.8), ("D", 5.0), ("D", 5.2)]
stubs = None
for i, (kind, val) in enumerate(STUB_VARIANTS):
    st = cq.Workplane("XY").circle(9).extrude(11.0)
    if kind == "round":
        st = st.cut(cylz(0, 0, -1, 12, val))
    else:
        st = st.cut(cylz(0, 0, -1, 12, 6.1).intersect(box(-4, val - 3.05, -4, 4, -1, 12)))
    for k in range(i + 1):
        a = 30.0 * k - 15.0 * i
        st = st.cut(box(8.0, 10, -0.5, 0.5, 2.0, 12).rotate((0, 0, 0), (0, 0, 1), a))
    st = st.translate((10 + (i % 3) * 22, 10 + (i // 3) * 22, 0))
    stubs = st if stubs is None else stubs.union(st)

# ---------------- orientation + front lettering ----------------
# The model above is built in a right-handed frame; the blueprint (and the real object seen from the FRONT) has +u to the
# viewer's right. Mirror body and plate about x = 70 so the printed parts match the blueprint exactly.
body = body.mirror("YZ", (W / 2, 0, 0))
plate = plate.mirror("YZ", (W / 2, 0, 0))
# raised G.R.E.M. on the front wall, reading left-to-right for someone standing in front
front_txt = lettering(cq.Plane(origin=(W / 2, D - 0.01, 15.0), xDir=(-1, 0, 0), normal=(0, 1, 0)), 12.0)
body = body.union(front_txt)

# ---------------- exports ----------------
export(body, "grem_body")
export(plate, "grem_top_plate")
export(k_small, "grem_knob_small_x4")
export(k_big, "grem_knob_large_x1")
export(tile, "grem_test_tile")
export(stubs, "grem_test_knob_stubs")

# assembly check: plate on the body slope
asm_plate = plate.rotate((0, 0, 0), (1, 0, 0), -math.degrees(T)).translate((0, 0, Z0))
export(asm_plate, "_assembled_plate")
inter = body.intersect(asm_plate)
print("interference volume plate/body: %.2f mm3" % inter.val().Volume())
for n, o in [("body", body), ("plate", plate), ("knob_small", k_small), ("knob_large", k_big), ("tile", tile), ("stubs", stubs)]:
    bb = o.val().BoundingBox()
    print("%-11s valid=%s vol=%8.0f  bbox %.1f x %.1f x %.1f" % (n, o.val().isValid(), o.val().Volume(), bb.xlen, bb.ylen, bb.zlen))
