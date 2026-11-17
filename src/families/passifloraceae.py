import os
import math
import importlib
import numpy as np
from geometry import NL


def _ss(a, b, x):
    """Interpolación smoothstep C1 en [a, b] para transiciones cromáticas y morfológicas limpias."""
    t = max(0.0, min(1.0, (float(x) - float(a)) / max(float(b) - float(a), 1e-6)))
    return t * t * (3.0 - 2.0 * t)


def _lowfreq(x, y, seed=0.0):
    """Ruido trigonométrico suave y determinista en [-1, 1] para venación y moteado orgánico."""
    n = (
        math.sin(0.23 * x + 1.4 + seed) * math.cos(0.27 * y - 0.7 + 1.8 * seed)
        + 0.6 * math.sin(0.15 * x - 0.33 * y + 2.9 + seed)
        + 0.4 * math.cos(0.41 * x + 0.31 * y - 1.1 * seed)
    )
    return max(-1.0, min(1.0, n / 1.6))


def _load_passiflora_photometric_tint(photo_path, grid_size=96):
    """Extrae micro-contraste fotométrico de la imagen de referencia si existe en disco."""
    if not photo_path or not os.path.exists(photo_path):
        return None
    try:
        pil_image = importlib.import_module("PIL.Image")
        img = np.asarray(pil_image.open(photo_path).convert("RGB"), dtype=np.float32) / 255.0
        lum = 0.299 * img[..., 0] + 0.587 * img[..., 1] + 0.114 * img[..., 2]
        gy = np.linspace(0, lum.shape[0] - 1, grid_size).astype(int)
        gx = np.linspace(0, lum.shape[1] - 1, grid_size).astype(int)
        sampled = lum[np.ix_(gy, gx)]
        mean_v = float(np.mean(sampled))
        std_v = float(np.std(sampled)) or 1.0
        return np.clip((sampled - mean_v) / (2.5 * std_v), -1.0, 1.0)
    except Exception:
        return None


class ObjMeshBuilder:
    """Constructor topológico con seguimiento automático de índices y color por vértice."""

    def __init__(self):
        self.lines = []
        self.v_count = 0

    def group(self, name):
        self.lines.append(f"g {name}")

    def material(self, name):
        self.lines.append(f"usemtl {name}")

    def v(self, x, y, z, r, g, b):
        self.v_count += 1
        r_c = max(0.0, min(1.0, r))
        g_c = max(0.0, min(1.0, g))
        b_c = max(0.0, min(1.0, b))
        self.lines.append(f"v {x:.4f} {y:.4f} {z:.4f} {r_c:.4f} {g_c:.4f} {b_c:.4f}")
        return self.v_count

    def f(self, i1, i2, i3):
        self.lines.append(f"f {i1} {i2} {i3}")

    def quad(self, p1, p2, p3, p4):
        self.lines.append(f"f {p1} {p2} {p3}")
        self.lines.append(f"f {p2} {p4} {p3}")

    def add_tube(self, pts, radii, colors, radial_segs=10, cap_start=False, cap_end=False):
        """Genera un tubo curvo continuo usando marcos ortonormales estables."""
        n = len(pts)
        if n < 2:
            return
        rings = []
        for i in range(n):
            if i == 0:
                tx, ty, tz = pts[1][0] - pts[0][0], pts[1][1] - pts[0][1], pts[1][2] - pts[0][2]
            elif i == n - 1:
                tx, ty, tz = pts[-1][0] - pts[-2][0], pts[-1][1] - pts[-2][1], pts[-1][2] - pts[-2][2]
            else:
                tx, ty, tz = pts[i + 1][0] - pts[i - 1][0], pts[i + 1][1] - pts[i - 1][1], pts[i + 1][2] - pts[i - 1][2]

            t_len = math.sqrt(tx * tx + ty * ty + tz * tz) or 1e-6
            tx, ty, tz = tx / t_len, ty / t_len, tz / t_len

            if abs(ty) < 0.9:
                ux, uy, uz = 0.0, 1.0, 0.0
            else:
                ux, uy, uz = 1.0, 0.0, 0.0

            nx = ty * uz - tz * uy
            ny = tz * ux - tx * uz
            nz = tx * uy - ty * ux
            n_len = math.sqrt(nx * nx + ny * ny + nz * nz) or 1e-6
            nx, ny, nz = nx / n_len, ny / n_len, nz / n_len

            bx = ty * nz - tz * ny
            by = tz * nx - tx * nz
            bz = tx * ny - ty * nx

            cx, cy, cz = pts[i]
            rad = radii[i]
            cr, cg, cb = colors[i]
            ring = []
            for s in range(radial_segs):
                ang = s * (2.0 * math.pi / radial_segs)
                ca, sa = math.cos(ang), math.sin(ang)
                vx = cx + rad * (ca * nx + sa * bx)
                vy = cy + rad * (ca * ny + sa * by)
                vz = cz + rad * (ca * nz + sa * bz)
                ring.append(self.v(vx, vy, vz, cr, cg, cb))
            rings.append(ring)

        for i in range(n - 1):
            r1, r2 = rings[i], rings[i + 1]
            for s in range(radial_segs):
                sn = (s + 1) % radial_segs
                self.quad(r1[s], r1[sn], r2[s], r2[sn])

        if cap_start:
            c0 = self.v(pts[0][0], pts[0][1], pts[0][2], *colors[0])
            for s in range(radial_segs):
                sn = (s + 1) % radial_segs
                self.f(c0, rings[0][sn], rings[0][s])

        if cap_end:
            c1 = self.v(pts[-1][0], pts[-1][1], pts[-1][2], *colors[-1])
            for s in range(radial_segs):
                sn = (s + 1) % radial_segs
                self.f(c1, rings[-1][s], rings[-1][sn])

    def build_obj(self):
        return NL.join(self.lines) + NL


def _lerp_color(c1, c2, t):
    t_c = max(0.0, min(1.0, t))
    return (
        c1[0] + (c2[0] - c1[0]) * t_c,
        c1[1] + (c2[1] - c1[1]) * t_c,
        c1[2] + (c2[2] - c1[2]) * t_c,
    )


