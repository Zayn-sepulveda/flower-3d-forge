import math
from geometry import NL


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

            # Vector auxiliar para producto cruz evitando singularidad
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


def _corona_radii_color(s, is_vitifolia=False):
    """Bandeado cromático exacto de 4 zonas para los filamentos exteriores (Radii)."""
    if is_vitifolia:
        if s < 0.25:
            return (0.65, 0.04, 0.08)
        elif s < 0.50:
            return (0.96, 0.94, 0.94)
        else:
            return (0.92, 0.12, 0.15)

    c_base = (0.38, 0.05, 0.32)   # Púrpura amatista oscuro [0.0, 0.22]
    c_mid  = (0.96, 0.96, 0.98)   # Blanco puro brillante [0.22, 0.48]
    c_dist = (0.62, 0.38, 0.82)   # Lavanda violáceo [0.48, 0.78]
    c_apex = (0.82, 0.68, 0.94)   # Lila pálido a blanquecino [0.78, 1.0]

    if s <= 0.20:
        return c_base
    elif s <= 0.24:
        return _lerp_color(c_base, c_mid, (s - 0.20) / 0.04)
    elif s <= 0.46:
        return c_mid
    elif s <= 0.50:
        return _lerp_color(c_mid, c_dist, (s - 0.46) / 0.04)
    elif s <= 0.76:
        return c_dist
    elif s <= 0.80:
        return _lerp_color(c_dist, c_apex, (s - 0.76) / 0.04)
    else:
        return c_apex


