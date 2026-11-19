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
    Construye el modelo anatomico 3D de alta fidelidad de Passifloraceae.
    Preserva los 13 grupos anatomicos (g) con morfometria real de P. ligularis:
    hipanto bulboso y ovario con doble pared carnosa, 3 bracteas ovado-cordadas
    con venacion reticulada suave, perianto reflexo patente con corniculo dorsal,
    moteado purpura organico, corona multiseriada densa con puntas blancas flexuosas,
    5 anteras biloculares pendulas y 3 estilos maculados con estigmas reniformes.
    """
    import random

    mb = ObjMeshBuilder()

    def _clamp_rgb(c):
        return (
            max(0.0, min(1.0, c[0])),
            max(0.0, min(1.0, c[1])),
            max(0.0, min(1.0, c[2])),
        )

    def _shade_rgb(c, factor):
        return _clamp_rgb((c[0] * factor, c[1] * factor, c[2] * factor))

    def _ligularis_corona_color(s, phase=0.0, ao_base=1.0):
        # Bandeado concentrico real de P. ligularis:
        # borgoña oscuro -> blanco -> purpura vino -> blanco -> amatista -> puntas blanco marfil
        sp = max(0.0, min(1.0, s + 0.018 * phase))
        c_burgundy = (0.28, 0.03, 0.16)
        c_ivory    = (0.96, 0.96, 0.98)
        c_plum     = (0.37, 0.05, 0.27)
        c_amethyst = (0.44, 0.23, 0.72)
        c_violet   = (0.60, 0.44, 0.86)
        c_tip      = (0.97, 0.97, 0.99)

        if sp < 0.13:
            col = _lerp_color((0.20, 0.02, 0.12), c_burgundy, sp / 0.13)
        elif sp < 0.17:
            col = _lerp_color(c_burgundy, c_ivory, _ss(0.13, 0.17, sp))
        elif sp < 0.27:
            col = c_ivory
        elif sp < 0.31:
            col = _lerp_color(c_ivory, c_plum, _ss(0.27, 0.31, sp))
        elif sp < 0.43:
            col = _lerp_color(c_plum, (0.32, 0.04, 0.24), (sp - 0.31) / 0.12)
        elif sp < 0.47:
            col = _lerp_color((0.32, 0.04, 0.24), c_ivory, _ss(0.43, 0.47, sp))
        elif sp < 0.56:
            col = c_ivory
        elif sp < 0.61:
            col = _lerp_color(c_ivory, c_amethyst, _ss(0.56, 0.61, sp))
        elif sp < 0.74:
            col = _lerp_color(c_amethyst, c_violet, (sp - 0.61) / 0.13)
        elif sp < 0.81:
            col = _lerp_color(c_violet, c_tip, _ss(0.74, 0.81, sp))
        else:
            col = c_tip

        return _shade_rgb(col, ao_base)

    colecta = cfg.get("colecta", {}) or cfg.get("taxonomia", {})
    especie = str(colecta.get("especie", "")).lower()
    is_vitifolia = "vitifolia" in especie
    _load_passiflora_photometric_tint(colecta.get("foto_campo", ""))

    corola = cfg.get("perianto", {}).get("corola", {})
    androceo = cfg.get("androceo", {})
    l_petal = float(corola.get("longitud_limbo_mm", 42.0 if not is_vitifolia else 65.0))
    w_petal = float(corola.get("ancho_petalo_mm", 12.2 if not is_vitifolia else 18.0))
    l_sepal = l_petal * (1.085 if not is_vitifolia else 1.05)
    w_sepal = w_petal * (1.38 if not is_vitifolia else 1.08)

    # =========================================================================
    # 1. PEDICELO Y HIPANTO BULBOSO CON DOBLE PARED CARNOSA (g Pedicelo_Hipanto)
    # =========================================================================
    mb.group("Pedicelo_Hipanto")
    mb.material("Mat_Caliz")

    ped_pts = [
        (0.0, -36.0, -2.6),
        (0.0, -28.0, -1.7),
        (0.0, -20.0, -0.9),
        (0.0, -14.0, -0.3),
        (0.0, -10.2, 0.0),
    ]
    ped_r = [2.15, 2.25, 2.40, 2.65, 3.35]
    ped_col = [
        (0.35, 0.56, 0.24),
        (0.39, 0.61, 0.26),
        (0.43, 0.65, 0.29),
        (0.47, 0.69, 0.32),
        (0.50, 0.72, 0.34),
    ]
    mb.add_tube(ped_pts, ped_r, ped_col, radial_segs=14, cap_start=True, cap_end=False)

    # Perfil externo + borde superior + pared interna de la camara nectarifera
    # (espesor carnoso real de ~1.4 mm visible en Corte Sagital)
    s_cup = 32
    if is_vitifolia:
        outer_prof = [
            (-8.5, 3.1, (0.44, 0.66, 0.30)),
            (-6.5, 5.2, (0.50, 0.70, 0.35)),
            (-3.5, 7.6, (0.58, 0.76, 0.42)),
            (-0.8, 8.6, (0.64, 0.80, 0.48)),
            (0.3,  8.8, (0.70, 0.84, 0.54)),
        ]
        inner_prof = [
            (0.3,  7.5, (0.82, 0.88, 0.72)),
            (-1.2, 7.1, (0.84, 0.89, 0.74)),
            (-4.2, 6.2, (0.85, 0.89, 0.76)),
            (-6.8, 4.0, (0.82, 0.86, 0.72)),
            (-7.4, 2.0, (0.78, 0.83, 0.68)),
        ]
    else:
        outer_prof = [
            (-10.4, 3.35, (0.44, 0.67, 0.29)),
            (-9.2,  6.20, (0.48, 0.71, 0.32)),
            (-7.3,  8.65, (0.53, 0.75, 0.37)),
            (-5.0,  9.55, (0.58, 0.78, 0.42)),
            (-2.6,  9.40, (0.65, 0.82, 0.48)),
            (-0.6,  9.55, (0.73, 0.86, 0.56)),
            (0.40,  9.75, (0.79, 0.89, 0.64)),
            (0.50,  8.85, (0.84, 0.91, 0.72)),
        ]
        inner_prof = [
            (0.30,  8.15, (0.86, 0.91, 0.76)),
            (-1.2,  7.95, (0.87, 0.91, 0.78)),
            (-3.4,  8.10, (0.86, 0.90, 0.77)),
            (-5.8,  7.75, (0.84, 0.88, 0.75)),
            (-7.8,  6.20, (0.81, 0.86, 0.72)),
            (-8.8,  3.80, (0.78, 0.84, 0.69)),
            (-9.0,  2.10, (0.76, 0.82, 0.66)),
        ]

    all_cup_prof = outer_prof + inner_prof
    cup_rings = []
    for idx_p, (y_c, r_c, c_cup) in enumerate(all_cup_prof):
        is_inner = idx_p >= len(outer_prof)
        ring = []
        for s in range(s_cup):
            ang = s * (2.0 * math.pi / s_cup)
            mod = 1.0 + (0.012 if is_inner else 0.028) * math.cos(5.0 * ang)
            # AO sutil en la cavidad interna y base del hipanto
            shade = 0.94 + 0.06 * math.cos(5.0 * ang)
            ring.append(mb.v(r_c * mod * math.cos(ang), y_c, r_c * mod * math.sin(ang), *_shade_rgb(c_cup, shade)))
        cup_rings.append(ring)

    for i in range(len(cup_rings) - 1):
        for s in range(s_cup):
            sn = (s + 1) % s_cup
            mb.quad(cup_rings[i][s], cup_rings[i][sn], cup_rings[i + 1][s], cup_rings[i + 1][sn])

    # =========================================================================
    # 2. 3 BRÁCTEAS INVOLUCRALES OVADO-CORDADAS CON VENACIÓN SUAVE (g Epicaliz_Bracteas_Involucrales)
    # =========================================================================
    mb.group("Epicaliz_Bracteas_Involucrales")
    mb.material("Mat_Caliz")

    bract_len = 29.5 if not is_vitifolia else 18.0
    bract_w = 23.5 if not is_vitifolia else 10.5
    nu_b, nv_b = 20, 14
    y_bract_base = -9.6 if not is_vitifolia else -7.2

    for b_idx in range(3):
        b_ang = b_idx * (2.0 * math.pi / 3.0) + math.pi / 6.0
        ca, sa = math.cos(b_ang), math.sin(b_ang)
        tx, tz = -sa, ca

        top_grid, bot_grid = [], []
        for i in range(nu_b + 1):
            v = i / nu_b
            # Contorno foliaceo ovado-cordado amplio en base y acuminado en apice
            base_bulge = math.sin(math.pi * (v ** 0.52))
            acuminate = (1.0 - 0.18 * (v ** 1.6))
            # Borde suavemente aserrado-glandular integrado en la lamina
            serr = 1.0 + 0.022 * math.sin(14.0 * math.pi * v) * math.sin(math.pi * v)
            w_loc = (bract_w * 0.5) * base_bulge * acuminate * serr

            # Las auriculas basales envuelven ligeramente hacia atras el hipanto bulboso
            r_reach = 2.6 + bract_len * (v ** 0.88) * 0.82
            y_curve = y_bract_base + 5.6 * math.sin(v * math.pi * 0.68) - 2.6 * (v ** 1.8)

            row_t, row_b = [], []
            for j in range(nv_b + 1):
                u = (j / nv_b) - 0.5
                au = abs(u)
                lat = u * 2.0 * w_loc
                # Concavidad abrazando la base del hipanto
                cup_lift = 3.2 * (u * u) * math.sin(math.pi * (v ** 0.75))
                cordate_back = -1.6 * (1.0 - v) * (au ** 1.4) * (1.0 - _ss(0.0, 0.35, v))

                # Venacion reticulada natural (nervio central + 5 pares de venas arqueadas de bajo contraste)
                mid_vein = math.exp(-((au / 0.048) ** 2)) * (1.0 - 0.45 * v)
                arc_coord = (v - 0.34 * (au ** 1.28)) * 5.5
                sec_veins = (
                    0.34
                    * (math.exp(-(((arc_coord - round(arc_coord)) / 0.14) ** 2)))
                    * _ss(0.05, 0.14, au)
                    * (1.0 - _ss(0.42, 0.50, au))
                    * (1.0 - 0.35 * v)
                )
                retic = 0.08 * _lowfreq(v * 18.0, u * 18.0, seed=float(b_idx + 1))
                vein_mask = min(1.0, mid_vein + sec_veins)
                rel = 0.22 * mid_vein + 0.07 * sec_veins

                px = (r_reach + cordate_back) * ca + lat * tx
                pz = (r_reach + cordate_back) * sa + lat * tz
                py = y_curve + cup_lift

                # Borde finamente glandular (tinte verde oliva/ambar integrado, sin capsulas flotantes)
                gland_edge = _ss(0.45, 0.50, au) * (0.5 + 0.5 * math.sin(14.0 * math.pi * v))
                ao_bract = 0.84 + 0.16 * _ss(0.0, 0.30, v)

                base_green = (0.36 + retic * 0.18, 0.60 + retic * 0.20, 0.24 + retic * 0.12)
                c_blade = _lerp_color(base_green, (0.64, 0.80, 0.44), vein_mask * 0.55)
                c_blade = _lerp_color(c_blade, (0.46, 0.58, 0.20), gland_edge * 0.55)
                c_top = _shade_rgb(c_blade, ao_bract)
                c_bot = _shade_rgb(_lerp_color(c_blade, (0.44, 0.66, 0.28), 0.25), ao_bract * 0.94)

                row_t.append(mb.v(px, py + 0.16 + rel * 0.35, pz, *c_top))
                row_b.append(mb.v(px, py - 0.16 - rel, pz, *c_bot))
            top_grid.append(row_t)
            bot_grid.append(row_b)

        for i in range(nu_b):
            for j in range(nv_b):
                mb.quad(top_grid[i][j], top_grid[i][j + 1], top_grid[i + 1][j], top_grid[i + 1][j + 1])
                mb.quad(bot_grid[i][j + 1], bot_grid[i][j], bot_grid[i + 1][j + 1], bot_grid[i + 1][j])
            mb.quad(bot_grid[i][0], top_grid[i][0], bot_grid[i + 1][0], top_grid[i + 1][0])
            mb.quad(top_grid[i][-1], bot_grid[i][-1], top_grid[i + 1][-1], bot_grid[i + 1][-1])

    # =========================================================================
    # 3. CÁLIZ: 5 SÉPALOS ANCHOS REFLEXOS PATENTES CON QUILLA Y CORNÍCULO (g Caliz_Sepalos)
    # =========================================================================
    mb.group("Caliz_Sepalos")
    mb.material("Mat_Caliz")

    nv_p, nu_p = 28, 14
    c_sepal_adaxial = (0.88, 0.12, 0.16) if is_vitifolia else (0.95, 0.97, 0.90)
    c_sepal_abaxial = (0.54, 0.74, 0.37)

    for k in range(5):
        base_ang = k * (2.0 * math.pi / 5.0)
        ca, sa = math.cos(base_ang), math.sin(base_ang)
        tx, tz = -sa, ca

        top_grid, bot_grid = [], []
        horn_base_pos = None

        for i in range(nv_p + 1):
            v = i / nv_p
            if v < 0.15:
                w_prof = 0.68 + 0.32 * math.sin((math.pi * 0.5) * (v / 0.15))
            elif v < 0.76:
                w_prof = 1.0 - 0.12 * ((v - 0.15) / 0.61)
            else:
                t_tip = (v - 0.76) / 0.24
                w_prof = 0.88 * math.sqrt(max(0.0, 1.0 - (t_tip ** 1.85)))
            w_loc = (w_sepal * 0.5) * w_prof

            # Postura en estrella abierta y suavemente reflexa (~36-42 grados bajo horizontal)
            if is_vitifolia:
                r_proj = 8.4 + l_sepal * (v ** 0.92) * 0.92
                y_prof = -0.2 + 1.8 * math.sin(math.pi * v * 0.55) - 6.8 * (v ** 1.65)
            else:
                r_proj = 9.2 + l_sepal * (0.85 * (v ** 0.90) - 0.04 * (v ** 2.2))
                y_prof = -0.1 + 1.8 * math.sin(math.pi * v * 0.48) - 24.0 * (v ** 1.38)

            row_t, row_b = [], []
            for j in range(nu_p + 1):
                u = (j / nu_p) - 0.5
                au = abs(u)
                lat = u * 2.0 * w_loc
                gutter = 1.25 * (u * u) * math.sin(math.pi * v)

                # Quilla dorsal prominente en el enves
                keel = 2.15 * math.sin(math.pi * (v ** 0.78)) * math.exp(-((au / 0.17) ** 2))
                thick = 0.72 * math.sin(math.pi * (v ** 0.75)) * (1.0 - 0.55 * au)
                vein_s = 0.05 * math.cos(u * 14.0) * math.sin(v * 2.5 * math.pi)

                px = r_proj * ca + lat * tx
                pz = r_proj * sa + lat * tz
                py_top = y_prof + gutter + vein_s
                py_bot = y_prof + gutter - thick - keel

                ao_base = 0.88 + 0.12 * _ss(0.0, 0.22, v)
                margin_tint = _ss(0.30, 0.50, au)
                c_top = _lerp_color(c_sepal_adaxial, (0.86, 0.93, 0.77), margin_tint * 0.50)
                c_top = _lerp_color(c_top, (0.82, 0.90, 0.72), (1.0 - _ss(0.0, 0.25, v)) * 0.35)
                row_t.append(mb.v(px, py_top, pz, *_shade_rgb(c_top, ao_base)))

                keel_blend = math.exp(-((au / 0.28) ** 2))
                c_bot = _lerp_color((0.84, 0.90, 0.76), c_sepal_abaxial, keel_blend * 0.92)
                row_b.append(mb.v(px, py_bot, pz, *_shade_rgb(c_bot, ao_base)))

                if abs(v - 0.87) < (0.5 / nv_p) and j == nu_p // 2:
                    horn_base_pos = (px, py_bot, pz)

            top_grid.append(row_t)
            bot_grid.append(row_b)

        for i in range(nv_p):
            for j in range(nu_p):
                mb.quad(top_grid[i][j], top_grid[i][j + 1], top_grid[i + 1][j], top_grid[i + 1][j + 1])
                mb.quad(bot_grid[i][j + 1], bot_grid[i][j], bot_grid[i + 1][j + 1], bot_grid[i + 1][j])
            mb.quad(bot_grid[i][0], top_grid[i][0], bot_grid[i + 1][0], top_grid[i + 1][0])
            mb.quad(top_grid[i][-1], bot_grid[i][-1], top_grid[i + 1][-1], bot_grid[i + 1][-1])

        # Corniculo dorsal subapical aristado (~5.2 mm)
        if horn_base_pos is not None:
            hx, hy, hz = horn_base_pos
            horn_pts = [
                (hx - 0.4 * ca, hy + 0.3, hz - 0.4 * sa),
                (hx + 1.5 * ca, hy - 1.1, hz + 1.5 * sa),
                (hx + 3.4 * ca, hy - 2.6, hz + 3.4 * sa),
                (hx + 4.9 * ca, hy - 3.9, hz + 4.9 * sa),
            ]
            horn_cols = [
                (0.56, 0.76, 0.38),
                (0.50, 0.72, 0.34),
                (0.46, 0.68, 0.31),
                (0.42, 0.62, 0.28),
            ]
            mb.add_tube(horn_pts, [0.82, 0.56, 0.28, 0.06], horn_cols, radial_segs=8, cap_end=True)

    # =========================================================================
    # 4. COROLA: 5 PÉTALOS CON MOTEADO PÚRPURA ORGÁNICO (g Corola_Petalos)
    # =========================================================================
    mb.group("Corola_Petalos")
    mb.material("Mat_CorolaLimbo")

    c_petal_base = (0.92, 0.14, 0.18) if is_vitifolia else (0.95, 0.96, 0.92)
    c_petal_spot = (0.48, 0.14, 0.42)

    nv_pet, nu_pet = 32, 16
    for k in range(5):
        base_ang = k * (2.0 * math.pi / 5.0) + (math.pi / 5.0)
        ca, sa = math.cos(base_ang), math.sin(base_ang)
        tx, tz = -sa, ca

        # Centros pseudoaleatorios deterministas para motas purpura organicas (sin rejilla)
        rng_p = random.Random(310 + k * 29)
        spots = []
        for _ in range(58):
            sv = rng_p.uniform(0.14, 0.90)
            su = rng_p.uniform(-0.44, 0.44)
            sr_v = rng_p.uniform(0.018, 0.036)
            sr_u = rng_p.uniform(0.032, 0.068)
            s_str = rng_p.uniform(0.45, 0.88)
            spots.append((sv, su, sr_v, sr_u, s_str))

        top_grid, bot_grid = [], []
        for i in range(nv_pet + 1):
            v = i / nv_pet
            if v < 0.16:
                w_prof = 0.62 + 0.38 * math.sin((math.pi * 0.5) * (v / 0.16))
            elif v < 0.78:
                w_prof = 1.0 - 0.08 * ((v - 0.16) / 0.62)
            else:
                t_tip = (v - 0.78) / 0.22
                w_prof = 0.92 * math.sqrt(max(0.0, 1.0 - (t_tip ** 1.9)))
            w_loc = (w_petal * 0.5) * w_prof

            if is_vitifolia:
                r_proj = 8.2 + l_petal * (v ** 0.92) * 0.92
                y_prof = 0.3 + 2.0 * math.sin(math.pi * v * 0.55) - 5.4 * (v ** 1.65)
            else:
                r_proj = 9.0 + l_petal * (0.87 * (v ** 0.90) - 0.03 * (v ** 2.1))
                y_prof = 0.2 + 2.0 * math.sin(math.pi * v * 0.50) - 20.5 * (v ** 1.38)

            row_t, row_b = [], []
            for j in range(nu_pet + 1):
                u = (j / nu_pet) - 0.5
                lat = u * 2.0 * w_loc
                gutter = 0.85 * (u * u) * math.sin(math.pi * v)
                thick = 0.32 * math.sin(math.pi * (v ** 0.8))

                px = r_proj * ca + lat * tx
                pz = r_proj * sa + lat * tz
                py_top = y_prof + gutter
                py_bot = y_prof + gutter - thick

                if is_vitifolia:
                    cp_top = c_petal_base
                    cp_bot = c_petal_base
                else:
                    spot_val = 0.0
                    for sv, su, sr_v, sr_u, s_str in spots:
                        dv = (v - sv) / sr_v
                        du = (u - su) / sr_u
                        d2 = dv * dv + du * du
                        if d2 < 2.2:
                            val = s_str * math.exp(-d2 * 1.35)
                            if val > spot_val:
                                spot_val = val

                    ao_p = 0.90 + 0.10 * _ss(0.0, 0.20, v)
                    green_wash = (1.0 - _ss(0.0, 0.40, v)) * 0.35 + _ss(0.32, 0.50, abs(u)) * 0.22
                    ivory_tinted = _lerp_color(c_petal_base, (0.88, 0.93, 0.82), green_wash)
                    cp_top = _shade_rgb(_lerp_color(ivory_tinted, c_petal_spot, min(0.82, spot_val)), ao_p)
                    # Enves blanco-verdoso dejando traslucir suavemente las motas
                    cp_bot = _shade_rgb(_lerp_color(ivory_tinted, c_petal_spot, min(0.32, spot_val * 0.38)), ao_p * 0.96)

                row_t.append(mb.v(px, py_top, pz, *cp_top))
                row_b.append(mb.v(px, py_bot, pz, *cp_bot))
            top_grid.append(row_t)
            bot_grid.append(row_b)

        for i in range(nv_pet):
            for j in range(nu_pet):
                mb.quad(top_grid[i][j], top_grid[i][j + 1], top_grid[i + 1][j], top_grid[i + 1][j + 1])
                mb.quad(bot_grid[i][j + 1], bot_grid[i][j], bot_grid[i + 1][j + 1], bot_grid[i + 1][j])
            mb.quad(bot_grid[i][0], top_grid[i][0], bot_grid[i + 1][0], top_grid[i + 1][0])
            mb.quad(top_grid[i][-1], bot_grid[i][-1], top_grid[i + 1][-1], bot_grid[i + 1][-1])

    # =========================================================================
    # 5. CORONA MULTISERIADA DENSA (4 SERIES, 250 FILAMENTOS, PUNTAS FLEXUOSAS) (g Corona_Filamentos_Radii)
    # =========================================================================
    mb.group("Corona_Filamentos_Radii")
    mb.material("Mat_CoronaVioleta")

    if is_vitifolia:
        corona_tiers = [
            {"count": 64, "r_base": 8.0, "y_base": 0.5, "len": 26.0, "lift": 16.0, "droop": 0.5, "r0": 0.52, "r1": 0.16, "ns": 18, "curl": 0.35},
            {"count": 56, "r_base": 7.2, "y_base": 0.9, "len": 21.0, "lift": 17.5, "droop": 0.3, "r0": 0.46, "r1": 0.14, "ns": 14, "curl": 0.25},
        ]
    else:
        corona_tiers = [
            # Serie 1: falda externa larga y carnosa con puntas blancas flexuosas
            {"count": 78, "r_base": 8.9, "y_base": 0.4, "len": 39.5, "lift": 6.2,  "droop": 3.4, "r0": 0.64, "r1": 0.19, "ns": 24, "curl": 2.35},
            # Serie 2: cojin superior denso superpuesto
            {"count": 72, "r_base": 8.3, "y_base": 1.0, "len": 36.2, "lift": 8.2,  "droop": 2.8, "r0": 0.58, "r1": 0.18, "ns": 22, "curl": 2.15},
            # Serie 3: transicion intermedia bandeada (elimina hueco en garganta)
            {"count": 54, "r_base": 7.6, "y_base": 0.8, "len": 16.0, "lift": 4.8,  "droop": 0.8, "r0": 0.48, "r1": 0.17, "ns": 10, "curl": 0.55},
            # Serie 4: collar interno-medio
            {"count": 46, "r_base": 7.0, "y_base": 0.5, "len": 8.5,  "lift": 3.2,  "droop": 0.3, "r0": 0.40, "r1": 0.16, "ns": 8,  "curl": 0.25},
        ]

    for w_idx, w_cfg in enumerate(corona_tiers):
        cnt = w_cfg["count"]
        ns_fil = w_cfg["ns"]
        rng_w = random.Random(500 + w_idx * 97)

        for i in range(cnt):
            ang_jit = rng_w.uniform(-0.012, 0.012)
            ang = i * (2.0 * math.pi / cnt) + (w_idx * math.pi / cnt) + ang_jit
            ca, sa = math.cos(ang), math.sin(ang)
            tx, tz = -sa, ca

            # Variacion organica unica por filamento (rompe simetria artificial)
            len_scale = rng_w.uniform(0.92, 1.09)
            lift_jit = rng_w.uniform(-1.1, 1.2)
            p1 = rng_w.uniform(0.0, 2.0 * math.pi)
            p2 = rng_w.uniform(0.0, 2.0 * math.pi)
            f1 = rng_w.uniform(2.6, 4.1)
            f2 = rng_w.uniform(4.8, 6.9)
            curl_dir = rng_w.choice([-1.0, 1.0]) * rng_w.uniform(0.70, 1.30)
            tip_bias_t = rng_w.uniform(-1.4, 1.4)
            tip_bias_y = rng_w.uniform(-1.6, 1.3)
            color_jit = rng_w.uniform(-1.0, 1.0)

            fil_len = w_cfg["len"] * len_scale
            f_pts, f_rad, f_col = [], [], []

            for j in range(ns_fil + 1):
                s = j / ns_fil
                r_dist = w_cfg["r_base"] + fil_len * (s ** 0.90)

                # Arco campanulado suave que abre hacia afuera y cae suavemente al borde
                y_arch = (
                    w_cfg["y_base"]
                    + (w_cfg["lift"] + lift_jit) * math.sin(math.pi * 0.58 * (s ** 0.72))
                    - w_cfg["droop"] * (s ** 2.15)
                )

                # Ondulacion organica asimetrica concentrada en las puntas blancas (s > 0.66)
                curl_env = _ss(0.60, 0.98, s)
                w_amp = w_cfg["curl"] * curl_env
                dy_curl = w_amp * (
                    0.58 * math.sin(f1 * math.pi * s + p1)
                    + 0.34 * math.cos(f2 * math.pi * s + p2)
                ) + tip_bias_y * (curl_env ** 1.7)
                dt_curl = w_amp * curl_dir * (
                    0.65 * math.cos(f1 * math.pi * s + p2)
                    + 0.35 * math.sin(f2 * math.pi * s + p1)
                ) + tip_bias_t * (curl_env ** 1.5)

                px = r_dist * ca + dt_curl * tx
                pz = r_dist * sa + dt_curl * tz
                py = y_arch + dy_curl

                rad = w_cfg["r0"] * ((1.0 - s) ** 0.62) + w_cfg["r1"] * s
                ao_base = 0.72 + 0.28 * _ss(0.0, 0.14, s)

                if is_vitifolia:
                    col = _shade_rgb(_corona_radii_color(s, True, phase=color_jit), ao_base)
                else:
                    # Las series cortas mapean el patron interior (borgoña -> blanco -> purpura)
                    s_color = s if w_idx < 2 else (s * (0.46 if w_idx == 2 else 0.32))
                    col = _ligularis_corona_color(s_color, phase=color_jit, ao_base=ao_base)

                f_pts.append((px, py, pz))
                f_rad.append(rad)
                f_col.append(col)

            mb.add_tube(f_pts, f_rad, f_col, radial_segs=5, cap_start=False, cap_end=True)

    # =========================================================================
    # 6. CORONA INTERNA: PALI Y ANILLO PUNTUADO DE LA GARGANTA (g Corona_Interna_Pali)
    # =========================================================================
    mb.group("Corona_Interna_Pali")
    mb.material("Mat_CorolaGarganta")

    pali_whorls = [
        {"count": 50, "r_base": 6.4, "y_base": 0.4, "height": 3.9, "tilt": 0.45, "tip_dark": False},
        {"count": 44, "r_base": 5.7, "y_base": 0.2, "height": 2.9, "tilt": 0.10, "tip_dark": False},
        # Anillo interno fino de papilas con puntas purpura oscuras (visible en vista cenital)
        {"count": 40, "r_base": 4.9, "y_base": 0.1, "height": 1.6, "tilt": -0.18, "tip_dark": True},
    ]

    for p_idx, p_cfg in enumerate(pali_whorls):
        cnt = p_cfg["count"]
        for i in range(cnt):
            ang = i * (2.0 * math.pi / cnt) + (p_idx * 0.08)
            ca, sa = math.cos(ang), math.sin(ang)

            p_pts, p_rad, p_col = [], [], []
            steps_p = 6
            for j in range(steps_p + 1):
                s = j / steps_p
                r_curr = p_cfg["r_base"] + p_cfg["tilt"] * (s ** 1.3)
                y_curr = p_cfg["y_base"] + p_cfg["height"] * s

                if s < 0.70:
                    rad = 0.25 - 0.05 * (s / 0.70)
                else:
                    t_cap = (s - 0.70) / 0.30
                    rad = 0.20 + 0.14 * math.sin(t_cap * math.pi * 0.85)

                if p_cfg["tip_dark"]:
                    col = _lerp_color((0.90, 0.93, 0.80), (0.28, 0.03, 0.18), _ss(0.55, 0.90, s))
                else:
                    col = (0.30, 0.03, 0.18) if s < 0.72 else _lerp_color((0.30, 0.03, 0.18), (0.95, 0.93, 0.96), (s - 0.72) / 0.28)

                p_pts.append((r_curr * ca, y_curr, r_curr * sa))
                p_rad.append(rad)
                p_col.append(col)

            mb.add_tube(p_pts, p_rad, p_col, radial_segs=5, cap_start=False, cap_end=True)

    # =========================================================================
    # 7. COLUMNA AXIAL: ANDROGINÓFORO ANCLADO AL HIPANTO (g Columna_Androginoforo)
    # =========================================================================
    mb.group("Columna_Androginoforo")
    mb.material("Mat_Filamento")

    y_col_bot = -8.6 if not is_vitifolia else -6.8
    h_androg = 11.2
    n_col, s_col = 24, 22
    rng_col = random.Random(701)
    col_spots = [(rng_col.uniform(0.35, 0.96), rng_col.uniform(0.0, 2.0 * math.pi), rng_col.uniform(0.03, 0.055)) for _ in range(32)]

    col_rings = []
    for i in range(n_col + 1):
        t = i / n_col
        y_c = y_col_bot + t * (h_androg - y_col_bot)
        # Dilatacion basal (troclea) cerca de la camara nectarifera
        trochlea = 0.52 * math.exp(-(((t - 0.22) / 0.08) ** 2))
        r_c = 1.85 + 0.55 * math.exp(-t * 6.0) + trochlea + 0.30 * math.exp(-(1.0 - t) * 8.0)
        ring = []
        for s in range(s_col):
            ang = s * (2.0 * math.pi / s_col)
            sp_hit = 0.0
            for st, sa_c, sr in col_spots:
                da = math.atan2(math.sin(ang - sa_c), math.cos(ang - sa_c))
                d2 = ((t - st) / sr) ** 2 + (da / 0.36) ** 2
                if d2 < 2.2:
                    sp_hit = max(sp_hit, math.exp(-d2 * 1.4))
            base_c = _lerp_color((0.84, 0.90, 0.72), (0.90, 0.95, 0.80), t)
            col = _lerp_color(base_c, (0.48, 0.14, 0.40), sp_hit * 0.65)
            ring.append(mb.v(r_c * math.cos(ang), y_c, r_c * math.sin(ang), *col))
        col_rings.append(ring)

    for i in range(n_col):
        for s in range(s_col):
            sn = (s + 1) % s_col
            mb.quad(col_rings[i][s], col_rings[i][sn], col_rings[i + 1][s], col_rings[i + 1][sn])

    # =========================================================================
    # 8. ANDROCEO: 5 ESTAMBRES Y ANTERAS BILOCULARES PÉNDULAS (g Androceo_Estambres)
    # =========================================================================
    mb.group("Androceo_Estambres")
    mb.material("Mat_Antera")

    ant_len = float(androceo.get("antera_longitud_mm", 7.2))
    y_stamen_origin = h_androg - 0.35

    for k in range(5):
        a_st = k * (2.0 * math.pi / 5.0) + (math.pi / 10.0)
        ca, sa = math.cos(a_st), math.sin(a_st)
        tx, tz = -sa, ca

        rng_f = random.Random(810 + k * 17)
        fil_spots = [(rng_f.uniform(0.15, 0.92), rng_f.uniform(-0.42, 0.42)) for _ in range(16)]

        nf_steps, nf_w = 16, 6
        f_top, f_bot = [], []
        tip_pos = None

        for i in range(nf_steps + 1):
            t = i / nf_steps
            r_f = 1.75 + 9.4 * (t ** 0.90)
            y_f = y_stamen_origin + 1.65 * math.sin(math.pi * t * 0.62) - 2.4 * (t ** 1.85)
            w_ribbon = 0.98 * (1.0 - 0.32 * t)
            th_ribbon = 0.28 * (1.0 - 0.20 * t)

            if i == nf_steps:
                tip_pos = (r_f * ca, y_f, r_f * sa)

            rt_row, rb_row = [], []
            for j in range(nf_w + 1):
                u = (j / nf_w) - 0.5
                lat = u * 2.0 * w_ribbon
                px = r_f * ca + lat * tx
                pz = r_f * sa + lat * tz

                s_val = 0.0
                for st_f, su_f in fil_spots:
                    d2 = ((t - st_f) / 0.06) ** 2 + ((u - su_f) / 0.20) ** 2
                    if d2 < 2.2:
                        s_val = max(s_val, math.exp(-d2 * 1.4))

                c_top = _lerp_color((0.83, 0.92, 0.64), (0.48, 0.14, 0.42), s_val * 0.68)
                c_bot = (0.78, 0.89, 0.58)
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

        # Antera oblonga bilocular versatil (inclinada ~30° hacia la corona con surco longitudinal y textura polinica)
        ax, ay, az = tip_pos
        ant_w = 3.25
        ant_th = 1.18
        tilt_ant = 0.52  # ~30 grados inclinada hacia abajo/afuera
        ct_a, st_a = math.cos(tilt_ant), math.sin(tilt_ant)

        na_u, na_v = 18, 18
        ant_rings = []
        for i in range(na_u + 1):
            u = (i / na_u) - 0.5
            u_norm = u * 2.0
            env_l = math.sqrt(max(0.0, 1.0 - 0.82 * (u_norm * u_norm)))
            s_along = u * ant_len
            arch_local = -0.35 * (u_norm * u_norm)

            ring = []
            for j in range(na_v):
                ang = j * (2.0 * math.pi / na_v)
                ca_a, sa_a = math.cos(ang), math.sin(ang)

                # Dos tecas prominentes separadas por un surco longitudinal central nitido
                theca_groove = 1.0 - 0.46 * math.exp(-((ca_a / 0.24) ** 2))
                # Textura granulosa sutil de granos de polen
                pollen_gran = 1.0 + 0.035 * _lowfreq(u * 24.0, ang * 5.0, seed=float(k + 5))

                loc_r = (ant_w * 0.5) * env_l * ca_a * pollen_gran
                loc_y = (ant_th * env_l * sa_a * theca_groove * pollen_gran) + arch_local

                # Rotacion versatil alrededor del eje tangencial
                rot_r = loc_r * ct_a - loc_y * st_a
                rot_y = loc_r * st_a + loc_y * ct_a

                px = ax + s_along * tx + rot_r * ca
                pz = az + s_along * tz + rot_r * sa
                py = (ay - 0.65) + rot_y

                groove_ao = 0.78 + 0.22 * theca_groove
                grain_tint = 0.94 + 0.08 * _lowfreq(u * 32.0, ang * 8.0, seed=float(k + 12))
                if sa_a >= 0.15:
                    # Conectivo dorsal amarillo-verdoso suave
                    col_a = _lerp_color((0.88, 0.84, 0.28), (0.72, 0.82, 0.34), sa_a)
                else:
                    # Tecas polinicas amarillo-dorado intenso
                    col_a = _lerp_color((0.96, 0.83, 0.16), (0.98, 0.74, 0.08), max(0.0, -sa_a))
                ring.append(mb.v(px, py, pz, *_shade_rgb(col_a, groove_ao * grain_tint)))
            ant_rings.append(ring)

        for i in range(na_u):
            for j in range(na_v):
                jn = (j + 1) % na_v
                mb.quad(ant_rings[i][j], ant_rings[i][jn], ant_rings[i + 1][j], ant_rings[i + 1][jn])

        c_left = mb.v(ax - 0.5 * ant_len * tx, ay - 0.92, az - 0.5 * ant_len * tz, 0.92, 0.80, 0.18)
        c_right = mb.v(ax + 0.5 * ant_len * tx, ay - 0.92, az + 0.5 * ant_len * tz, 0.92, 0.80, 0.18)
        for j in range(na_v):
            jn = (j + 1) % na_v
            mb.f(c_left, ant_rings[0][jn], ant_rings[0][j])
            mb.f(c_right, ant_rings[-1][j], ant_rings[-1][jn])

    # =========================================================================
    # 9. GINECEO EXTERNO: OVARIO SÚPERO CON PERICARPIO CARNOSO DOBLE (g Gineceo_Ovario_Supero)
    # =========================================================================
    mb.group("Gineceo_Ovario_Supero")
    mb.material("Mat_Ovario")

    ov_base_y = h_androg - 0.2
    ov_h = 7.4
    ov_rx = 3.05
    ov_wall = 1.02  # Espesor real del pericarpio (~1.0 mm) visible en Corte Sagital
    no_u, no_v = 20, 24

    # Capa externa verde manzana brillante
    ov_out_rings = []
    for i in range(no_u + 1):
        v = i / no_u
        theta_v = v * math.pi
        y_ov = ov_base_y + ov_h * (0.5 - 0.5 * math.cos(theta_v))
        r_ov = ov_rx * math.sin(theta_v)
        if i == 0 or i == no_u:
            r_ov = 0.34

        ring = []
        for j in range(no_v):
            ang = j * (2.0 * math.pi / no_v)
            carpel_flute = 1.0 + 0.032 * math.cos(3.0 * ang)
            gloss_shade = 0.92 + 0.06 * math.cos(3.0 * ang) + 0.06 * math.sin(theta_v)
            c_ov = _shade_rgb((0.56, 0.80, 0.30), gloss_shade)
            ring.append(mb.v(r_ov * carpel_flute * math.cos(ang), y_ov, r_ov * carpel_flute * math.sin(ang), *c_ov))
        ov_out_rings.append(ring)

    for i in range(no_u):
        for j in range(no_v):
            jn = (j + 1) % no_v
            mb.quad(ov_out_rings[i][j], ov_out_rings[i][jn], ov_out_rings[i + 1][j], ov_out_rings[i + 1][jn])

    top_cap_ov = mb.v(0.0, ov_base_y + ov_h, 0.0, 0.56, 0.80, 0.30)
    bot_cap_ov = mb.v(0.0, ov_base_y, 0.0, 0.50, 0.74, 0.26)
    for j in range(no_v):
        jn = (j + 1) % no_v
        mb.f(top_cap_ov, ov_out_rings[-1][j], ov_out_rings[-1][jn])
        mb.f(bot_cap_ov, ov_out_rings[0][jn], ov_out_rings[0][j])

    # Capa interna de la cavidad unilocular (pericarpio crema-verdoso, normales hacia adentro)
    ov_in_h = ov_h - 1.85
    ov_in_base = ov_base_y + 0.92
    ov_in_rx = ov_rx - ov_wall
    ov_in_rings = []
    for i in range(14 + 1):
        v = i / 14.0
        theta_v = v * math.pi
        y_in = ov_in_base + ov_in_h * (0.5 - 0.5 * math.cos(theta_v))
        r_in = max(0.18, ov_in_rx * math.sin(theta_v))
        ring = []
        for j in range(no_v):
            ang = j * (2.0 * math.pi / no_v)
            shade_in = 0.92 + 0.08 * math.sin(theta_v)
            c_in = _shade_rgb((0.88, 0.93, 0.78), shade_in)
            ring.append(mb.v(r_in * math.cos(ang), y_in, r_in * math.sin(ang), *c_in))
        ov_in_rings.append(ring)

    for i in range(len(ov_in_rings) - 1):
        for j in range(no_v):
            jn = (j + 1) % no_v
            # Winding invertido para que la cavidad mire hacia el interior
            mb.quad(ov_in_rings[i][jn], ov_in_rings[i][j], ov_in_rings[i + 1][jn], ov_in_rings[i + 1][j])

    # =========================================================================
    # 10. 3 ESTILOS MACULADOS (SIN ANILLOS) Y ESTIGMAS RENIFORMES GRANDES (g Gineceo_Estilos_Estigmas)
    # =========================================================================
    mb.group("Gineceo_Estilos_Estigmas")
    mb.material("Mat_Estilo")

    y_style_origin = ov_base_y + ov_h - 0.30
    n_st = 20
    s_st = 12

    for k in range(3):
        a_sy = k * (2.0 * math.pi / 3.0) + (math.pi / 6.0)
        ca, sa = math.cos(a_sy), math.sin(a_sy)
        tx, tz = -sa, ca

        rng_sy = random.Random(920 + k * 37)
        sy_spots = [
            (rng_sy.uniform(0.08, 0.92), rng_sy.uniform(0.0, 2.0 * math.pi), rng_sy.uniform(0.032, 0.058))
            for _ in range(36)
        ]

        # Construir el estilo con anillos individuales para moteado purpura 3D (sin anillos de cebra)
        st_centers = []
        st_rads = []
        for i in range(n_st + 1):
            t = i / n_st
            r_s = 0.42 + 10.6 * (t ** 0.88)
            y_s = y_style_origin + 3.4 * math.sin(math.pi * (t ** 0.70)) - 4.8 * (t ** 1.95)
            rad_s = 0.56 + 0.66 * (t ** 1.25)
            st_centers.append((r_s * ca, y_s, r_s * sa))
            st_rads.append(rad_s)

        st_rings = []
        for i in range(n_st + 1):
            t = i / n_st
            px0, py0, pz0 = st_centers[i]
            if i < n_st:
                dx = st_centers[i + 1][0] - px0
                dy = st_centers[i + 1][1] - py0
                dz = st_centers[i + 1][2] - pz0
            else:
                dx = px0 - st_centers[i - 1][0]
                dy = py0 - st_centers[i - 1][1]
                dz = pz0 - st_centers[i - 1][2]
            dl = math.sqrt(dx * dx + dy * dy + dz * dz) or 1.0
            ux, uy, uz = dx / dl, dy / dl, dz / dl

            # Normal binormal estable respecto al vector tangencial (tx, 0, tz)
            nx = uy * tz - uz * 0.0
            ny = uz * tx - ux * tz
            nz = ux * 0.0 - uy * tx
            nl = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
            nx, ny, nz = nx / nl, ny / nl, nz / nl

            rad_s = st_rads[i]
            ring = []
            for j in range(s_st):
                ang = j * (2.0 * math.pi / s_st)
                c_a, s_a = math.cos(ang), math.sin(ang)
                vx_s = px0 + rad_s * (c_a * nx + s_a * tx)
                vy_s = py0 + rad_s * (c_a * ny)
                vz_s = pz0 + rad_s * (c_a * nz + s_a * tz)

                sp_val = 0.0
                for st_p, sa_p, sr_p in sy_spots:
                    da = math.atan2(math.sin(ang - sa_p), math.cos(ang - sa_p))
                    d2 = ((t - st_p) / sr_p) ** 2 + (da / 0.42) ** 2
                    if d2 < 2.2:
                        sp_val = max(sp_val, math.exp(-d2 * 1.45))

                # Fondo verde-lavanda translucido con pecas purpura finas
                base_st = _lerp_color((0.88, 0.93, 0.82), (0.86, 0.78, 0.88), _ss(0.15, 0.85, t) * 0.55)
                col_s = _lerp_color(base_st, (0.46, 0.12, 0.40), sp_val * 0.72)
                ring.append(mb.v(vx_s, vy_s, vz_s, *col_s))
            st_rings.append(ring)

        for i in range(n_st):
            for j in range(s_st):
                jn = (j + 1) % s_st
                mb.quad(st_rings[i][j], st_rings[i][jn], st_rings[i + 1][j], st_rings[i + 1][jn])

        # Estigma reniforme-capitado grande y papiloso (~3.4 mm ancho) enfrentado a las anteras
        sx, sy, sz = st_centers[-1]
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

                lobe_w = 2.35 * sin_p * ct
                indent = 0.52 * (1.0 - ct * ct) * max(0.0, st)
                lobe_r = (1.68 * sin_p * st) - indent
                lobe_h = 1.25 * cos_p * (1.0 + 0.16 * (ct * ct))

                pap = 1.0 + 0.045 * math.sin(7.0 * phi) * math.cos(9.0 * theta)

                tilt_a = 0.68
                r_rot = lobe_r * math.cos(tilt_a) - lobe_h * math.sin(tilt_a)
                y_rot = lobe_r * math.sin(tilt_a) + lobe_h * math.cos(tilt_a)

                px = sx + 0.45 * ca + (lobe_w * pap) * tx + (r_rot * pap) * ca
                pz = sz + 0.45 * sa + (lobe_w * pap) * tz + (r_rot * pap) * sa
                py = sy - 0.25 + (y_rot * pap)

                shade_st = 0.88 + 0.12 * cos_p + 0.05 * math.sin(7.0 * phi) * math.cos(9.0 * theta)
                c_stig = _shade_rgb((0.68, 0.84, 0.40), shade_st)
                ring.append(mb.v(px, py, pz, *c_stig))
            stig_rings.append(ring)

        for i in range(ns_u):
            for j in range(ns_v):
                jn = (j + 1) % ns_v
                mb.quad(stig_rings[i][j], stig_rings[i][jn], stig_rings[i + 1][j], stig_rings[i + 1][jn])

        p_top = mb.v(
            sx + 0.45 * ca - 1.25 * math.sin(0.68) * ca,
            sy - 0.25 + 1.25 * math.cos(0.68),
            sz + 0.45 * sa - 1.25 * math.sin(0.68) * sa,
            0.70, 0.86, 0.42,
        )
        p_bot = mb.v(
            sx + 0.45 * ca + 1.25 * math.sin(0.68) * ca,
            sy - 0.25 - 1.25 * math.cos(0.68),
            sz + 0.45 * sa + 1.25 * math.sin(0.68) * sa,
            0.62, 0.78, 0.36,
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

    r_inner_max = ov_in_rx * 0.94
    for p_idx in range(3):
        p_ang = p_idx * (2.0 * math.pi / 3.0)
        ca, sa = math.cos(p_ang), math.sin(p_ang)
        tx, tz = -sa, ca

        cord_pts, cord_r, cord_c = [], [], []
        n_cord = 14
        for i in range(n_cord + 1):
            v = 0.12 + 0.76 * (i / n_cord)
            theta_v = v * math.pi
            y_p = ov_in_base + ov_in_h * (0.5 - 0.5 * math.cos(theta_v))
            r_p = r_inner_max * math.sin(theta_v)
            cord_pts.append((r_p * ca, y_p, r_p * sa))
            cord_r.append(0.28 * math.sin(theta_v))
            cord_c.append((0.88, 0.87, 0.70))

        mb.add_tube(cord_pts, cord_r, cord_c, radial_segs=8, cap_start=True, cap_end=True)

        n_ovules = 7
        for ov_i in range(n_ovules):
            v = 0.16 + 0.68 * (ov_i / (n_ovules - 1))
            theta_v = v * math.pi
            y_p = ov_in_base + ov_in_h * (0.5 - 0.5 * math.cos(theta_v))
            r_wall = r_inner_max * math.sin(theta_v)

            for row_side in [-1.0, 1.0]:
                wx = r_wall * ca + (row_side * 0.22) * tx
                wz = r_wall * sa + (row_side * 0.22) * tz

                ox = (r_wall - 0.56) * ca + (row_side * 0.42) * tx
                oz = (r_wall - 0.56) * sa + (row_side * 0.42) * tz
                oy = y_p + (0.10 * row_side)

                fun_pts = [(wx, y_p, wz), ((wx + ox) * 0.5, y_p + 0.12, (wz + oz) * 0.5), (ox, oy, oz)]
                mb.add_tube(fun_pts, [0.11, 0.09, 0.12], [(0.88, 0.87, 0.70)] * 3, radial_segs=6)

                ov_u_pts = [
                    (ox, oy - 0.44, oz),
                    (ox, oy - 0.22, oz),
                    (ox, oy, oz),
                    (ox, oy + 0.22, oz),
                    (ox, oy + 0.44, oz),
                ]
                ov_u_rad = [0.09, 0.34, 0.45, 0.34, 0.09]
                ov_u_col = [(0.97, 0.95, 0.86)] * 5
                mb.add_tube(ov_u_pts, ov_u_rad, ov_u_col, radial_segs=8, cap_start=True, cap_end=True)

    # =========================================================================
    # 12. ANATOMÍA INTERNA: CÁMARA NECTARÍFERA PROFUNDA, ANNULUS, LIMEN Y OPÉRCULO (g Camara_Nectarifera_Interna)
    # =========================================================================
    mb.group("Camara_Nectarifera_Interna")
    mb.material("Mat_CorolaGarganta")

    s_nec = 32
    # Annulus / Torus nectarifero bien definido en el fondo de la camara (y ~ -6.8)
    r_torus_maj = 5.05 if not is_vitifolia else 3.9
    r_torus_min = 0.70
    y_torus = -6.8 if not is_vitifolia else -4.6
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
            sh = 0.92 + 0.08 * sm
            ring.append(mb.v(r_ring * math.cos(ang), y_ring, r_ring * math.sin(ang), *_shade_rgb((0.82, 0.90, 0.56), sh)))
        torus_rings.append(ring)

    for i in range(nt_minor):
        inext = (i + 1) % nt_minor
        for s in range(s_nec):
            sn = (s + 1) % s_nec
            mb.quad(torus_rings[i][s], torus_rings[i][sn], torus_rings[inext][s], torus_rings[inext][sn])

    # Limen: collar acopado alrededor de la base del androginoforo
    y_lim_off = 0.0 if not is_vitifolia else 2.2
    limen_prof = [
        (2.15, -7.2 + y_lim_off, (0.84, 0.89, 0.72)),
        (2.85, -6.2 + y_lim_off, (0.87, 0.91, 0.76)),
        (3.45, -3.6 + y_lim_off, (0.90, 0.93, 0.82)),
        (3.20, -2.0 + y_lim_off, (0.76, 0.56, 0.80)),
        (2.70, -3.4 + y_lim_off, (0.85, 0.88, 0.76)),
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

    # Operculum membranoso plicado (32 pliegues radiales cubriendo la camara nectarifera)
    op_prof = [
        (7.70, -0.35, (0.86, 0.84, 0.86)),
        (6.25, -1.55, (0.84, 0.74, 0.86)),
        (4.65, -2.15, (0.88, 0.82, 0.90)),
        (3.85, -1.15, (0.92, 0.93, 0.86)),
        (4.05, -0.25, (0.94, 0.95, 0.90)),
    ]
    op_rings = []
    for idx_op, (r_o, y_o, col_o) in enumerate(op_prof):
        ring = []
        for s in range(s_nec):
            ang = s * (2.0 * math.pi / s_nec)
            plic = 0.22 * math.sin(16.0 * ang) if idx_op >= 1 else 0.0
            sp_op = math.sin(12.0 * ang + idx_op * 1.7)
            c_op = _lerp_color(col_o, (0.44, 0.10, 0.36), 0.45 if (idx_op >= 3 and sp_op > 0.42) else 0.0)
            ring.append(mb.v((r_o + plic) * math.cos(ang), y_o + plic * 0.45, (r_o + plic) * math.sin(ang), *c_op))
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

    c_vasc = (0.84, 0.89, 0.70)
    vasc_trunk = [
        (0.0, -34.5, -2.4),
        (0.0, -24.0, -1.3),
        (0.0, -14.0, -0.3),
        (0.0, -8.8, 0.0),
        (0.0, -2.0, 0.0),
        (0.0, 5.0, 0.0),
        (0.0, h_androg - 0.2, 0.0),
    ]
    mb.add_tube(vasc_trunk, [0.52, 0.56, 0.62, 0.70, 0.62, 0.60, 0.66], [c_vasc] * 7, radial_segs=10, cap_start=True, cap_end=True)

    for k in range(5):
        a_st = k * (2.0 * math.pi / 5.0) + (math.pi / 10.0)
        ca, sa = math.cos(a_st), math.sin(a_st)
        st_trace = [
            (0.0, h_androg - 0.9, 0.0),
            (1.3 * ca, h_androg - 0.3, 1.3 * sa),
            (3.2 * ca, h_androg + 0.3, 3.2 * sa),
        ]
        mb.add_tube(st_trace, [0.24, 0.20, 0.14], [c_vasc] * 3, radial_segs=6, cap_end=True)

    for p_idx in range(3):
        p_ang = p_idx * (2.0 * math.pi / 3.0)
        ca, sa = math.cos(p_ang), math.sin(p_ang)
        pl_trace = [
            (0.0, h_androg - 0.2, 0.0),
            (1.0 * ca, ov_base_y + 0.8, 1.0 * sa),
            (2.25 * ca, ov_base_y + ov_h * 0.5, 2.25 * sa),
            (0.85 * ca, ov_base_y + ov_h - 0.4, 0.85 * sa),
        ]
        mb.add_tube(pl_trace, [0.22, 0.18, 0.16, 0.15], [c_vasc] * 4, radial_segs=6, cap_end=True)

    return mb.build_obj()