def _corona_radii_color(s, is_vitifolia=False, phase=0.0):
    """
    Bandeado concéntrico multizona para los filamentos de la corona (Radii).
    En Passiflora ligularis reproduce el patrón cebra (blanco / púrpura granate /
    blanco / púrpura-violeta / azul-lavanda / ápice blanco puro ondulado).
    """
    if is_vitifolia:
        if s < 0.25:
            return (0.65, 0.04, 0.08)
        elif s < 0.50:
            return (0.96, 0.94, 0.94)
        else:
            return (0.92, 0.12, 0.15)

    s_mod = max(0.0, min(1.0, s + 0.012 * phase))

    c_white = (0.98, 0.98, 1.00)     # Blanco brillante de las bandas claras y el ápice
    c_maroon = (0.34, 0.04, 0.24)    # Púrpura granate oscuro de las bandas basales
    c_purple = (0.44, 0.09, 0.42)    # Púrpura rojizo medio
    c_violet = (0.48, 0.24, 0.76)    # Azul-violeta subapical característico de P. ligularis

    if s_mod < 0.07:
        return _lerp_color((0.92, 0.95, 0.88), c_maroon, _ss(0.03, 0.07, s_mod))
    elif s_mod < 0.17:
        return _lerp_color(c_maroon, c_white, _ss(0.14, 0.17, s_mod))
    elif s_mod < 0.26:
        return _lerp_color(c_white, c_maroon, _ss(0.23, 0.26, s_mod))
    elif s_mod < 0.37:
        return _lerp_color(c_maroon, c_white, _ss(0.34, 0.37, s_mod))
    elif s_mod < 0.46:
        return _lerp_color(c_white, c_purple, _ss(0.43, 0.46, s_mod))
    elif s_mod < 0.58:
        return _lerp_color(c_purple, c_white, _ss(0.55, 0.58, s_mod))
    elif s_mod < 0.67:
        return _lerp_color(c_white, c_violet, _ss(0.64, 0.67, s_mod))
    elif s_mod < 0.85:
        return c_violet
    else:
        return _lerp_color(c_violet, c_white, _ss(0.85, 0.90, s_mod))