def build_passiflora_flower(cfg):
    """
    Generador morfométrico e histológico para Passifloraceae (Passiflora incarnata / P. vitifolia):
    Incluye Epicáliz glandular, Cáliz carena-corniculado, Corola laminar suave,
    Corona multiseriada sin aliasing (Radii + Pali), Androginóforo moteado,
    Androceo con filamentos acintados y anteras versátiles biloculares en 'T',
    Gineceo con ovario súpero velutino, estilos claviformes y estigmas reniformes sólidos,
    más Anatomía Interna (Placentación parietal con óvulos anátropos, Cámara nectarífera con
    opérculo/limen y Sistema vascular central ramificado).
    """
    mb = ObjMeshBuilder()

    especie = str(cfg.get('taxonomia', {}).get('especie', '')).lower()
    is_vitifolia = 'vitifolia' in especie

    corola = cfg.get('perianto', {}).get('corola', {})
    l_petal = float(corola.get('longitud_limbo_mm', 36.0 if not is_vitifolia else 55.0))
    w_petal = float(corola.get('ancho_petalo_mm', 12.5 if not is_vitifolia else 15.0))
    l_sepal = l_petal * 1.05
    w_sepal = w_petal * 1.08

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
        (0.0, -4.0, 0.0)
    ]
    ped_r = [1.8, 1.9, 2.0, 2.2, 2.8]
    ped_col = [(0.38, 0.60, 0.28)] * len(ped_pts)
    mb.add_tube(ped_pts, ped_r, ped_col, radial_segs=14, cap_start=True, cap_end=False)

    # Copa externa del hipanto (con cavidad urceolada basal)
    n_cup, s_cup = 10, 28
    cup_rings = []
    for i in range(n_cup):
        t = i / (n_cup - 1)
        y_c = -4.0 + t * 4.2
        r_c = 2.8 + 5.8 * math.sin(t * math.pi * 0.62)
        c_cup = _lerp_color((0.42, 0.64, 0.32), (0.58, 0.74, 0.44), t)
        ring = []
        for s in range(s_cup):
            ang = s * (2.0 * math.pi / s_cup)
            # Sutiles depresiones intrastaminales del hipanto
            mod = 1.0 + 0.04 * math.cos(5.0 * ang)
            ring.append(mb.v(r_c * mod * math.cos(ang), y_c, r_c * mod * math.sin(ang), *c_cup))
        cup_rings.append(ring)

    for i in range(n_cup - 1):
        for s in range(s_cup):
            sn = (s + 1) % s_cup
            mb.quad(cup_rings[i][s], cup_rings[i][sn], cup_rings[i + 1][s], cup_rings[i + 1][sn])

    # =========================================================================
    # 2. BRÁCTEAS INVOLUCRALES (EPICÁLIZ) CON GLÁNDULAS (g Epicaliz_Bracteas_Involucrales)
    # =========================================================================
    mb.group("Epicaliz_Bracteas_Involucrales")
    mb.material("Mat_Caliz")

    bract_len = 13.5
    bract_w = 7.2
    nu_b, nv_b = 14, 8
    y_bract_base = -7.2

    for b_idx in range(3):
        b_ang = b_idx * (2.0 * math.pi / 3.0) + math.pi / 6.0
        ca, sa = math.cos(b_ang), math.sin(b_ang)
        tx, tz = -sa, ca

        top_grid, bot_grid = [], []
        for i in range(nu_b + 1):
            v = i / nu_b
            # Perfil ovado-lanceolado cóncavo hacia arriba
            w_loc = (bract_w * 0.5) * math.sin(math.pi * (v ** 0.72)) * (1.0 - 0.15 * v)
            r_reach = 2.1 + bract_len * (v ** 0.88) * 0.78
            y_curve = y_bract_base - 1.2 * math.sin(v * math.pi * 0.5) + 4.8 * (v ** 1.5)

            row_t, row_b = [], []
            for j in range(nv_b + 1):
                u = (j / nv_b) - 0.5
                lat = u * 2.0 * w_loc
                cup_lift = 1.6 * (u * u) * math.sin(math.pi * v)

                px = r_reach * ca + lat * tx
                pz = r_reach * sa + lat * tz
                py = y_curve + cup_lift

                c_bract = _lerp_color((0.32, 0.54, 0.22), (0.38, 0.62, 0.28), 0.5 - abs(u))
                row_t.append(mb.v(px, py + 0.15, pz, *c_bract))
                row_b.append(mb.v(px, py - 0.15, pz, *(c_bract[0] * 0.9, c_bract[1] * 0.9, c_bract[2] * 0.9)))
            top_grid.append(row_t)
            bot_grid.append(row_b)

        for i in range(nu_b):
            for j in range(nv_b):
                mb.quad(top_grid[i][j], top_grid[i][j + 1], top_grid[i + 1][j], top_grid[i + 1][j + 1])
                mb.quad(bot_grid[i][j + 1], bot_grid[i][j], bot_grid[i + 1][j + 1], bot_grid[i + 1][j])

        # 2 pares de glándulas nectaríferas marginales esféricas por bráctea
        for v_gland in [0.22, 0.36]:
            w_g = (bract_w * 0.5) * math.sin(math.pi * (v_gland ** 0.72)) * (1.0 - 0.15 * v_gland)
            r_g = 2.1 + bract_len * (v_gland ** 0.88) * 0.78
            y_g = y_bract_base - 1.2 * math.sin(v_gland * math.pi * 0.5) + 4.8 * (v_gland ** 1.5) + 0.4
            for side in [-1.0, 1.0]:
                gx = r_g * ca + (side * w_g) * tx
                gz = r_g * sa + (side * w_g) * tz
                gy = y_g
                g_pts = [(gx, gy - 0.55, gz), (gx, gy, gz), (gx, gy + 0.55, gz)]
                g_rad = [0.20, 0.62, 0.20]
                g_col = [(0.48, 0.72, 0.20)] * 3
                mb.add_tube(g_pts, g_rad, g_col, radial_segs=8, cap_start=True, cap_end=True)

    # =========================================================================
    # 3. CÁLIZ: 5 SÉPALOS CARENA-CORNICULADOS (g Caliz_Sepalos)
    # =========================================================================
    mb.group("Caliz_Sepalos")
    mb.material("Mat_Caliz")

    nv_p, nu_p = 26, 12
    c_sepal_adaxial = (0.88, 0.12, 0.16) if is_vitifolia else (0.85, 0.82, 0.90)
    c_sepal_abaxial = (0.62, 0.76, 0.48)

    for k in range(5):
        base_ang = k * (2.0 * math.pi / 5.0)
        ca, sa = math.cos(base_ang), math.sin(base_ang)
        tx, tz = -sa, ca

        top_grid, bot_grid = [], []
        horn_base_pos = None

        for i in range(nv_p + 1):
            v = i / nv_p
            # Perfil elíptico-obtuso continuo sin facetas poligonales
            if v < 0.20:
                w_prof = math.sin((math.pi * 0.5) * (v / 0.20))
            elif v < 0.82:
                w_prof = 1.0 - 0.08 * ((v - 0.20) / 0.62)
            else:
                t_tip = (v - 0.82) / 0.18
                w_prof = 0.92 * math.sqrt(max(0.0, 1.0 - (t_tip ** 2)))
            w_loc = (w_sepal * 0.5) * w_prof
            r_proj = 7.8 + l_sepal * (v ** 0.92) * 0.92
            y_prof = -0.2 + 1.8 * math.sin(math.pi * v * 0.55) - 6.5 * (v ** 1.7)

            row_t, row_b = [], []
            for j in range(nu_p + 1):
                u = (j / nu_p) - 0.5
                lat = u * 2.0 * w_loc
                gutter = 1.1 * (u * u) * math.sin(math.pi * v)

                # Quilla dorsal (carina) en el envés abaxial
                keel = 1.45 * math.sin(math.pi * (v ** 0.8)) * math.exp(-((u / 0.18) ** 2))
                thick = 0.55 * math.sin(math.pi * v) * (1.0 - 0.5 * abs(u))

                px = r_proj * ca + lat * tx
                pz = r_proj * sa + lat * tz
                py_top = y_prof + gutter
                py_bot = y_prof + gutter - thick - keel

                row_t.append(mb.v(px, py_top, pz, *c_sepal_adaxial))
                # El envés es verde amarillento en la quilla y bordes abaxiales
                keel_blend = math.exp(-((u / 0.35) ** 2))
                c_bot = _lerp_color((0.68, 0.78, 0.54), c_sepal_abaxial, keel_blend)
                row_b.append(mb.v(px, py_bot, pz, *c_bot))

                if abs(v - 0.88) < (0.5 / nv_p) and j == nu_p // 2:
                    horn_base_pos = (px, py_bot, pz)

            top_grid.append(row_t)
            bot_grid.append(row_b)

        for i in range(nv_p):
            for j in range(nu_p):
                mb.quad(top_grid[i][j], top_grid[i][j + 1], top_grid[i + 1][j], top_grid[i + 1][j + 1])
                mb.quad(bot_grid[i][j + 1], bot_grid[i][j], bot_grid[i + 1][j + 1], bot_grid[i + 1][j])
            # Costura de márgenes laterales
            mb.quad(bot_grid[i][0], top_grid[i][0], bot_grid[i + 1][0], top_grid[i + 1][0])
            mb.quad(top_grid[i][-1], bot_grid[i][-1], top_grid[i + 1][-1], bot_grid[i + 1][-1])

        # Mucrón o cuernito subapical (corniculum) de 2.5 mm en v = 0.88
        if horn_base_pos is not None:
            hx, hy, hz = horn_base_pos
            horn_pts = [
                (hx - 0.4 * ca, hy + 0.3, hz - 0.4 * sa),
                (hx + 0.9 * ca, hy - 0.8, hz + 0.9 * sa),
                (hx + 2.1 * ca, hy - 1.6, hz + 2.1 * sa),
                (hx + 2.8 * ca, hy - 2.1, hz + 2.8 * sa)
            ]
            horn_r = [0.65, 0.45, 0.22, 0.05]
            horn_c = [(0.52, 0.70, 0.38)] * 4
            mb.add_tube(horn_pts, horn_r, horn_c, radial_segs=8, cap_start=False, cap_end=True)

    # =========================================================================
    # 4. COROLA: 5 PÉTALOS LAMINARES SUAVES (g Corola_Petalos)
    # =========================================================================
    mb.group("Corola_Petalos")
    mb.material("Mat_CorolaLimbo")

    c_petal = (0.92, 0.14, 0.18) if is_vitifolia else (0.80, 0.64, 0.90)

    for k in range(5):
        base_ang = k * (2.0 * math.pi / 5.0) + (math.pi / 5.0)
        ca, sa = math.cos(base_ang), math.sin(base_ang)
        tx, tz = -sa, ca

        top_grid, bot_grid = [], []
        for i in range(nv_p + 1):
            v = i / nv_p
            if v < 0.20:
                w_prof = math.sin((math.pi * 0.5) * (v / 0.20))
            elif v < 0.82:
                w_prof = 1.0 - 0.08 * ((v - 0.20) / 0.62)
            else:
                t_tip = (v - 0.82) / 0.18
                w_prof = 0.92 * math.sqrt(max(0.0, 1.0 - (t_tip ** 2)))
            w_loc = (w_petal * 0.5) * w_prof
            r_proj = 7.6 + l_petal * (v ** 0.92) * 0.92
            y_prof = 0.3 + 2.0 * math.sin(math.pi * v * 0.55) - 5.2 * (v ** 1.65)

            row_t, row_b = [], []
            for j in range(nu_p + 1):
                u = (j / nu_p) - 0.5
                lat = u * 2.0 * w_loc
                gutter = 0.85 * (u * u) * math.sin(math.pi * v)
                thick = 0.28 * math.sin(math.pi * v)

                px = r_proj * ca + lat * tx
                pz = r_proj * sa + lat * tz
                py_top = y_prof + gutter
                py_bot = y_prof + gutter - thick

                shade = 1.0 - 0.06 * abs(u)
                cp = (c_petal[0] * shade, c_petal[1] * shade, c_petal[2] * shade)
                row_t.append(mb.v(px, py_top, pz, *cp))
                row_b.append(mb.v(px, py_bot, pz, *cp))
            top_grid.append(row_t)
            bot_grid.append(row_b)

        for i in range(nv_p):
            for j in range(nu_p):
                mb.quad(top_grid[i][j], top_grid[i][j + 1], top_grid[i + 1][j], top_grid[i + 1][j + 1])
                mb.quad(bot_grid[i][j + 1], bot_grid[i][j], bot_grid[i + 1][j + 1], bot_grid[i + 1][j])
            mb.quad(bot_grid[i][0], top_grid[i][0], bot_grid[i + 1][0], top_grid[i + 1][0])
            mb.quad(top_grid[i][-1], bot_grid[i][-1], top_grid[i + 1][-1], bot_grid[i + 1][-1])

    # =========================================================================
    # 5. CORONA MULTISERIADA EXTERNA: RADII SIN ALIASING (g Corona_Filamentos_Radii)
    # =========================================================================
    mb.group("Corona_Filamentos_Radii")
    mb.material("Mat_CoronaVioleta")

    ns_fil = 32  # >= 18 segmentos longitudinales para curva suave libre de aliasing
    outer_whorls = [
        {"count": 56, "r_base": 7.6, "y_base": 0.6, "len": 28.0, "lift": 3.2, "A_z": 2.1, "A_t": 0.75},
        {"count": 50, "r_base": 6.8, "y_base": 0.9, "len": 23.5, "lift": 4.2, "A_z": 1.8, "A_t": 0.60},
    ]

    for w_idx, w_cfg in enumerate(outer_whorls):
        cnt = w_cfg["count"]
        for i in range(cnt):
            ang = i * (2.0 * math.pi / cnt) + (w_idx * math.pi / cnt)
            ca, sa = math.cos(ang), math.sin(ang)
            tx, tz = -sa, ca
            phase_shift = 0.25 * math.sin(i * 0.5)

            f_pts, f_rad, f_col = [], [], []
            for j in range(ns_fil + 1):
                s = j / ns_fil
                # Mitad basal recta/ascendente (s < 0.5); mitad distal con onda sinusoidal suave
                r_dist = w_cfg["r_base"] + w_cfg["len"] * (s ** 0.96)
                y_base_arch = w_cfg["y_base"] + w_cfg["lift"] * math.sin(math.pi * (s ** 0.85)) - 2.4 * (s ** 1.8)

                wave_env = max(0.0, s - 0.40) ** 1.4
                delta_vertical = w_cfg["A_z"] * wave_env * math.sin(5.5 * math.pi * s + phase_shift)
                delta_tangent = w_cfg["A_t"] * wave_env * math.cos(4.5 * math.pi * s + phase_shift)

                px = r_dist * ca + delta_tangent * tx
                pz = r_dist * sa + delta_tangent * tz
                py = y_base_arch + delta_vertical

                # Adelgazamiento progresivo desde 0.45 mm hasta 0.12 mm
                rad = 0.45 * (1.0 - s) + 0.12 * s
                col = _corona_radii_color(s, is_vitifolia)

                f_pts.append((px, py, pz))
                f_rad.append(rad)
                f_col.append(col)

            mb.add_tube(f_pts, f_rad, f_col, radial_segs=6, cap_start=False, cap_end=True)

    # =========================================================================
    # 6. CORONA INTERNA: PALI CAPITADOS (g Corona_Interna_Pali)
    # =========================================================================
    mb.group("Corona_Interna_Pali")
    mb.material("Mat_CorolaGarganta")

    pali_whorls = [
        {"count": 46, "r_base": 5.9, "y_base": 0.7, "height": 3.6, "tilt": 0.4},
        {"count": 40, "r_base": 5.2, "y_base": 0.6, "height": 3.0, "tilt": 0.1},
        {"count": 34, "r_base": 4.6, "y_base": 0.5, "height": 2.4, "tilt": -0.25},
    ]

    for p_idx, p_cfg in enumerate(pali_whorls):
        cnt = p_cfg["count"]
        for i in range(cnt):
            ang = i * (2.0 * math.pi / cnt) + (p_idx * 0.08)
            ca, sa = math.cos(ang), math.sin(ang)

            p_pts, p_rad, p_col = [], [], []
            steps_p = 7
            for j in range(steps_p + 1):
                s = j / steps_p
                r_curr = p_cfg["r_base"] + p_cfg["tilt"] * (s ** 1.3)
                y_curr = p_cfg["y_base"] + p_cfg["height"] * s

                # Ligeramente capitados (engrosados en la punta s ~ 0.85)
                if s < 0.72:
                    rad = 0.24 - 0.05 * (s / 0.72)
                else:
                    t_cap = (s - 0.72) / 0.28
                    rad = 0.19 + 0.13 * math.sin(t_cap * math.pi * 0.85)

                if s < 0.78:
                    col = (0.35, 0.04, 0.25)
                else:
                    col = _lerp_color((0.35, 0.04, 0.25), (0.95, 0.90, 0.96), (s - 0.78) / 0.22)

                p_pts.append((r_curr * ca, y_curr, r_curr * sa))
                p_rad.append(rad)
                p_col.append(col)

            mb.add_tube(p_pts, p_rad, p_col, radial_segs=6, cap_start=False, cap_end=True)

    # =========================================================================
    # 7. COLUMNA AXIAL: ANDROGINÓFORO CON MOTEADO (g Columna_Androginoforo)
    # =========================================================================
    mb.group("Columna_Androginoforo")
    mb.material("Mat_Filamento")

    h_androg = 9.6
    n_col, s_col = 20, 20
    col_rings = []
    for i in range(n_col + 1):
        t = i / n_col
        y_c = t * h_androg
        # Ensanchado en la base (radio 2.5 mm) y cilindro firme de 1.8 mm en el fuste
        r_c = 1.80 + 0.75 * math.exp(-t * 6.5) + 0.25 * math.exp(-(1.0 - t) * 8.0)
        ring = []
        for s in range(s_col):
            ang = s * (2.0 * math.pi / s_col)
            # Sutil moteado púrpura paramétrico sobre base blanco-verdosa (0.88, 0.92, 0.82)
            mottle = math.sin(16.0 * t * math.pi + 2.0 * ang) * math.cos(7.0 * ang - 9.0 * t)
            if mottle > 0.42:
                inten = min(1.0, (mottle - 0.42) / 0.45)
                col = _lerp_color((0.88, 0.92, 0.82), (0.52, 0.16, 0.46), inten * 0.75)
            else:
                col = (0.88, 0.92, 0.82)
            ring.append(mb.v(r_c * math.cos(ang), y_c, r_c * math.sin(ang), *col))
        col_rings.append(ring)

    for i in range(n_col):
        for s in range(s_col):
            sn = (s + 1) % s_col
            mb.quad(col_rings[i][s], col_rings[i][sn], col_rings[i + 1][s], col_rings[i + 1][sn])

    # =========================================================================
    # 8. ANDROCEO: 5 FILAMENTOS ACINTADOS Y ANTERAS VERSÁTILES BILOCULARES (g Androceo_Estambres)
    # =========================================================================
    mb.group("Androceo_Estambres")
    mb.material("Mat_Antera")

    y_stamen_origin = h_androg - 0.3
    for k in range(5):
        a_st = k * (2.0 * math.pi / 5.0) + (math.pi / 10.0)
        ca, sa = math.cos(a_st), math.sin(a_st)
        tx, tz = -sa, ca

        # A. Filamento estaminal acintado (aplanado dorsiventralmente)
        nf_steps, nf_w = 16, 6
        f_top, f_bot = [], []
        tip_pos = None

        for i in range(nf_steps + 1):
            t = i / nf_steps
            r_f = 1.6 + 8.6 * (t ** 0.92)
            y_f = y_stamen_origin + 1.1 * math.sin(math.pi * t * 0.65) - 2.6 * (t ** 1.8)
            w_ribbon = 0.72 * (1.0 - 0.35 * t)
            th_ribbon = 0.22 * (1.0 - 0.25 * t)

            if i == nf_steps:
                tip_pos = (r_f * ca, y_f, r_f * sa)

            rt_row, rb_row = [], []
            for j in range(nf_w + 1):
                u = (j / nf_w) - 0.5
                lat = u * 2.0 * w_ribbon
                px = r_f * ca + lat * tx
                pz = r_f * sa + lat * tz

                # Micropuntos púrpura sobre verde claro en la cara adaxial del filamento
                spot = math.sin(22.0 * t + 9.0 * u) * math.cos(14.0 * t - 7.0 * u)
                c_top = _lerp_color((0.80, 0.90, 0.70), (0.50, 0.14, 0.44), 0.75 if spot > 0.48 else 0.0)
                c_bot = (0.78, 0.88, 0.68)

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

        # B. Antera versátil bilocular (6.0 mm x 2.5 mm) en inserción dorsifija en "T"
        ax, ay, az = tip_pos
        ant_len = 6.0
        ant_w = 2.5
        ant_th = 0.72
        na_u, na_v = 18, 16
        ant_rings = []

        for i in range(na_u + 1):
            u = (i / na_u) - 0.5  # Longitudinal a lo largo del eje tangencial [-0.5, 0.5]
            u_norm = u * 2.0      # [-1, 1]
            env_l = math.sqrt(max(0.0, 1.0 - 0.82 * (u_norm * u_norm)))
            s_along = u * ant_len
            # Suave arqueamiento natural de la antera
            arch_y = -0.25 * (u_norm * u_norm)

            ring = []
            for j in range(na_v):
                ang = j * (2.0 * math.pi / na_v)
                ca_a, sa_a = math.cos(ang), math.sin(ang)

                # Surco longitudinal medio que divide la antera en 2 tecas paralelas
                theca_pinch = 1.0 - 0.38 * (math.exp(-((ca_a / 0.28) ** 2)))
                rad_w = (ant_w * 0.5) * env_l * ca_a
                rad_h = ant_th * env_l * sa_a * theca_pinch

                px = ax + s_along * tx + rad_w * ca
                pz = az + s_along * tz + rad_w * sa
                py = (ay - 0.45) + arch_y + rad_h

                # Cara dorsal superior amarillo-verdosa (0.82, 0.86, 0.45);
                # Cara ventral inferior dehiscente amarillo polen intenso (0.96, 0.84, 0.15)
                if sa_a >= 0.0:
                    col_a = _lerp_color((0.88, 0.86, 0.32), (0.82, 0.86, 0.45), sa_a)
                else:
                    col_a = _lerp_color((0.88, 0.86, 0.32), (0.96, 0.84, 0.15), -sa_a)
                ring.append(mb.v(px, py, pz, *col_a))
            ant_rings.append(ring)

        for i in range(na_u):
            for j in range(na_v):
                jn = (j + 1) % na_v
                mb.quad(ant_rings[i][j], ant_rings[i][jn], ant_rings[i + 1][j], ant_rings[i + 1][jn])

        # Tapas sólidas en ambos extremos de la antera bilocular
        c_left = mb.v(ax - 0.5 * ant_len * tx, ay - 0.70, az - 0.5 * ant_len * tz, 0.90, 0.85, 0.28)
        c_right = mb.v(ax + 0.5 * ant_len * tx, ay - 0.70, az + 0.5 * ant_len * tz, 0.90, 0.85, 0.28)
        for j in range(na_v):
            jn = (j + 1) % na_v
            mb.f(c_left, ant_rings[0][jn], ant_rings[0][j])
            mb.f(c_right, ant_rings[-1][j], ant_rings[-1][jn])

    # =========================================================================
    # 9. GINECEO EXTERNO: OVARIO SÚPERO GLOBOSO (g Gineceo_Ovario_Supero)
    # =========================================================================
    mb.group("Gineceo_Ovario_Supero")
    mb.material("Mat_Ovario")

    # Elipsoide prominente y globoso (6.0 mm alto x 4.5 mm diámetro) en la cima del androginóforo
    ov_base_y = h_androg - 0.1
    ov_h = 6.0
    ov_rx = 2.25
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
            # Sutil modulación tricarpelar y sombreado velutino sedoso (0.76, 0.86, 0.68)
            carpel_flute = 1.0 + 0.035 * math.cos(3.0 * ang)
            velvet_shade = 0.96 + 0.04 * math.cos(3.0 * ang) + 0.03 * math.sin(theta_v)
            c_ov = (0.76 * velvet_shade, 0.86 * velvet_shade, 0.68 * velvet_shade)
            ring.append(mb.v(r_ov * carpel_flute * math.cos(ang), y_ov, r_ov * carpel_flute * math.sin(ang), *c_ov))
        ov_rings.append(ring)

    for i in range(no_u):
        for j in range(no_v):
            jn = (j + 1) % no_v
            mb.quad(ov_rings[i][j], ov_rings[i][jn], ov_rings[i + 1][j], ov_rings[i + 1][jn])

    top_cap_ov = mb.v(0.0, ov_base_y + ov_h, 0.0, 0.76, 0.86, 0.68)
    for j in range(no_v):
        jn = (j + 1) % no_v
        mb.f(top_cap_ov, ov_rings[-1][j], ov_rings[-1][jn])

    # =========================================================================
    # 10. ESTILOS CLAVIFORMES (n=18) Y ESTIGMAS RENIFORMES SÓLIDOS (g Gineceo_Estilos_Estigmas)
    # =========================================================================
    mb.group("Gineceo_Estilos_Estigmas")
    mb.material("Mat_Estilo")

    y_style_origin = ov_base_y + ov_h - 0.25
    n_st = 18  # 18 segmentos longitudinales para arco continuo sin quiebres

    for k in range(3):
        a_sy = k * (2.0 * math.pi / 3.0) + (math.pi / 6.0)
        ca, sa = math.cos(a_sy), math.sin(a_sy)
        tx, tz = -sa, ca

        st_pts, st_rad, st_col = [], [], []
        for i in range(n_st + 1):
            t = i / n_st
            # Arco continuo divergente y recurvado hacia abajo
            r_s = 0.35 + 8.4 * (t ** 0.88)
            y_s = y_style_origin + 3.2 * math.sin(math.pi * (t ** 0.75)) - 3.6 * (t ** 2.1)

            # Engrosamiento progresivo claviforme desde 0.50 mm hasta 1.10 mm
            rad_s = 0.50 + 0.60 * (t ** 1.35)

            # Blanco-crema verdoso (0.92, 0.94, 0.86) con manchas púrpura
            sp = math.sin(19.0 * t + k * 2.1)
            c_s = _lerp_color((0.92, 0.94, 0.86), (0.52, 0.16, 0.46), 0.65 if sp > 0.35 else 0.0)

            st_pts.append((r_s * ca, y_s, r_s * sa))
            st_rad.append(rad_s)
            st_col.append(c_s)

        mb.add_tube(st_pts, st_rad, st_col, radial_segs=12, cap_start=True, cap_end=True)

        # Estigma sólido bilobulado/reniforme (completamente cerrado, sin hueco central)
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

                # Geometría reniforme (arriñonada/bilobulada) cerrada e inclinada hacia afuera
                lobe_w = 1.85 * sin_p * ct
                indent = 0.38 * (1.0 - ct * ct) * max(0.0, st)
                lobe_r = (1.35 * sin_p * st) - indent
                lobe_h = 0.95 * cos_p * (1.0 + 0.18 * (ct * ct))

                # Papilas superficiales suaves
                pap = 1.0 + 0.03 * math.sin(6.0 * phi) * math.cos(8.0 * theta)

                # Rotación de 35° hacia afuera y abajo
                tilt_a = 0.62
                r_rot = lobe_r * math.cos(tilt_a) - lobe_h * math.sin(tilt_a)
                y_rot = lobe_r * math.sin(tilt_a) + lobe_h * math.cos(tilt_a)

                px = sx + 0.35 * ca + (lobe_w * pap) * tx + (r_rot * pap) * ca
                pz = sz + 0.35 * sa + (lobe_w * pap) * tz + (r_rot * pap) * sa
                py = sy - 0.15 + (y_rot * pap)

                shade_st = 0.94 + 0.08 * cos_p
                c_stig = (0.68 * shade_st, 0.84 * shade_st, 0.42 * shade_st)
                ring.append(mb.v(px, py, pz, *c_stig))
            stig_rings.append(ring)

        for i in range(ns_u):
            for j in range(ns_v):
                jn = (j + 1) % ns_v
                mb.quad(stig_rings[i][j], stig_rings[i][jn], stig_rings[i + 1][j], stig_rings[i + 1][jn])

        # Cierre polar superior e inferior del estigma reniforme
        p_top = mb.v(sx + 0.35 * ca - 0.95 * math.sin(0.62) * ca, sy - 0.15 + 0.95 * math.cos(0.62), sz + 0.35 * sa - 0.95 * math.sin(0.62) * sa, 0.68, 0.84, 0.42)
        p_bot = mb.v(sx + 0.35 * ca + 0.95 * math.sin(0.62) * ca, sy - 0.15 - 0.95 * math.cos(0.62), sz + 0.35 * sa + 0.95 * math.sin(0.62) * sa, 0.64, 0.80, 0.38)
        for j in range(ns_v):
            jn = (j + 1) % ns_v
            mb.f(p_top, stig_rings[0][jn], stig_rings[0][j])
            mb.f(p_bot, stig_rings[-1][j], stig_rings[-1][jn])

    # =========================================================================
    # 11. ANATOMÍA INTERNA: PLACENTACIÓN PARIETAL Y ÓVULOS (g Ovulos_Placentacion_Parietal)
    # =========================================================================
    mb.group("Ovulos_Placentacion_Parietal")
    mb.material("Mat_Blanco")

    # 3 Cordones placentarios parietales (a 0°, 120° y 240° al 80% del radio interno del ovario)
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

        # 2 Hileras verticales de 7 óvulos anátropos por placenta (con funículo corto)
        n_ovules = 7
        for ov_i in range(n_ovules):
            v = 0.18 + 0.64 * (ov_i / (n_ovules - 1))
            theta_v = v * math.pi
            y_p = ov_base_y + ov_h * (0.5 - 0.5 * math.cos(theta_v))
            r_wall = r_inner_max * math.sin(theta_v)

            for row_side in [-1.0, 1.0]:
                # Funículo corto desde la pared placentaria hacia el lóculo
                wx = r_wall * ca + (row_side * 0.24) * tx
                wz = r_wall * sa + (row_side * 0.24) * tz

                ox = (r_wall - 0.52) * ca + (row_side * 0.42) * tx
                oz = (r_wall - 0.52) * sa + (row_side * 0.42) * tz
                oy = y_p + (0.12 * row_side)

                fun_pts = [(wx, y_p, wz), ((wx + ox) * 0.5, y_p + 0.15, (wz + oz) * 0.5), (ox, oy, oz)]
                mb.add_tube(fun_pts, [0.10, 0.09, 0.12], [(0.90, 0.88, 0.72)] * 3, radial_segs=6)

                # Cuerpo del óvulo anátropo (esferita elipsoide de 0.42 mm radio en blanco marfil)
                ov_u_pts = [
                    (ox, oy - 0.42, oz),
                    (ox, oy - 0.22, oz),
                    (ox, oy, oz),
                    (ox, oy + 0.22, oz),
                    (ox, oy + 0.42, oz)
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
    # A. Toroide secretor (Anillo nectarífero inferior color ámbar claro 0.85, 0.92, 0.65)
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

    # B. Limen (anillo cupuliforme que abraza el pie del androginóforo)
    limen_prof = [
        (1.95, -2.5, (0.86, 0.90, 0.76)),
        (2.55, -2.2, (0.88, 0.92, 0.78)),
        (2.95, -1.1, (0.90, 0.92, 0.84)),
        (2.75, -0.4, (0.76, 0.52, 0.82)),
        (2.45, -1.2, (0.86, 0.88, 0.78))
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

    # C. Opérculo (membrana anular plegada hacia adentro que cierra el techo de la cámara nectarífera)
    op_prof = [
        (5.40, -0.3, (0.68, 0.42, 0.78)),
        (4.45, -1.2, (0.76, 0.52, 0.82)),
        (3.35, -1.4, (0.86, 0.72, 0.90)),
        (3.10, -0.2, (0.95, 0.92, 0.96)),
        (3.30, 0.5, (0.96, 0.94, 0.98))
    ]
    op_rings = []
    for idx_op, (r_o, y_o, col_o) in enumerate(op_prof):
        ring = []
        for s in range(s_nec):
            ang = s * (2.0 * math.pi / s_nec)
            # Pliegues finos (plicado) del opérculo
            plic = 0.12 * math.sin(14.0 * ang) if idx_op >= 2 else 0.0
            ring.append(mb.v((r_o + plic) * math.cos(ang), y_o + plic * 0.5, (r_o + plic) * math.sin(ang), *col_o))
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
    # Tronco vascular central desde el pedicelo hasta la base del ovario
    vasc_trunk = [
        (0.0, -32.0, -3.2),
        (0.0, -22.0, -2.0),
        (0.0, -12.0, -0.8),
        (0.0, -4.0, 0.0),
        (0.0, 2.5, 0.0),
        (0.0, 6.5, 0.0),
        (0.0, h_androg - 0.2, 0.0)
    ]
    mb.add_tube(vasc_trunk, [0.48, 0.52, 0.55, 0.62, 0.58, 0.58, 0.65], [c_vasc] * 7, radial_segs=10, cap_start=True, cap_end=True)

    # 5 Trazas vasculares estaminales hacia los filamentos
    for k in range(5):
        a_st = k * (2.0 * math.pi / 5.0) + (math.pi / 10.0)
        ca, sa = math.cos(a_st), math.sin(a_st)
        st_trace = [
            (0.0, h_androg - 0.8, 0.0),
            (1.1 * ca, h_androg - 0.3, 1.1 * sa),
            (2.8 * ca, h_androg + 0.2, 2.8 * sa)
        ]
        mb.add_tube(st_trace, [0.24, 0.20, 0.14], [c_vasc] * 3, radial_segs=6, cap_end=True)

    # 3 Trazas vasculares placentarias ascendentes hacia las placentas y los estilos
    for p_idx in range(3):
        p_ang = p_idx * (2.0 * math.pi / 3.0)
        ca, sa = math.cos(p_ang), math.sin(p_ang)
        pl_trace = [
            (0.0, h_androg - 0.2, 0.0),
            (0.85 * ca, ov_base_y + 0.6, 0.85 * sa),
            (1.55 * ca, ov_base_y + ov_h * 0.5, 1.55 * sa),
            (0.65 * ca, ov_base_y + ov_h - 0.3, 0.65 * sa)
        ]
        mb.add_tube(pl_trace, [0.22, 0.18, 0.16, 0.15], [c_vasc] * 4, radial_segs=6, cap_end=True)

    return mb.build_obj()