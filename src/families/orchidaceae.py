import math
import numpy as np


def _smoothstep(e0, e1, x):
    t = np.clip((x - e0) / max(1e-6, (e1 - e0)), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _add_closed_tube(curve_pts, radii, colors_ring, n_slices, vertices, colors, faces,
                     cap_start=True, cap_end=True, rx_scale=1.0, ry_scale=1.0,
                     ventral_flatten=1.0):
    """Genera un tubo parametrico hermetico cerrado en ambos extremos."""
    n_rings = len(curve_pts)
    base_idx = len(vertices)
    theta_vals = np.linspace(0.0, 2.0 * np.pi, n_slices, endpoint=False)

    for i in range(n_rings):
        p = curve_pts[i]
        if i == 0:
            tang = curve_pts[1] - p
        elif i == n_rings - 1:
            tang = p - curve_pts[i - 1]
        else:
            tang = curve_pts[i + 1] - curve_pts[i - 1]
        norm_t = np.linalg.norm(tang)
        tang = tang / (norm_t if norm_t > 1e-6 else 1.0)

        ref_x = np.array([1.0, 0.0, 0.0])
        if abs(np.dot(tang, ref_x)) > 0.92:
            ref_x = np.array([0.0, 1.0, 0.0])
        n2 = np.cross(tang, ref_x)
        n2 /= max(1e-6, np.linalg.norm(n2))
        n1 = np.cross(n2, tang)
        n1 /= max(1e-6, np.linalg.norm(n1))

        for j, th in enumerate(theta_vals):
            r = radii[i, j] if np.ndim(radii) == 2 else radii[i]
            sy = ry_scale * (ventral_flatten if math.sin(th) < 0.0 else 1.0)
            pt = p + r * (rx_scale * math.cos(th) * n1 + sy * math.sin(th) * n2)
            vertices.append(pt.tolist())
            c = colors_ring[i, j] if np.ndim(colors_ring) == 3 else colors_ring[i]
            colors.append(np.clip(c, 0.0, 1.0).tolist())

    for i in range(n_rings - 1):
        for j in range(n_slices):
            j_next = (j + 1) % n_slices
            p1 = base_idx + i * n_slices + j + 1
            p2 = base_idx + i * n_slices + j_next + 1
            p3 = base_idx + (i + 1) * n_slices + j_next + 1
            p4 = base_idx + (i + 1) * n_slices + j + 1
            faces.append((p1, p2, p3))
            faces.append((p1, p3, p4))

    if cap_start:
        c0 = colors_ring[0, 0] if np.ndim(colors_ring) == 3 else colors_ring[0]
        vertices.append(curve_pts[0].tolist())
        colors.append(np.clip(c0, 0.0, 1.0).tolist())
        v_center_start = len(vertices)
        for j in range(n_slices):
            j_next = (j + 1) % n_slices
            p1 = base_idx + j + 1
            p2 = base_idx + j_next + 1
            faces.append((v_center_start, p2, p1))

    if cap_end:
        ce = colors_ring[-1, 0] if np.ndim(colors_ring) == 3 else colors_ring[-1]
        vertices.append(curve_pts[-1].tolist())
        colors.append(np.clip(ce, 0.0, 1.0).tolist())
        v_center_end = len(vertices)
        ring_off = base_idx + (n_rings - 1) * n_slices
        for j in range(n_slices):
            j_next = (j + 1) % n_slices
            p1 = ring_off + j + 1
            p2 = ring_off + j_next + 1
            faces.append((v_center_end, p1, p2))


def _add_ellipsoid(center, radii_xyz, color_rgb, n_lat, n_lon, vertices, colors, faces):
    """Genera un elipsoide 3D solido cerrado."""
    base_idx = len(vertices)
    cx, cy, cz = center
    rx, ry, rz = radii_xyz
    c_arr = np.clip(color_rgb, 0.0, 1.0).tolist()

    for i in range(n_lat + 1):
        phi = math.pi * i / n_lat
        sp, cp = math.sin(phi), math.cos(phi)
        for j in range(n_lon):
            th = 2.0 * math.pi * j / n_lon
            px = cx + rx * sp * math.cos(th)
            py = cy + ry * cp
            pz = cz + rz * sp * math.sin(th)
            vertices.append([px, py, pz])
            colors.append(c_arr)

    for i in range(n_lat):
        for j in range(n_lon):
            j_next = (j + 1) % n_lon
            p1 = base_idx + i * n_lon + j + 1
            p2 = base_idx + i * n_lon + j_next + 1
            p3 = base_idx + (i + 1) * n_lon + j_next + 1
            p4 = base_idx + (i + 1) * n_lon + j + 1
            faces.append((p1, p2, p3))
            faces.append((p1, p3, p4))


def _add_double_shell_grid(pts_outer, pts_inner, cols_outer, cols_inner,
                           i_start, i_end, vertices, colors, faces,
                           cap_v_start=False, cap_v_end=False):
    """Construye una lamina solida de dos caras (abaxial/adaxial) con bordes cosidos."""
    n_v_sub = i_end - i_start
    n_u = pts_outer.shape[1]
    base_out = len(vertices)

    for i in range(i_start, i_end):
        for j in range(n_u):
            vertices.append(pts_outer[i, j].tolist())
            colors.append(np.clip(cols_outer[i, j], 0.0, 1.0).tolist())

    base_in = len(vertices)
    for i in range(i_start, i_end):
        for j in range(n_u):
            vertices.append(pts_inner[i, j].tolist())
            colors.append(np.clip(cols_inner[i, j], 0.0, 1.0).tolist())

    # Superficie externa (abaxial)
    for i in range(n_v_sub - 1):
        for j in range(n_u - 1):
            p1 = base_out + i * n_u + j + 1
            p2 = base_out + i * n_u + (j + 1) + 1
            p3 = base_out + (i + 1) * n_u + (j + 1) + 1
            p4 = base_out + (i + 1) * n_u + j + 1
            faces.append((p1, p2, p3))
            faces.append((p1, p3, p4))

    # Superficie interna (adaxial, orientacion invertida)
    for i in range(n_v_sub - 1):
        for j in range(n_u - 1):
            p1 = base_in + i * n_u + j + 1
            p2 = base_in + i * n_u + (j + 1) + 1
            p3 = base_in + (i + 1) * n_u + (j + 1) + 1
            p4 = base_in + (i + 1) * n_u + j + 1
            faces.append((p1, p3, p2))
            faces.append((p1, p4, p3))

    # Costura de bordes laterales (j = 0 y j = n_u - 1)
    for i in range(n_v_sub - 1):
        o1 = base_out + i * n_u + 1
        o2 = base_out + (i + 1) * n_u + 1
        i1 = base_in + i * n_u + 1
        i2 = base_in + (i + 1) * n_u + 1
        faces.append((o1, o2, i2))
        faces.append((o1, i2, i1))

        o1 = base_out + i * n_u + (n_u - 1) + 1
        o2 = base_out + (i + 1) * n_u + (n_u - 1) + 1
        i1 = base_in + i * n_u + (n_u - 1) + 1
        i2 = base_in + (i + 1) * n_u + (n_u - 1) + 1
        faces.append((o1, i2, o2))
        faces.append((o1, i1, i2))

    # Costura de borde basal (i = 0)
    if cap_v_start:
        for j in range(n_u - 1):
            o1 = base_out + j + 1
            o2 = base_out + (j + 1) + 1
            i1 = base_in + j + 1
            i2 = base_in + (j + 1) + 1
            faces.append((o1, i2, o2))
            faces.append((o1, i1, i2))

    # Costura de borde distal (i = n_v_sub - 1)
    if cap_v_end:
        last_off = (n_v_sub - 1) * n_u
        for j in range(n_u - 1):
            o1 = base_out + last_off + j + 1
            o2 = base_out + last_off + (j + 1) + 1
            i1 = base_in + last_off + j + 1
            i2 = base_in + last_off + (j + 1) + 1
            faces.append((o1, o2, i2))
            faces.append((o1, i2, i1))


def build_orchidaceae_flower(cfg):
    """
    Generador morfometrico v2.1 para Cattleya trianae (COL-ATL-006):
    - Sepalos oblongo-lanceolados con apice obtuso-subagudo y union nodal continua.
    - Petalos laterales ovado-rombicos anchos (101.4 x 66.1 mm) con ondulacion organica suave.
    - Labelo trilobulado convoluto (90.0 x 70.1 mm) hermetico de doble pared: exterior lila
      pastel envolviendo la columna, garganta dorada estriada, macula carmesi y borde rizado.
    - Ginostemio (33.0 x 10.7 mm), 4 polinios cerosos en 2 pares y cavidad estigmatica.
    - Ovario pedicelado infero (72.0 mm) con cuniculus nectarifero y placentacion parietal
      centrados en x = 0 para corte sagital y Rayos X simetricos.
    """
    NL = chr(10)
    perianto = cfg.get("perianto") or {}
    caliz = perianto.get("caliz") or {}
    corola = perianto.get("corola") or {}
    androceo = cfg.get("androceo") or {}
    gineceo = cfg.get("gineceo") or {}

    sep_d_len = float(caliz.get("sepalo_dorsal_largo_mm", 96.7))
    sep_d_wid = float(caliz.get("sepalo_dorsal_ancho_mm", 25.2))
    sep_l_len = float(caliz.get("sepalo_lateral_largo_mm", 94.0))
    sep_l_wid = float(caliz.get("sepalo_lateral_ancho_mm", 24.0))
    sep_l_ang = float(caliz.get("angulo_despliegue_lateral_grados", 134.0))

    pet_len = float(corola.get("petalo_lateral_largo_mm", 101.4))
    pet_wid = float(corola.get("petalo_lateral_ancho_mm", 66.1))
    lab_wid = float(corola.get("labelo_ancho_extendido_mm", 70.1))
    wall_t = float(corola.get("grosor_pared_mm", 0.65))

    col_len = float(androceo.get("columna_longitud_libre_mm", 33.0))
    col_wid = float(androceo.get("columna_ancho_mm", 10.7))
    ov_len = float(gineceo.get("ovario_pedicelado_longitud_mm", 72.0))

    # Paleta calibrada para evitar sobreexposicion bajo iluminacion aditiva Three.js
    c_lilac_base  = np.array([0.740, 0.565, 0.820])  # Lila pastel aterciopelado
    c_lilac_soft  = np.array([0.810, 0.660, 0.870])  # Lila claro borde rizado
    c_lilac_vein  = np.array([0.605, 0.415, 0.710])  # Nervadura lavanda sutil
    c_lilac_hood  = np.array([0.720, 0.515, 0.805])  # Capucha dorsal del labelo
    c_claw_cream  = np.array([0.825, 0.745, 0.855])  # Uña basal suave
    c_gold_throat = np.array([0.925, 0.685, 0.025])  # Garganta amarillo dorado
    c_amber_deep  = np.array([0.865, 0.520, 0.035])  # Sombra ambar garganta
    c_crimson     = np.array([0.595, 0.055, 0.325])  # Macula carmesi aterciopelada
    c_magenta     = np.array([0.715, 0.095, 0.435])  # Transicion magenta
    c_col_ivory   = np.array([0.925, 0.905, 0.825])  # Columna blanco-marfil
    c_col_rose    = np.array([0.840, 0.670, 0.770])  # Tinte rosaceo dorsal columna
    c_pollinia    = np.array([0.950, 0.760, 0.075])  # 4 polinios amarillo oro
    c_stigma      = np.array([0.855, 0.815, 0.580])  # Cavidad estigmatica ventral
    c_ovary_olive = np.array([0.410, 0.535, 0.260])  # Verde oliva ovario
    c_ovary_dark  = np.array([0.320, 0.430, 0.195])  # Surcos longitudinales ovario
    c_cuniculus   = np.array([0.775, 0.845, 0.480])  # Cuniculus nectarifero
    c_ovules      = np.array([0.940, 0.920, 0.825])  # Ovulos parietales

    vertices, colors = [], []
    groups = {}

    # =========================================================================
    # 1. OVARIO PEDICELADO INFERO Y ANATOMIA INTERNA (Centrado en x = 0)
    # =========================================================================
    f_ovary, f_cun, f_ovules = [], [], []
    n_ov_pts, sides_ov = 48, 24
    t_ov = np.linspace(0.0, 1.0, n_ov_pts)

    ov_pts = np.column_stack([
        np.zeros(n_ov_pts),
        -0.8 - 34.0 * (t_ov ** 1.25) + 5.0 * np.sin(math.pi * t_ov),
        -1.2 - ov_len * (0.86 * t_ov) - 3.5 * np.sin(math.pi * t_ov)
    ])

    radii_ov = np.zeros((n_ov_pts, sides_ov))
    cols_ov = np.zeros((n_ov_pts, sides_ov, 3))
    theta_ov = np.linspace(0.0, 2.0 * np.pi, sides_ov, endpoint=False)

    for i, t in enumerate(t_ov):
        swelling = 1.75 * math.exp(-((t - 0.24) / 0.14) ** 2)
        neck_flare = 0.85 * math.exp(-(t / 0.08) ** 2)
        r_base = 2.85 * (1.0 - 0.18 * t) + swelling + neck_flare
        for j, th in enumerate(theta_ov):
            rib = 0.20 * math.cos(6.0 * th)
            radii_ov[i, j] = r_base + rib
            mix_r = 0.5 + 0.5 * math.cos(6.0 * th)
            col_i = (1.0 - mix_r) * c_ovary_dark + mix_r * c_ovary_olive
            if t < 0.09:
                col_i = 0.72 * col_i + 0.28 * np.array([0.60, 0.70, 0.44])
            cols_ov[i, j] = col_i

    _add_closed_tube(ov_pts, radii_ov, cols_ov, sides_ov, vertices, colors, f_ovary,
                     cap_start=True, cap_end=True)
    groups["Ovario_Pedicelado_Pared"] = f_ovary

    # 1B. Cuniculus nectarifero (tunel dorsal interno en x = 0, adnato al ovario)
    n_cun = 24
    idx_cun = np.linspace(0, 22, n_cun).astype(int)
    cun_pts, cun_rad = [], []
    for k_i, idx in enumerate(idx_cun):
        u_c = k_i / max(1, n_cun - 1)
        p = ov_pts[idx].copy()
        p[0] = 0.0
        p[1] += 1.35 - 0.30 * u_c
        cun_pts.append(p)
        cun_rad.append(0.80 * (1.0 - 0.58 * (u_c ** 1.35)))
    _add_closed_tube(np.array(cun_pts), np.array(cun_rad), np.tile(c_cuniculus, (n_cun, 1)),
                     14, vertices, colors, f_cun, cap_start=True, cap_end=True)
    groups["Cuniculus_Nectarifero"] = f_cun

    # 1C. Camara ovarica y 3 placentas parietales simetricas (visibles en corte y Rayos X)
    n_loc = 20
    t_loc_idx = np.linspace(4, 21, n_loc).astype(int)
    loc_pts, loc_rad = [], []
    for k_i, idx in enumerate(t_loc_idx):
        u_l = k_i / max(1, n_loc - 1)
        p = ov_pts[idx].copy()
        p[0] = 0.0
        p[1] -= 0.85
        loc_pts.append(p)
        loc_rad.append(1.75 * math.sin(math.pi * (0.10 + 0.80 * u_l)))
    loc_pts = np.array(loc_pts)
    _add_closed_tube(loc_pts, np.array(loc_rad), np.tile(np.array([0.80, 0.86, 0.62]), (n_loc, 1)),
                     14, vertices, colors, f_ovules, cap_start=True, cap_end=True)

    rng = np.random.default_rng(42)
    placenta_angles = [math.radians(30.0), math.radians(150.0), math.radians(270.0)]
    for k_i in range(2, n_loc - 2):
        center_l = loc_pts[k_i]
        r_max = loc_rad[k_i] * 0.78
        for base_ang in placenta_angles:
            for sub in (-0.22, 0.22):
                ang_o = base_ang + sub
                ox = center_l[0] + r_max * math.cos(ang_o)
                oy = center_l[1] + r_max * math.sin(ang_o)
                oz = center_l[2] + rng.uniform(-0.75, 0.75)
                _add_ellipsoid((ox, oy, oz), (0.34, 0.42, 0.56), c_ovules, 5, 8,
                               vertices, colors, f_ovules)
    groups["Cavidad_Ovarica_Ovulos"] = f_ovules

    # =========================================================================
    # 2. SEPALOS (Dorsal erecto + 2 Laterales suavemente falcados hacia abajo)
    # =========================================================================
    sepal_specs = [
        ("Sepalo_Dorsal", 90.0, sep_d_len, sep_d_wid * 0.5, 0.0, -1.6, 0.0),
        ("Sepalo_Lateral_Izq", 90.0 + sep_l_ang, sep_l_len, sep_l_wid * 0.5, 1.0, -2.1, 5.5),
        ("Sepalo_Lateral_Der", 90.0 - sep_l_ang, sep_l_len, sep_l_wid * 0.5, -1.0, -2.1, -5.5),
    ]
    for grp_name, ang_deg, length, half_w, side_sign, z_base, falcate_shift in sepal_specs:
        f_sep = []
        n_v, n_u = 48, 24
        v_vals = np.linspace(0.0, 1.0, n_v)
        u_vals = np.linspace(-1.0, 1.0, n_u)
        base_idx = len(vertices)
        ca, sa = math.cos(math.radians(ang_deg)), math.sin(math.radians(ang_deg))

        for v in v_vals:
            w_prof = (math.sin(math.pi * (v ** 0.72)) ** 0.76) * (0.28 + 0.72 * math.sin(math.pi * min(1.0, v * 1.08)))
            r_d = v * length
            falc = falcate_shift * (v ** 2.1)
            for u in u_vals:
                w_loc = u * half_w * w_prof
                edge_s = (abs(u) ** 2.6) * _smoothstep(0.25, 0.75, v)
                wave_s = 1.2 * edge_s * math.sin(5.0 * math.pi * v + 0.8 * side_sign)

                px_loc = r_d
                py_loc = w_loc + falc
                px = px_loc * ca - py_loc * sa
                py = px_loc * sa + py_loc * ca - 0.5 * (1.0 - v)

                pz = (
                    z_base
                    + 5.2 * math.sin(math.pi * (v ** 0.85))
                    - 11.0 * (v ** 2.3)
                    + 1.9 * (1.0 - u ** 2) * math.sin(math.pi * v)
                    + wave_s
                )

                vein = 0.5 + 0.5 * math.cos(10.0 * math.pi * u)
                v_str = 0.24 * vein * (1.0 - 0.45 * v)
                col = (1.0 - v_str) * c_lilac_base + v_str * c_lilac_vein
                if v < 0.14:
                    mix_b = 1.0 - (v / 0.14)
                    col = (1.0 - 0.40 * mix_b) * col + (0.40 * mix_b) * c_claw_cream

                if grp_name.endswith("_Der"):
                    px = max(0.08, px)
                elif grp_name.endswith("_Izq"):
                    px = min(-0.08, px)
                vertices.append([px, py, pz])
                colors.append(np.clip(col, 0.0, 1.0).tolist())

        for i in range(n_v - 1):
            for j in range(n_u - 1):
                p1 = base_idx + i * n_u + j + 1
                p2 = base_idx + i * n_u + (j + 1) + 1
                p3 = base_idx + (i + 1) * n_u + (j + 1) + 1
                p4 = base_idx + (i + 1) * n_u + j + 1
                f_sep.append((p1, p2, p3))
                f_sep.append((p1, p3, p4))
        groups[grp_name] = f_sep

    # =========================================================================
    # 3. PETALOS LATERALES OVADO-ROMBICOS (Ondulacion organica suave, sin sierra)
    # =========================================================================
    petal_specs = [
        ("Petalo_Lateral_Der", 15.0, 1.0),
        ("Petalo_Lateral_Izq", 165.0, -1.0),
    ]
    for grp_name, ang_deg, side in petal_specs:
        f_pet = []
        n_v, n_u = 72, 44
        v_vals = np.linspace(0.0, 1.0, n_v)
        u_vals = np.linspace(-1.0, 1.0, n_u)
        base_idx = len(vertices)
        ca, sa = math.cos(math.radians(ang_deg)), math.sin(math.radians(ang_deg))
        half_pw = pet_wid * 0.5

        for v in v_vals:
            w_prof = (math.sin(math.pi * (v ** 0.82)) ** 0.84) * (0.24 + 0.76 * math.sin(math.pi * min(1.0, v * 1.14)))
            r_d = v * pet_len
            for u in u_vals:
                abs_u = abs(u)
                edge_mask = (abs_u ** 2.3) * _smoothstep(0.18, 0.58, v)

                wave_z = edge_mask * (
                    5.0 * math.sin(4.2 * math.pi * v + 0.5 * side)
                    + 2.3 * math.cos(8.0 * math.pi * v - 1.2 * u)
                    + 0.9 * math.sin(12.0 * math.pi * v + 1.6 * u)
                )
                wave_w = edge_mask * (1.6 * math.sin(4.2 * math.pi * v + 0.5 * side))
                midrib = 1.6 * math.exp(-16.0 * (u ** 2)) * math.sin(math.pi * v)

                w_loc = u * half_pw * w_prof + wave_w
                px = r_d * ca - w_loc * sa
                py = r_d * sa + w_loc * ca - 3.6 * (v ** 1.9)

                pz = (
                    0.4
                    + 8.2 * math.sin(math.pi * (v ** 0.82)) * (1.0 - 0.45 * (u ** 2))
                    - 5.2 * (v ** 2.4)
                    + midrib
                    + wave_z
                )

                vein_pat = 0.5 + 0.5 * math.cos(16.0 * math.pi * u * (0.35 + 0.65 * v))
                vein_strength = 0.28 * vein_pat * (1.0 - 0.35 * v)
                col = (1.0 - vein_strength) * c_lilac_base + vein_strength * c_lilac_vein
                rim_mix = 0.30 * (abs_u ** 2.5) * _smoothstep(0.3, 0.9, v)
                col = (1.0 - rim_mix) * col + rim_mix * c_lilac_soft
                if v < 0.14:
                    mix_c = 1.0 - (v / 0.14)
                    col = (1.0 - 0.50 * mix_c) * col + (0.50 * mix_c) * c_claw_cream

                if grp_name.endswith("_Der"):
                    px = max(0.08, px)
                elif grp_name.endswith("_Izq"):
                    px = min(-0.08, px)
                vertices.append([px, py, pz])
                colors.append(np.clip(col, 0.0, 1.0).tolist())

        for i in range(n_v - 1):
            for j in range(n_u - 1):
                p1 = base_idx + i * n_u + j + 1
                p2 = base_idx + i * n_u + (j + 1) + 1
                p3 = base_idx + (i + 1) * n_u + (j + 1) + 1
                p4 = base_idx + (i + 1) * n_u + j + 1
                f_pet.append((p1, p2, p3))
                f_pet.append((p1, p3, p4))
        groups[grp_name] = f_pet

    # =========================================================================
    # 4. LABELO TRILOBULADO CONVOLUTO HERMETICO DE DOBLE PARED
    # =========================================================================
    f_lip_tube, f_lip_front = [], []
    n_lv, n_lu = 86, 76
    split_i = 45
    v_lab = np.linspace(0.0, 1.0, n_lv)
    u_lab = np.linspace(-1.0, 1.0, n_lu)

    pts_out = np.zeros((n_lv, n_lu, 3))
    pts_in = np.zeros((n_lv, n_lu, 3))
    cols_out = np.zeros((n_lv, n_lu, 3))
    cols_in = np.zeros((n_lv, n_lu, 3))

    for i, v in enumerate(v_lab):
        flare = float(_smoothstep(0.46, 0.72, v))
        tube_wrap = math.radians(158.0 + 34.0 * math.sin(math.pi * min(1.0, v / 0.56)))
        open_ang = math.radians(82.0)
        max_ang = (1.0 - flare) * tube_wrap + flare * open_ang

        r_tube = 5.4 + 9.2 * (v ** 0.85)
        w_flare = (lab_wid * 0.5) * (math.sin(math.pi * min(1.0, max(0.0, (v - 0.36) / 0.68))) ** 0.68)

        cy = -1.5 - 18.0 * (v ** 1.15) - 44.0 * (max(0.0, v - 0.38) ** 1.35)
        cz = 0.2 + 35.0 * math.sin(0.5 * math.pi * min(1.0, v / 0.60)) + 13.0 * max(0.0, v - 0.56)

        for j, u in enumerate(u_lab):
            abs_u = abs(u)
            theta = u * max_ang

            overlap_r = 0.35 * u * (1.0 - flare)
            rt_o = r_tube + overlap_r
            rt_i = max(2.8, rt_o - wall_t)

            tx_o = rt_o * 1.08 * math.sin(theta)
            ty_o = cy - rt_o * 1.02 * math.cos(theta)
            tz_o = cz + rt_o * 0.20 * math.cos(theta)

            tx_i = rt_i * 1.08 * math.sin(theta)
            ty_i = cy - rt_i * 1.02 * math.cos(theta)
            tz_i = cz + rt_i * 0.20 * math.cos(theta)

            emarg_notch = 7.0 * (_smoothstep(0.65, 1.0, v) ** 1.6) * math.exp(-16.0 * (u ** 2))
            fx = u * max(w_flare, r_tube * 1.15)
            fy = cy - 9.5 * (1.0 - 0.45 * (u ** 2)) * flare + emarg_notch
            fz = cz + 5.5 * (1.0 - (u ** 2)) * flare - 0.45 * emarg_notch

            px_o = (1.0 - flare) * tx_o + flare * fx
            py_o = (1.0 - flare) * ty_o + flare * fy
            pz_o = (1.0 - flare) * tz_o + flare * fz

            px_i = (1.0 - flare) * tx_i + flare * fx
            py_i = (1.0 - flare) * ty_i + flare * (fy + wall_t * 0.5)
            pz_i = (1.0 - flare) * tz_i + flare * (fz + wall_t * 0.85)

            ruffle_env = _smoothstep(0.48, 0.68, v) * (
                0.22 * (abs_u ** 1.3) + 0.78 * max(abs_u ** 1.5, float(_smoothstep(0.76, 1.0, v)))
            )
            ruffle = ruffle_env * (
                3.2 * math.sin(10.0 * math.pi * u + 1.5 * math.pi * v)
                + 1.6 * math.cos(22.0 * math.pi * u - 3.0 * math.pi * v)
                + 0.7 * math.sin(36.0 * math.pi * u + 4.0 * math.pi * v)
            )
            pz_o += ruffle
            py_o += ruffle * 0.45
            pz_i += ruffle
            py_i += ruffle * 0.45

            pts_out[i, j] = [px_o, py_o, pz_o]
            pts_in[i, j] = [px_i, py_i, pz_i]

            # Coloracion adaxial (garganta dorada estriada -> macula carmesi -> borde lila)
            striation = (0.5 + 0.5 * math.cos(30.0 * math.pi * u)) ** 2.4
            throat_col = (1.0 - 0.50 * striation) * c_gold_throat + (0.50 * striation) * c_crimson
            throat_col = 0.86 * throat_col + 0.14 * c_amber_deep

            v_front = max(0.0, (v - 0.44) / 0.56)
            feather = 0.042 * math.cos(32.0 * math.pi * u)
            ellip_dist = math.sqrt((u / 0.92) ** 2 + (v_front / 0.92) ** 2) + feather

            if ellip_dist < 0.46:
                col_adax = throat_col
            elif ellip_dist < 0.85:
                m_mac = float(_smoothstep(0.46, 0.64, ellip_dist))
                mac_tone = (1.0 - 0.25 * abs_u) * c_crimson + (0.25 * abs_u) * c_magenta
                col_adax = (1.0 - m_mac) * throat_col + m_mac * mac_tone
            else:
                m_rim = float(_smoothstep(0.85, 0.97, ellip_dist))
                col_adax = (1.0 - m_rim) * c_magenta + m_rim * c_lilac_soft

            cols_in[i, j] = np.clip(col_adax, 0.0, 1.0)

            # Coloracion abaxial (exterior lila pastel en la capucha)
            if v < 0.56:
                dorsal_mix = _smoothstep(0.35, 0.95, abs_u)
                col_abax = (1.0 - 0.45 * dorsal_mix) * c_lilac_base + (0.45 * dorsal_mix) * c_lilac_hood
            else:
                mix_f = float(_smoothstep(0.56, 0.75, v))
                col_abax = (1.0 - mix_f) * c_lilac_base + mix_f * (0.52 * col_adax + 0.48 * c_lilac_soft)

            cols_out[i, j] = np.clip(col_abax, 0.0, 1.0)

    _add_double_shell_grid(pts_out, pts_in, cols_out, cols_in, 0, split_i + 1,
                           vertices, colors, f_lip_tube, cap_v_start=True, cap_v_end=False)
    _add_double_shell_grid(pts_out, pts_in, cols_out, cols_in, split_i, n_lv,
                           vertices, colors, f_lip_front, cap_v_start=False, cap_v_end=True)

    groups["Labelo_Tubo_Garganta"] = f_lip_tube
    groups["Labelo_Lobulo_Frontal_Macula"] = f_lip_front

    # =========================================================================
    # 5. GINOSTEMIO (Columna arqueada superior), 4 POLINIOS Y ESTIGMA
    # =========================================================================
    f_col, f_pol, f_stig = [], [], []
    n_col, sides_col = 28, 22
    t_col = np.linspace(0.0, 1.0, n_col)

    col_pts = np.column_stack([
        np.zeros(n_col),
        0.5 - 7.8 * (t_col ** 1.45) + 2.4 * np.sin(math.pi * t_col),
        0.6 + col_len * 0.94 * t_col
    ])

    radii_col = np.zeros((n_col, sides_col))
    cols_col = np.zeros((n_col, sides_col, 3))
    theta_col = np.linspace(0.0, 2.0 * np.pi, sides_col, endpoint=False)

    for i, t in enumerate(t_col):
        profile_w = 0.72 + 0.30 * math.sin(0.5 * math.pi * t) - 0.16 * (t ** 6)
        r_base = (col_wid * 0.5) * profile_w
        for j, th in enumerate(theta_col):
            radii_col[i, j] = r_base
            dorsal_tint = max(0.0, math.sin(th)) * (0.35 + 0.65 * t)
            cols_col[i, j] = (1.0 - 0.45 * dorsal_tint) * c_col_ivory + (0.45 * dorsal_tint) * c_col_rose

    _add_closed_tube(col_pts, radii_col, cols_col, sides_col, vertices, colors, f_col,
                     cap_start=True, cap_end=True, rx_scale=1.0, ry_scale=0.66,
                     ventral_flatten=0.70)
    groups["Columna_Ginostemio"] = f_col

    # 5B. Operculo anteral + 4 Polinios cerosos en 2 pares paralelos
    apex_pt = col_pts[-1]
    _add_ellipsoid(
        (apex_pt[0], apex_pt[1] + 0.55, apex_pt[2] + 0.80),
        (2.35, 1.30, 1.75),
        np.array([0.94, 0.90, 0.78]),
        8, 12, vertices, colors, f_pol
    )
    pollinia_offsets = [
        (-1.20, -0.35, 0.85),
        (-0.48, -0.45, 1.05),
        (0.48, -0.45, 1.05),
        (1.20, -0.35, 0.85),
    ]
    for ox, oy, oz in pollinia_offsets:
        _add_ellipsoid(
            (apex_pt[0] + ox, apex_pt[1] + oy, apex_pt[2] + oz),
            (0.32, 0.66, 0.94),
            c_pollinia,
            7, 10, vertices, colors, f_pol
        )
    groups["Antera_Polinios_4"] = f_pol

    # 5C. Cavidad estigmatica ventral (inmediatamente bajo el rostelo)
    stig_pt = col_pts[-4]
    _add_ellipsoid(
        (stig_pt[0], stig_pt[1] - 1.70, stig_pt[2] + 0.35),
        (2.05, 0.85, 1.95),
        c_stigma,
        7, 12, vertices, colors, f_stig
    )
    groups["Cavidad_Estigmatica"] = f_stig

    # =========================================================================
    # ENSAMBLAJE DEL OBJ CON VERTEX COLORS Y GRUPOS HISTOLOGICOS
    # =========================================================================
    lines = []
    for v, c in zip(vertices, colors):
        lines.append(f"v {v[0]:.4f} {v[1]:.4f} {v[2]:.4f} {c[0]:.4f} {c[1]:.4f} {c[2]:.4f}" + NL)

    for grp_name, grp_faces in groups.items():
        lines.append(f"g {grp_name}" + NL)
        for f_idx in grp_faces:
            lines.append(f"f {f_idx[0]} {f_idx[1]} {f_idx[2]}" + NL)

    return "".join(lines)