def build_passiflora_flower(cfg):
    """
    Generador morfométrico e histológico para Passifloraceae (Passiflora ligularis / P. vitifolia):
    Incluye brácteas involucrales foliáceas reticuladas, cáliz y corola fuertemente retroflexos
    en P. ligularis (pétalos 30 x 10 mm con punteado púrpura adaxial), corona multiseriada
    acopada con bandeado cebra y ápices blancos rizados, columna con 5 anteras versátiles (5-8 mm),
    ovario súpero tricarpelar verde manzana, 3 estilos curvos maculados y anatomía interna completa.
    """
    mb = ObjMeshBuilder()

    colecta = cfg.get("colecta", {}) or cfg.get("taxonomia", {})
    especie = str(colecta.get("especie", "")).lower()
    is_vitifolia = "vitifolia" in especie
    photo_map = _load_passiflora_photometric_tint(colecta.get("foto_campo", ""))

    corola = cfg.get("perianto", {}).get("corola", {})
    androceo = cfg.get("androceo", {})
    l_petal = float(corola.get("longitud_limbo_mm", 30.0 if not is_vitifolia else 65.0))
    w_petal = float(corola.get("ancho_petalo_mm", 10.0 if not is_vitifolia else 18.0))
    l_sepal = l_petal * (1.08 if not is_vitifolia else 1.05)
    w_sepal = w_petal * (1.22 if not is_vitifolia else 1.08)

    # =========================================================================
    # 1. PEDICELO Y COPA EXTERNA DEL HIPANTO (g Pedicelo_Hipanto)
    # =========================================================================
    mb.group("Pedicelo_Hipanto")
    mb.material("Mat_Caliz")

    ped_pts = [
        (0.0, -34.0, -3.5),
        (0.0, -24.0, -2.2),
        (0.0, -14.0, -1.0),
        (0.0, -7.5, -0.2),
        (0.0, -4.0, 0.0),
    ]
    ped_r = [1.7, 1.8, 1.95, 2.15, 2.8]
    ped_col = [(0.36, 0.58, 0.26)] * len(ped_pts)
    mb.add_tube(ped_pts, ped_r, ped_col, radial_segs=14, cap_start=True, cap_end=False)

    n_cup, s_cup = 12, 32
    cup_rings = []
    for i in range(n_cup):
        t = i / (n_cup - 1)
        y_c = -4.0 + t * 4.4
        r_c = 2.8 + 6.0 * math.sin(t * math.pi * 0.62)
        c_cup = _lerp_color((0.44, 0.66, 0.32), (0.68, 0.82, 0.52), t)
        ring = []
        for s in range(s_cup):
            ang = s * (2.0 * math.pi / s_cup)
            mod = 1.0 + 0.035 * math.cos(5.0 * ang) + 0.015 * math.cos(10.0 * ang)
            ring.append(mb.v(r_c * mod * math.cos(ang), y_c, r_c * mod * math.sin(ang), *c_cup))
        cup_rings.append(ring)

    for i in range(n_cup - 1):
        for s in range(s_cup):
            sn = (s + 1) % s_cup
            mb.quad(cup_rings[i][s], cup_rings[i][sn], cup_rings[i + 1][s], cup_rings[i + 1][sn])

    # =========================================================================
    # 2. BRÁCTEAS INVOLUCRALES FOLIÁCEAS CON VENACIÓN RETICULADA (g Epicaliz_Bracteas_Involucrales)
    # =========================================================================
    mb.group("Epicaliz_Bracteas_Involucrales")
    mb.material("Mat_Caliz")

    bract_len = 22.0 if not is_vitifolia else 16.0
    bract_w = 14.0 if not is_vitifolia else 8.5
    nu_b, nv_b = 18, 12
    y_bract_base = -5.6

    for b_idx in range(3):
        b_ang = b_idx * (2.0 * math.pi / 3.0) + math.pi / 6.0
        ca, sa = math.cos(b_ang), math.sin(b_ang)
        tx, tz = -sa, ca

        top_grid, bot_grid = [], []
        for i in range(nu_b + 1):
            v = i / nu_b
            # Contorno ovado-cordado foliáceo (típico de P. ligularis)
            w_loc = (bract_w * 0.5) * math.sin(math.pi * (v ** 0.65)) * (1.0 - 0.12 * v)
            r_reach = 2.4 + bract_len * (v ** 0.86) * 0.72
            y_curve = y_bract_base - 2.2 * math.sin(v * math.pi * 0.65) - 4.5 * (v ** 1.4)

            row_t, row_b = [], []
            for j in range(nv_b + 1):
                u = (j / nv_b) - 0.5
                lat = u * 2.0 * w_loc
                cup_lift = 1.8 * (u * u) * math.sin(math.pi * v)

                # Venación reticulada estilo Araceae
                mid_vein = math.exp(-((u / 0.08) ** 2))
                sec_veins = 0.55 * (math.cos(10.0 * v * math.pi - 4.5 * abs(u)) ** 4) * (1.0 - mid_vein)
                vein_mask = min(1.0, mid_vein + sec_veins)
                rel = 0.18 * vein_mask

                px = r_reach * ca + lat * tx
                pz = r_reach * sa + lat * tz
                py = y_curve + cup_lift + rel

                c_blade = _lerp_color((0.30, 0.56, 0.22), (0.58, 0.78, 0.42), vein_mask * 0.65)
                row_t.append(mb.v(px, py + 0.14, pz, *c_blade))
                row_b.append(mb.v(px, py - 0.14, pz, *(c_blade[0] * 0.88, c_blade[1] * 0.88, c_blade[2] * 0.88)))
            top_grid.append(row_t)
            bot_grid.append(row_b)

        for i in range(nu_b):
            for j in range(nv_b):
                mb.quad(top_grid[i][j], top_grid[i][j + 1], top_grid[i + 1][j], top_grid[i + 1][j + 1])
                mb.quad(bot_grid[i][j + 1], bot_grid[i][j], bot_grid[i + 1][j + 1], bot_grid[i + 1][j])

        # Glándulas nectaríferas marginales en preantesis
        for v_gland in [0.20, 0.38]:
            w_g = (bract_w * 0.5) * math.sin(math.pi * (v_gland ** 0.65)) * (1.0 - 0.12 * v_gland)
            r_g = 2.4 + bract_len * (v_gland ** 0.86) * 0.72
            y_g = y_bract_base - 2.2 * math.sin(v_gland * math.pi * 0.65) - 4.5 * (v_gland ** 1.4) + 0.35
            for side in [-1.0, 1.0]:
                gx = r_g * ca + (side * w_g) * tx
                gz = r_g * sa + (side * w_g) * tz
                g_pts = [(gx, y_g - 0.45, gz), (gx, y_g, gz), (gx, y_g + 0.45, gz)]
                mb.add_tube(g_pts, [0.18, 0.52, 0.18], [(0.48, 0.74, 0.24)] * 3, radial_segs=8, cap_start=True, cap_end=True)

    # =========================================================================
    # 3. CÁLIZ: 5 SÉPALOS FUERTEMENTE RETROFLEXOS Y AQUILLADOS (g Caliz_Sepalos)
    # =========================================================================
    mb.group("Caliz_Sepalos")
    mb.material("Mat_Caliz")

    nv_p, nu_p = 30, 14
    c_sepal_adaxial = (0.88, 0.12, 0.16) if is_vitifolia else (0.92, 0.96, 0.88)
    c_sepal_abaxial = (0.54, 0.74, 0.40)

    for k in range(5):
        base_ang = k * (2.0 * math.pi / 5.0)
        ca, sa = math.cos(base_ang), math.sin(base_ang)
        tx, tz = -sa, ca

        top_grid, bot_grid = [], []
        horn_base_pos = None

        for i in range(nv_p + 1):
            v = i / nv_p
            if v < 0.18:
                w_prof = math.sin((math.pi * 0.5) * (v / 0.18))
            elif v < 0.80:
                w_prof = 1.0 - 0.10 * ((v - 0.18) / 0.62)
            else:
                t_tip = (v - 0.80) / 0.20
                w_prof = 0.90 * math.sqrt(max(0.0, 1.0 - (t_tip ** 2)))
            w_loc = (w_sepal * 0.5) * w_prof

            # En P. ligularis los sépalos son fuertemente retroflexos (doblados hacia abajo/atrás)
            if is_vitifolia:
                r_proj = 7.8 + l_sepal * (v ** 0.92) * 0.92
                y_prof = -0.2 + 1.8 * math.sin(math.pi * v * 0.55) - 6.5 * (v ** 1.7)
            else:
                r_proj = 7.8 + l_sepal * (0.76 * (v ** 0.85) - 0.10 * (v ** 2.2))
                y_prof = -0.1 + 1.2 * math.sin(math.pi * v * 0.40) - 18.5 * (v ** 1.45)

            row_t, row_b = [], []
            for j in range(nu_p + 1):
                u = (j / nu_p) - 0.5
                lat = u * 2.0 * w_loc
                gutter = 0.95 * (u * u) * math.sin(math.pi * v)

                keel = 1.55 * math.sin(math.pi * (v ** 0.8)) * math.exp(-((u / 0.16) ** 2))
                thick = 0.52 * math.sin(math.pi * v) * (1.0 - 0.45 * abs(u))
                vein_s = 0.04 * math.cos(u * 16.0) * math.sin(v * 3.0 * math.pi)

                px = r_proj * ca + lat * tx
                pz = r_proj * sa + lat * tz
                py_top = y_prof + gutter + vein_s
                py_bot = y_prof + gutter - thick - keel

                # Margen blanquecino-verdoso en la cara adaxial con nervio central pálido
                margin_tint = _ss(0.32, 0.50, abs(u))
                c_top = _lerp_color(c_sepal_adaxial, (0.84, 0.92, 0.78), margin_tint * 0.55)
                row_t.append(mb.v(px, py_top, pz, *c_top))

                keel_blend = math.exp(-((u / 0.32) ** 2))
                c_bot = _lerp_color((0.74, 0.86, 0.62), c_sepal_abaxial, keel_blend)
                row_b.append(mb.v(px, py_bot, pz, *c_bot))

                if abs(v - 0.88) < (0.5 / nv_p) and j == nu_p // 2:
                    horn_base_pos = (px, py_bot, pz)

            top_grid.append(row_t)
            bot_grid.append(row_b)

        for i in range(nv_p):
            for j in range(nu_p):
                mb.quad(top_grid[i][j], top_grid[i][j + 1], top_grid[i + 1][j], top_grid[i + 1][j + 1])
                mb.quad(bot_grid[i][j + 1], bot_grid[i][j], bot_grid[i + 1][j + 1], bot_grid[i + 1][j])
            mb.quad(bot_grid[i][0], top_grid[i][0], bot_grid[i + 1][0], top_grid[i + 1][0])
            mb.quad(top_grid[i][-1], bot_grid[i][-1], top_grid[i + 1][-1], bot_grid[i + 1][-1])

        # Cornículo dorsal subapical (aristado)
        if horn_base_pos is not None:
            hx, hy, hz = horn_base_pos
            horn_pts = [
                (hx - 0.3 * ca, hy + 0.2, hz - 0.3 * sa),
                (hx + 0.9 * ca, hy - 1.0, hz + 0.9 * sa),
                (hx + 2.0 * ca, hy - 2.2, hz + 2.0 * sa),
                (hx + 2.7 * ca, hy - 3.0, hz + 2.7 * sa),
            ]
            mb.add_tube(horn_pts, [0.62, 0.42, 0.22, 0.05], [(0.48, 0.70, 0.34)] * 4, radial_segs=8, cap_end=True)

    # =========================================================================
    # 4. COROLA: 5 PÉTALOS REFLEXOS (30 x 10 mm) CON PUNTEADO PÚRPURA (g Corola_Petalos)
    # =========================================================================
    mb.group("Corola_Petalos")
    mb.material("Mat_CorolaLimbo")

    c_petal_base = (0.92, 0.14, 0.18) if is_vitifolia else (0.97, 0.96, 0.99)
    c_petal_spot = (0.48, 0.10, 0.44)

    for k in range(5):
        base_ang = k * (2.0 * math.pi / 5.0) + (math.pi / 5.0)
        ca, sa = math.cos(base_ang), math.sin(base_ang)
        tx, tz = -sa, ca

        top_grid, bot_grid = [], []
        for i in range(nv_p + 1):
            v = i / nv_p
            if v < 0.18:
                w_prof = math.sin((math.pi * 0.5) * (v / 0.18))
            elif v < 0.82:
                w_prof = 1.0 - 0.08 * ((v - 0.18) / 0.64)
            else:
                t_tip = (v - 0.82) / 0.18
                w_prof = 0.92 * math.sqrt(max(0.0, 1.0 - (t_tip ** 2)))
            w_loc = (w_petal * 0.5) * w_prof

            # Postura fuertemente reflexa en P. ligularis (30 x 10 mm)
            if is_vitifolia:
                r_proj = 7.6 + l_petal * (v ** 0.92) * 0.92
                y_prof = 0.3 + 2.0 * math.sin(math.pi * v * 0.55) - 5.2 * (v ** 1.65)
            else:
                r_proj = 7.5 + l_petal * (0.78 * (v ** 0.86) - 0.08 * (v ** 2.1))
                y_prof = 0.2 + 1.4 * math.sin(math.pi * v * 0.42) - 16.2 * (v ** 1.45)

            row_t, row_b = [], []
            for j in range(nu_p + 1):
                u = (j / nu_p) - 0.5
                lat = u * 2.0 * w_loc
                gutter = 0.65 * (u * u) * math.sin(math.pi * v)
                thick = 0.26 * math.sin(math.pi * v)

                px = r_proj * ca + lat * tx
                pz = r_proj * sa + lat * tz
                py_top = y_prof + gutter
                py_bot = y_prof + gutter - thick

                if is_vitifolia:
                    cp_top = c_petal_base
                    cp_bot = c_petal_base
                else:
                    # Punteado púrpura denso en cara adaxial, más disperso hacia la base (v < 0.25)
                    spot_field = (
                        math.sin(28.0 * v * math.pi + 11.0 * u + k * 1.7)
                        * math.cos(19.0 * u * math.pi - 15.0 * v + k * 2.3)
                        + 0.35 * _lowfreq(v * 30.0, u * 20.0, seed=float(k))
                    )
                    density_thresh = 0.58 - 0.30 * _ss(0.12, 0.65, v)
                    spot_mask = _ss(density_thresh, density_thresh + 0.18, spot_field) * (1.0 - 0.35 * _ss(0.85, 1.0, v))
                    rose_flush = 0.14 * _ss(0.25, 0.80, v) * (1.0 - abs(u))
                    base_ivory = _lerp_color(c_petal_base, (0.92, 0.84, 0.95), rose_flush)
                    cp_top = _lerp_color(base_ivory, c_petal_spot, spot_mask * 0.78)
                    cp_bot = _lerp_color((0.95, 0.94, 0.97), (0.88, 0.80, 0.92), rose_flush)

                row_t.append(mb.v(px, py_top, pz, *cp_top))
                row_b.append(mb.v(px, py_bot, pz, *cp_bot))
            top_grid.append(row_t)
            bot_grid.append(row_b)

        for i in range(nv_p):
            for j in range(nu_p):
                mb.quad(top_grid[i][j], top_grid[i][j + 1], top_grid[i + 1][j], top_grid[i + 1][j + 1])
                mb.quad(bot_grid[i][j + 1], bot_grid[i][j], bot_grid[i + 1][j + 1], bot_grid[i + 1][j])
            mb.quad(bot_grid[i][0], top_grid[i][0], bot_grid[i + 1][0], top_grid[i + 1][0])
            mb.quad(top_grid[i][-1], bot_grid[i][-1], top_grid[i + 1][-1], bot_grid[i + 1][-1])

    # =========================================================================
    # 5. CORONA MULTISERIADA EXTERNA: RADII CEBRA CON ÁPICES RIZADOS (g Corona_Filamentos_Radii)
    # =========================================================================
    mb.group("Corona_Filamentos_Radii")
    mb.material("Mat_CoronaVioleta")

    ns_fil = 36  # Alta resolución longitudinal para el bandeado cebra y el rizo apical
    outer_whorls = [
        {"count": 62, "r_base": 7.5, "y_base": 0.5, "len": 31.0, "lift": 11.5, "A_z": 1.85, "A_t": 0.95},
        {"count": 56, "r_base": 6.8, "y_base": 0.9, "len": 28.0, "lift": 13.0, "A_z": 1.65, "A_t": 0.80},
    ]

    for w_idx, w_cfg in enumerate(outer_whorls):
        cnt = w_cfg["count"]
        for i in range(cnt):
            ang = i * (2.0 * math.pi / cnt) + (w_idx * math.pi / cnt)
            ca, sa = math.cos(ang), math.sin(ang)
            tx, tz = -sa, ca
            phase_shift = 0.65 * math.sin(i * 0.73 + w_idx * 1.4)
            color_jitter = math.sin(i * 1.37 + w_idx)

            f_pts, f_rad, f_col = [], [], []
            for j in range(ns_fil + 1):
                s = j / ns_fil
                # Elevación campanulada/acopada hacia adelante (como en las fotos de P. ligularis)
                r_dist = w_cfg["r_base"] + w_cfg["len"] * (s ** 0.88)
                y_base_arch = (
                    w_cfg["y_base"]
                    + w_cfg["lift"] * math.sin(math.pi * 0.62 * (s ** 0.78))
                    - 1.8 * (s ** 2.4)
                )

                # Rizo sinusoidal pronunciado en el cuarto apical blanco (s > 0.72)
                curl_env = _ss(0.62, 0.98, s)
                delta_vertical = w_cfg["A_z"] * curl_env * math.sin(7.0 * math.pi * s + phase_shift)
                delta_tangent = w_cfg["A_t"] * curl_env * math.cos(6.0 * math.pi * s + phase_shift)

                px = r_dist * ca + delta_tangent * tx
                pz = r_dist * sa + delta_tangent * tz
                py = y_base_arch + delta_vertical

                # Filamentos liguliformes subulados: firmes en el cuerpo y finos en el ápice rizado
                rad = 0.46 * ((1.0 - s) ** 0.65) + 0.11 * s
                col = _corona_radii_color(s, is_vitifolia, phase=color_jitter)

                f_pts.append((px, py, pz))
                f_rad.append(rad)
                f_col.append(col)

            mb.add_tube(f_pts, f_rad, f_col, radial_segs=6, cap_start=False, cap_end=True)

    # =========================================================================
    # 6. CORONA INTERNA: PALI Y ANILLO PURPÚREO DE LA GARGANTA (g Corona_Interna_Pali)
    # =========================================================================
    mb.group("Corona_Interna_Pali")
    mb.material("Mat_CorolaGarganta")

    pali_whorls = [
        {"count": 50, "r_base": 6.1, "y_base": 0.7, "height": 3.8, "tilt": 0.35},
        {"count": 44, "r_base": 5.4, "y_base": 0.6, "height": 3.1, "tilt": 0.10},
        {"count": 38, "r_base": 4.8, "y_base": 0.5, "height": 2.4, "tilt": -0.20},
        {"count": 32, "r_base": 4.2, "y_base": 0.3, "height": 1.8, "tilt": -0.35},
    ]

    for p_idx, p_cfg in enumerate(pali_whorls):
        cnt = p_cfg["count"]
        for i in range(cnt):
            ang = i * (2.0 * math.pi / cnt) + (p_idx * 0.09)
            ca, sa = math.cos(ang), math.sin(ang)

            p_pts, p_rad, p_col = [], [], []
            steps_p = 7
            for j in range(steps_p + 1):
                s = j / steps_p
                r_curr = p_cfg["r_base"] + p_cfg["tilt"] * (s ** 1.3)
                y_curr = p_cfg["y_base"] + p_cfg["height"] * s

                if s < 0.72:
                    rad = 0.24 - 0.05 * (s / 0.72)
                else:
                    t_cap = (s - 0.72) / 0.28
                    rad = 0.19 + 0.13 * math.sin(t_cap * math.pi * 0.85)

                if s < 0.76:
                    col = (0.30, 0.03, 0.20)
                else:
                    col = _lerp_color((0.30, 0.03, 0.20), (0.96, 0.92, 0.98), (s - 0.76) / 0.24)

                p_pts.append((r_curr * ca, y_curr, r_curr * sa))
                p_rad.append(rad)
                p_col.append(col)

            mb.add_tube(p_pts, p_rad, p_col, radial_segs=6, cap_start=False, cap_end=True)

    # =========================================================================
    # 7. COLUMNA AXIAL: ANDROGINÓFORO CON TRÓCLEA Y MOTEADO (g Columna_Androginoforo)
    # =========================================================================
    mb.group("Columna_Androginoforo")
    mb.material("Mat_Filamento")

    h_androg = 10.2
    n_col, s_col = 22, 22
    col_rings = []
    for i in range(n_col + 1):
        t = i / n_col
        y_c = t * h_androg
        # Incluye dilatación basal anular (tróclea en t ~ 0.18) y fuste cilíndrico firme
        trochlea = 0.48 * math.exp(-(((t - 0.18) / 0.09) ** 2))
        r_c = 1.75 + 0.70 * math.exp(-t * 6.5) + trochlea + 0.25 * math.exp(-(1.0 - t) * 8.0)
        ring = []
        for s in range(s_col):
            ang = s * (2.0 * math.pi / s_col)
            mottle = math.sin(16.0 * t * math.pi + 2.0 * ang) * math.cos(7.0 * ang - 9.0 * t)
            if mottle > 0.38:
                inten = min(1.0, (mottle - 0.38) / 0.45)
                col = _lerp_color((0.90, 0.95, 0.82), (0.46, 0.10, 0.38), inten * 0.80)
            else:
                col = (0.90, 0.95, 0.82)
            ring.append(mb.v(r_c * math.cos(ang), y_c, r_c * math.sin(ang), *col))
        col_rings.append(ring)

    for i in range(n_col):
        for s in range(s_col):
            sn = (s + 1) % s_col
            mb.quad(col_rings[i][s], col_rings[i][sn], col_rings[i + 1][s], col_rings[i + 1][sn])

    # =========================================================================
    # 8. ANDROCEO: 5 FILAMENTOS LIBRES Y ANTERAS OBLONGAS DE 5-8 mm (g Androceo_Estambres)
    # =========================================================================
    mb.group("Androceo_Estambres")
    mb.material("Mat_Antera")

    ant_len = float(androceo.get("antera_longitud_mm", 6.5))
    y_stamen_origin = h_androg - 0.3
    for k in range(5):
        a_st = k * (2.0 * math.pi / 5.0) + (math.pi / 10.0)
        ca, sa = math.cos(a_st), math.sin(a_st)
        tx, tz = -sa, ca

        nf_steps, nf_w = 16, 6
        f_top, f_bot = [], []
        tip_pos = None

        for i in range(nf_steps + 1):
            t = i / nf_steps
            r_f = 1.6 + 8.2 * (t ** 0.92)
            y_f = y_stamen_origin + 1.2 * math.sin(math.pi * t * 0.65) - 2.2 * (t ** 1.75)
            w_ribbon = 0.82 * (1.0 - 0.30 * t)
            th_ribbon = 0.25 * (1.0 - 0.22 * t)

            if i == nf_steps:
                tip_pos = (r_f * ca, y_f, r_f * sa)

            rt_row, rb_row = [], []
            for j in range(nf_w + 1):
                u = (j / nf_w) - 0.5
                lat = u * 2.0 * w_ribbon
                px = r_f * ca + lat * tx
                pz = r_f * sa + lat * tz

                spot = math.sin(24.0 * t + 9.0 * u + k) * math.cos(15.0 * t - 7.0 * u)
                c_top = _lerp_color((0.82, 0.92, 0.66), (0.48, 0.12, 0.42), 0.72 if spot > 0.46 else 0.0)
                c_bot = (0.80, 0.90, 0.64)

                rt_row.append(mb.v(px, y_f + th_ribbon, pz, *c_top))
                rb_row.append(mb.v(px, y_f - th_ribbon, pz, *c_bot))
            f_top.append(rt_row)
            f_bot.append(rb_row)

        for i in range(nf_steps):
            for j in range(nf_w):
                mb.quad(f_top[i][j], f_top[i][j + 1], f_top[i + 1][j], f_top[i + 1][j + 1])
                mb.quad(f_bot[i][j + 1], f_bot[i][j], f_bot[i + 1][j + 1], f_bot[i + 1][j])
            mb.quad(f_bot[i][0], f_top[i][0], f_bot[i + 1][0], f_top[i + 1][0])
            mb.quad(f_top[i][-1], f_bot[i][-1], f_top[i + 1][-1], f_bot[i + 1][-1])

        # Antera oblonga versátil bilocular (6.5 mm x 2.7 mm) amarillo polen dorado
        ax, ay, az = tip_pos
        ant_w = 2.7
        ant_th = 0.78
        na_u, na_v = 18, 16
        ant_rings = []

        for i in range(na_u + 1):
            u = (i / na_u) - 0.5
            u_norm = u * 2.0
            env_l = math.sqrt(max(0.0, 1.0 - 0.80 * (u_norm * u_norm)))
            s_along = u * ant_len
            arch_y = -0.22 * (u_norm * u_norm)

            ring = []
            for j in range(na_v):
                ang = j * (2.0 * math.pi / na_v)
                ca_a, sa_a = math.cos(ang), math.sin(ang)

                theca_pinch = 1.0 - 0.40 * (math.exp(-((ca_a / 0.28) ** 2)))
                rad_w = (ant_w * 0.5) * env_l * ca_a
                rad_h = ant_th * env_l * sa_a * theca_pinch

                px = ax + s_along * tx + rad_w * ca
                pz = az + s_along * tz + rad_w * sa
                py = (ay - 0.45) + arch_y + rad_h

                if sa_a >= 0.0:
                    col_a = _lerp_color((0.92, 0.84, 0.22), (0.80, 0.86, 0.36), sa_a)
                else:
                    col_a = _lerp_color((0.95, 0.82, 0.16), (0.98, 0.76, 0.10), -sa_a)
                ring.append(mb.v(px, py, pz, *col_a))
            ant_rings.append(ring)

        for i in range(na_u):
            for j in range(na_v):
                jn = (j + 1) % na_v
                mb.quad(ant_rings[i][j], ant_rings[i][jn], ant_rings[i + 1][j], ant_rings[i + 1][jn])

        c_left = mb.v(ax - 0.5 * ant_len * tx, ay - 0.68, az - 0.5 * ant_len * tz, 0.94, 0.82, 0.20)
        c_right = mb.v(ax + 0.5 * ant_len * tx, ay - 0.68, az + 0.5 * ant_len * tz, 0.94, 0.82, 0.20)
        for j in range(na_v):
            jn = (j + 1) % na_v
            mb.f(c_left, ant_rings[0][jn], ant_rings[0][j])
            mb.f(c_right, ant_rings[-1][j], ant_rings[-1][jn])

    # =========================================================================
    # 9. GINECEO EXTERNO: OVARIO SÚPERO OVOIDE GLABRO (g Gineceo_Ovario_Supero)
    # =========================================================================
    mb.group("Gineceo_Ovario_Supero")
    mb.material("Mat_Ovario")

    ov_base_y = h_androg - 0.1
    ov_h = 6.4
    ov_rx = 2.45
    no_u, no_v = 20, 24
    ov_rings = []

    for i in range(no_u + 1):
        v = i / no_u
        theta_v = v * math.pi
        y_ov = ov_base_y + ov_h * (0.5 - 0.5 * math.cos(theta_v))
        r_ov = ov_rx * math.sin(theta_v)
        if i == 0 or i == no_u:
            r_ov = 0.28

        ring = []
        for j in range(no_v):
            ang = j * (2.0 * math.pi / no_v)
            carpel_flute = 1.0 + 0.03 * math.cos(3.0 * ang)
            gloss_shade = 0.95 + 0.05 * math.cos(3.0 * ang) + 0.04 * math.sin(theta_v)
            # Verde manzana brillante y glabro en P. ligularis
            c_ov = (0.56 * gloss_shade, 0.78 * gloss_shade, 0.28 * gloss_shade)
            ring.append(mb.v(r_ov * carpel_flute * math.cos(ang), y_ov, r_ov * carpel_flute * math.sin(ang), *c_ov))
        ov_rings.append(ring)

    for i in range(no_u):
        for j in range(no_v):
            jn = (j + 1) % no_v
            mb.quad(ov_rings[i][j], ov_rings[i][jn], ov_rings[i + 1][j], ov_rings[i + 1][jn])

    top_cap_ov = mb.v(0.0, ov_base_y + ov_h, 0.0, 0.56, 0.78, 0.28)
    for j in range(no_v):
        jn = (j + 1) % no_v
        mb.f(top_cap_ov, ov_rings[-1][j], ov_rings[-1][jn])

    # =========================================================================
    # 10. ESTILOS CURVOS DESCENDENTES Y ESTIGMAS RENIFORMES (g Gineceo_Estilos_Estigmas)
    # =========================================================================
    mb.group("Gineceo_Estilos_Estigmas")
    mb.material("Mat_Estilo")

    y_style_origin = ov_base_y + ov_h - 0.25
    n_st = 18

    for k in range(3):
        a_sy = k * (2.0 * math.pi / 3.0) + (math.pi / 6.0)
        ca, sa = math.cos(a_sy), math.sin(a_sy)
        tx, tz = -sa, ca

        st_pts, st_rad, st_col = [], [], []
        for i in range(n_st + 1):
            t = i / n_st
            r_s = 0.35 + 8.2 * (t ** 0.88)
            y_s = y_style_origin + 2.8 * math.sin(math.pi * (t ** 0.72)) - 4.2 * (t ** 2.0)
            rad_s = 0.48 + 0.58 * (t ** 1.35)

            sp = math.sin(21.0 * t + k * 2.1)
            c_s = _lerp_color((0.90, 0.95, 0.80), (0.48, 0.14, 0.42), 0.65 if sp > 0.32 else 0.0)

            st_pts.append((r_s * ca, y_s, r_s * sa))
            st_rad.append(rad_s)
            st_col.append(c_s)

        mb.add_tube(st_pts, st_rad, st_col, radial_segs=12, cap_start=True, cap_end=True)

        sx, sy, sz = st_pts[-1]
        ns_u, ns_v = 14, 16
        stig_rings = []
        for i in range(ns_u + 1):
            v = i / ns_u
            phi = v * math.pi
            sin_p, cos_p = math.sin(phi), math.cos(phi)
            ring = []
            for j in range(ns_v):
                theta = j * (2.0 * math.pi / ns_v)
                ct, st = math.cos(theta), math.sin(theta)

                lobe_w = 1.95 * sin_p * ct
                indent = 0.42 * (1.0 - ct * ct) * max(0.0, st)
                lobe_r = (1.40 * sin_p * st) - indent
                lobe_h = 0.98 * cos_p * (1.0 + 0.18 * (ct * ct))

                pap = 1.0 + 0.03 * math.sin(6.0 * phi) * math.cos(8.0 * theta)

                tilt_a = 0.62
                r_rot = lobe_r * math.cos(tilt_a) - lobe_h * math.sin(tilt_a)
                y_rot = lobe_r * math.sin(tilt_a) + lobe_h * math.cos(tilt_a)

                px = sx + 0.35 * ca + (lobe_w * pap) * tx + (r_rot * pap) * ca
                pz = sz + 0.35 * sa + (lobe_w * pap) * tz + (r_rot * pap) * sa
                py = sy - 0.15 + (y_rot * pap)

                shade_st = 0.94 + 0.08 * cos_p
                c_stig = (0.76 * shade_st, 0.90 * shade_st, 0.48 * shade_st)
                ring.append(mb.v(px, py, pz, *c_stig))
            stig_rings.append(ring)

        for i in range(ns_u):
            for j in range(ns_v):
                jn = (j + 1) % ns_v
                mb.quad(stig_rings[i][j], stig_rings[i][jn], stig_rings[i + 1][j], stig_rings[i + 1][jn])

        p_top = mb.v(
            sx + 0.35 * ca - 0.98 * math.sin(0.62) * ca,
            sy - 0.15 + 0.98 * math.cos(0.62),
            sz + 0.35 * sa - 0.98 * math.sin(0.62) * sa,
            0.76, 0.90, 0.48,
        )
        p_bot = mb.v(
            sx + 0.35 * ca + 0.98 * math.sin(0.62) * ca,
            sy - 0.15 - 0.98 * math.cos(0.62),
            sz + 0.35 * sa + 0.98 * math.sin(0.62) * sa,
            0.72, 0.86, 0.44,
        )
        for j in range(ns_v):
            jn = (j + 1) % ns_v
            mb.f(p_top, stig_rings[0][jn], stig_rings[0][j])
            mb.f(p_bot, stig_rings[-1][j], stig_rings[-1][jn])

    # =========================================================================
    # 11. ANATOMÍA INTERNA: PLACENTACIÓN PARIETAL Y ÓVULOS (g Ovulos_Placentacion_Parietal)
    # =========================================================================
    mb.group("Ovulos_Placentacion_Parietal")
    mb.material("Mat_Blanco")

    r_inner_max = ov_rx * 0.78
    for p_idx in range(3):
        p_ang = p_idx * (2.0 * math.pi / 3.0)
        ca, sa = math.cos(p_ang), math.sin(p_ang)
        tx, tz = -sa, ca

        cord_pts, cord_r, cord_c = [], [], []
        n_cord = 14
        for i in range(n_cord + 1):
            v = 0.12 + 0.76 * (i / n_cord)
            theta_v = v * math.pi
            y_p = ov_base_y + ov_h * (0.5 - 0.5 * math.cos(theta_v))
            r_p = r_inner_max * math.sin(theta_v)
            cord_pts.append((r_p * ca, y_p, r_p * sa))
            cord_r.append(0.28 * math.sin(theta_v))
            cord_c.append((0.90, 0.88, 0.72))

        mb.add_tube(cord_pts, cord_r, cord_c, radial_segs=8, cap_start=True, cap_end=True)

        n_ovules = 7
        for ov_i in range(n_ovules):
            v = 0.18 + 0.64 * (ov_i / (n_ovules - 1))
            theta_v = v * math.pi
            y_p = ov_base_y + ov_h * (0.5 - 0.5 * math.cos(theta_v))
            r_wall = r_inner_max * math.sin(theta_v)

            for row_side in [-1.0, 1.0]:
                wx = r_wall * ca + (row_side * 0.24) * tx
                wz = r_wall * sa + (row_side * 0.24) * tz

                ox = (r_wall - 0.52) * ca + (row_side * 0.42) * tx
                oz = (r_wall - 0.52) * sa + (row_side * 0.42) * tz
                oy = y_p + (0.12 * row_side)

                fun_pts = [(wx, y_p, wz), ((wx + ox) * 0.5, y_p + 0.15, (wz + oz) * 0.5), (ox, oy, oz)]
                mb.add_tube(fun_pts, [0.10, 0.09, 0.12], [(0.90, 0.88, 0.72)] * 3, radial_segs=6)

                ov_u_pts = [
                    (ox, oy - 0.42, oz),
                    (ox, oy - 0.22, oz),
                    (ox, oy, oz),
                    (ox, oy + 0.22, oz),
                    (ox, oy + 0.42, oz),
                ]
                ov_u_rad = [0.08, 0.32, 0.42, 0.32, 0.08]
                ov_u_col = [(0.98, 0.96, 0.88)] * 5
                mb.add_tube(ov_u_pts, ov_u_rad, ov_u_col, radial_segs=8, cap_start=True, cap_end=True)

    # =========================================================================
    # 12. ANATOMÍA INTERNA: CÁMARA NECTARÍFERA, OPÉRCULO Y LIMEN (g Camara_Nectarifera_Interna)
    # =========================================================================
    mb.group("Camara_Nectarifera_Interna")
    mb.material("Mat_CorolaGarganta")

    s_nec = 28
    r_torus_maj = 3.85
    r_torus_min = 0.58
    y_torus = -2.4
    nt_minor = 10
    torus_rings = []
    for i in range(nt_minor):
        ang_m = i * (2.0 * math.pi / nt_minor)
        cm, sm = math.cos(ang_m), math.sin(ang_m)
        r_ring = r_torus_maj + r_torus_min * cm
        y_ring = y_torus + r_torus_min * sm
        ring = []
        for s in range(s_nec):
            ang = s * (2.0 * math.pi / s_nec)
            ring.append(mb.v(r_ring * math.cos(ang), y_ring, r_ring * math.sin(ang), 0.85, 0.92, 0.65))
        torus_rings.append(ring)

    for i in range(nt_minor):
        inext = (i + 1) % nt_minor
        for s in range(s_nec):
            sn = (s + 1) % s_nec
            mb.quad(torus_rings[i][s], torus_rings[i][sn], torus_rings[inext][s], torus_rings[inext][sn])

    limen_prof = [
        (1.95, -2.5, (0.86, 0.90, 0.76)),
        (2.55, -2.2, (0.88, 0.92, 0.78)),
        (2.95, -1.1, (0.90, 0.92, 0.84)),
        (2.75, -0.4, (0.76, 0.52, 0.82)),
        (2.45, -1.2, (0.86, 0.88, 0.78)),
    ]
    limen_rings = []
    for r_l, y_l, col_l in limen_prof:
        ring = []
        for s in range(s_nec):
            ang = s * (2.0 * math.pi / s_nec)
            ring.append(mb.v(r_l * math.cos(ang), y_l, r_l * math.sin(ang), *col_l))
        limen_rings.append(ring)

    for i in range(len(limen_rings) - 1):
        for s in range(s_nec):
            sn = (s + 1) % s_nec
            mb.quad(limen_rings[i][s], limen_rings[i][sn], limen_rings[i + 1][s], limen_rings[i + 1][sn])

    op_prof = [
        (5.40, -0.3, (0.68, 0.42, 0.78)),
        (4.45, -1.2, (0.76, 0.52, 0.82)),
        (3.35, -1.4, (0.86, 0.72, 0.90)),
        (3.10, -0.2, (0.92, 0.94, 0.86)),
        (3.30, 0.5, (0.94, 0.96, 0.90)),
    ]
    op_rings = []
    for idx_op, (r_o, y_o, col_o) in enumerate(op_prof):
        ring = []
        for s in range(s_nec):
            ang = s * (2.0 * math.pi / s_nec)
            plic = 0.14 * math.sin(16.0 * ang) if idx_op >= 2 else 0.0
            # Moteado púrpura fino en el diafragma interno como en las fotos de P. ligularis
            sp_op = math.sin(12.0 * ang + idx_op * 1.9)
            c_op = _lerp_color(col_o, (0.42, 0.08, 0.34), 0.55 if sp_op > 0.45 else 0.0)
            ring.append(mb.v((r_o + plic) * math.cos(ang), y_o + plic * 0.5, (r_o + plic) * math.sin(ang), *c_op))
        op_rings.append(ring)

    for i in range(len(op_rings) - 1):
        for s in range(s_nec):
            sn = (s + 1) % s_nec
            mb.quad(op_rings[i][s], op_rings[i][sn], op_rings[i + 1][s], op_rings[i + 1][sn])

    # =========================================================================
    # 13. ANATOMÍA INTERNA: SISTEMA VASCULAR CENTRAL (g Eje_Vascular_Interno)
    # =========================================================================
    mb.group("Eje_Vascular_Interno")
    mb.material("Mat_Filamento")

    c_vasc = (0.82, 0.88, 0.68)
    vasc_trunk = [
        (0.0, -32.0, -3.2),
        (0.0, -22.0, -2.0),
        (0.0, -12.0, -0.8),
        (0.0, -4.0, 0.0),
        (0.0, 2.5, 0.0),
        (0.0, 6.5, 0.0),
        (0.0, h_androg - 0.2, 0.0),
    ]
    mb.add_tube(vasc_trunk, [0.48, 0.52, 0.55, 0.62, 0.58, 0.58, 0.65], [c_vasc] * 7, radial_segs=10, cap_start=True, cap_end=True)

    for k in range(5):
        a_st = k * (2.0 * math.pi / 5.0) + (math.pi / 10.0)
        ca, sa = math.cos(a_st), math.sin(a_st)
        st_trace = [
            (0.0, h_androg - 0.8, 0.0),
            (1.1 * ca, h_androg - 0.3, 1.1 * sa),
            (2.8 * ca, h_androg + 0.2, 2.8 * sa),
        ]
        mb.add_tube(st_trace, [0.24, 0.20, 0.14], [c_vasc] * 3, radial_segs=6, cap_end=True)

    for p_idx in range(3):
        p_ang = p_idx * (2.0 * math.pi / 3.0)
        ca, sa = math.cos(p_ang), math.sin(p_ang)
        pl_trace = [
            (0.0, h_androg - 0.2, 0.0),
            (0.85 * ca, ov_base_y + 0.6, 0.85 * sa),
            (1.55 * ca, ov_base_y + ov_h * 0.5, 1.55 * sa),
            (0.65 * ca, ov_base_y + ov_h - 0.3, 0.65 * sa),
        ]
        mb.add_tube(pl_trace, [0.22, 0.18, 0.16, 0.15], [c_vasc] * 4, radial_segs=6, cap_end=True)

    return mb.build_obj()