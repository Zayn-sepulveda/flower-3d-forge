import math
import numpy as np


def _smoothstep(e0, e1, x):
    t = np.clip((x - e0) / max(1e-6, (e1 - e0)), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _add_closed_tube(curve_pts, radii, colors_ring, n_slices, vertices, colors, faces,
                     cap_start=True, cap_end=True, rx_scale=1.0, ry_scale=1.0,
                     ref_vec=(0.0, 0.0, 1.0)):
    """Genera un tubo parametrico hermetico sin torsion en el plano XY."""
    n_rings = len(curve_pts)
    base_idx = len(vertices)
    theta_vals = np.linspace(0.0, 2.0 * np.pi, n_slices, endpoint=False)
    ref = np.array(ref_vec, dtype=float)

    for i in range(n_rings):
        p = curve_pts[i]
        if i == 0:
            tang = curve_pts[1] - p
        elif i == n_rings - 1:
            tang = p - curve_pts[i - 1]
        else:
            tang = curve_pts[i + 1] - curve_pts[i - 1]
        nt = np.linalg.norm(tang)
        tang = tang / (nt if nt > 1e-6 else 1.0)

        r_use = ref if abs(np.dot(tang, ref)) < 0.92 else np.array([1.0, 0.0, 0.0])
        n1 = np.cross(tang, r_use)
        n1 /= max(1e-6, np.linalg.norm(n1))
        n2 = np.cross(n1, tang)
        n2 /= max(1e-6, np.linalg.norm(n2))

        for j, th in enumerate(theta_vals):
            r = radii[i, j] if np.ndim(radii) == 2 else radii[i]
            pt = p + r * (rx_scale * math.cos(th) * n1 + ry_scale * math.sin(th) * n2)
            vertices.append(pt.tolist())
            c = colors_ring[i, j] if np.ndim(colors_ring) == 3 else colors_ring[i]
            colors.append(np.clip(c, 0.0, 1.0).tolist())

    for i in range(n_rings - 1):
        for j in range(n_slices):
            jn = (j + 1) % n_slices
            p1 = base_idx + i * n_slices + j + 1
            p2 = base_idx + i * n_slices + jn + 1
            p3 = base_idx + (i + 1) * n_slices + jn + 1
            p4 = base_idx + (i + 1) * n_slices + j + 1
            faces.append((p1, p2, p3))
            faces.append((p1, p3, p4))

    if cap_start:
        c0 = colors_ring[0, 0] if np.ndim(colors_ring) == 3 else colors_ring[0]
        vertices.append(curve_pts[0].tolist())
        colors.append(np.clip(c0, 0.0, 1.0).tolist())
        vc = len(vertices)
        for j in range(n_slices):
            jn = (j + 1) % n_slices
            faces.append((vc, base_idx + jn + 1, base_idx + j + 1))

    if cap_end:
        ce = colors_ring[-1, 0] if np.ndim(colors_ring) == 3 else colors_ring[-1]
        vertices.append(curve_pts[-1].tolist())
        colors.append(np.clip(ce, 0.0, 1.0).tolist())
        vc = len(vertices)
        off = base_idx + (n_rings - 1) * n_slices
        for j in range(n_slices):
            jn = (j + 1) % n_slices
            faces.append((vc, off + j + 1, off + jn + 1))


def _add_ellipsoid(center, radii_xyz, color_rgb, n_lat, n_lon, vertices, colors, faces,
                   rot_z=0.0, rugose_amp=0.0, color_var=0.0, inner_invert=False):
    """Genera un elipsoide solido cerrado (soporta textura rugosa para pirenos y caras internas)."""
    base_idx = len(vertices)
    cx, cy, cz = center
    rx, ry, rz = radii_xyz
    c_base = np.array(color_rgb, dtype=float)
    cz_r, sz_r = math.cos(rot_z), math.sin(rot_z)

    for i in range(n_lat + 1):
        phi = math.pi * i / n_lat
        sp, cp = math.sin(phi), math.cos(phi)
        for j in range(n_lon):
            th = 2.0 * math.pi * j / n_lon
            rug = 1.0 + rugose_amp * (
                math.sin(5.0 * th + 3.0 * phi) * 0.6 + math.cos(7.0 * phi - 4.0 * th) * 0.4
            )
            lx = rx * sp * math.cos(th) * rug
            ly = ry * cp * rug
            lz = rz * sp * math.sin(th) * rug

            px = cx + lx * cz_r - ly * sz_r
            py = cy + lx * sz_r + ly * cz_r
            pz = cz + lz

            shade = 1.0 + color_var * (rug - 1.0) / max(1e-4, rugose_amp) if rugose_amp > 0 else 1.0
            vertices.append([px, py, pz])
            colors.append(np.clip(c_base * shade, 0.0, 1.0).tolist())

    for i in range(n_lat):
        for j in range(n_lon):
            jn = (j + 1) % n_lon
            p1 = base_idx + i * n_lon + j + 1
            p2 = base_idx + i * n_lon + jn + 1
            p3 = base_idx + (i + 1) * n_lon + jn + 1
            p4 = base_idx + (i + 1) * n_lon + j + 1
            if inner_invert:
                faces.append((p1, p3, p2))
                faces.append((p1, p4, p3))
            else:
                faces.append((p1, p2, p3))
                faces.append((p1, p3, p4))


def _add_double_shell_grid(pts_out, pts_in, cols_out, cols_in, vertices, colors, faces):
    """Construye una cascara solida cerrada (bractea cimbiforme o lamina) cosida en los 4 bordes."""
    n_v, n_u = pts_out.shape[0], pts_out.shape[1]
    base_o = len(vertices)
    for i in range(n_v):
        for j in range(n_u):
            vertices.append(pts_out[i, j].tolist())
            colors.append(np.clip(cols_out[i, j], 0.0, 1.0).tolist())

    base_i = len(vertices)
    for i in range(n_v):
        for j in range(n_u):
            vertices.append(pts_in[i, j].tolist())
            colors.append(np.clip(cols_in[i, j], 0.0, 1.0).tolist())

    for i in range(n_v - 1):
        for j in range(n_u - 1):
            p1 = base_o + i * n_u + j + 1
            p2 = base_o + i * n_u + (j + 1) + 1
            p3 = base_o + (i + 1) * n_u + (j + 1) + 1
            p4 = base_o + (i + 1) * n_u + j + 1
            faces.append((p1, p2, p3))
            faces.append((p1, p3, p4))

            q1 = base_i + i * n_u + j + 1
            q2 = base_i + i * n_u + (j + 1) + 1
            q3 = base_i + (i + 1) * n_u + (j + 1) + 1
            q4 = base_i + (i + 1) * n_u + j + 1
            faces.append((q1, q3, q2))
            faces.append((q1, q4, q3))

    # Costura bordes laterales (j = 0 y j = n_u - 1)
    for i in range(n_v - 1):
        o1, o2 = base_o + i * n_u + 1, base_o + (i + 1) * n_u + 1
        i1, i2 = base_i + i * n_u + 1, base_i + (i + 1) * n_u + 1
        faces.append((o1, o2, i2))
        faces.append((o1, i2, i1))

        o1 = base_o + i * n_u + (n_u - 1) + 1
        o2 = base_o + (i + 1) * n_u + (n_u - 1) + 1
        i1 = base_i + i * n_u + (n_u - 1) + 1
        i2 = base_i + (i + 1) * n_u + (n_u - 1) + 1
        faces.append((o1, i2, o2))
        faces.append((o1, i1, i2))

    # Costura borde basal (i = 0) y distal (i = n_v - 1)
    for j in range(n_u - 1):
        o1, o2 = base_o + j + 1, base_o + j + 2
        i1, i2 = base_i + j + 1, base_i + j + 2
        faces.append((o1, i2, o2))
        faces.append((o1, i1, i2))

        lo = (n_v - 1) * n_u
        o1, o2 = base_o + lo + j + 1, base_o + lo + j + 2
        i1, i2 = base_i + lo + j + 1, base_i + lo + j + 2
        faces.append((o1, o2, i2))
        faces.append((o1, i2, i1))


def _build_cymbiform_bract(node_pt, side, length, h_keel, h_lip, half_z, droop_deg,
                           wall_t, vertices, colors, faces):
    """Construye una bractea cimbiforme de doble pared (bote con concavidad hacia abajo)."""
    n_v, n_u = 28, 22
    v_vals = np.linspace(0.0, 1.0, n_v)
    u_vals = np.linspace(-1.0, 1.0, n_u)

    ang = math.radians(droop_deg)
    e_l = np.array([side * math.cos(ang), -math.sin(ang), 0.0])
    e_u = np.array([side * math.sin(ang), math.cos(ang), 0.0])
    e_z = np.array([0.0, 0.0, 1.0])

    c_red_deep  = np.array([0.66, 0.09, 0.11])
    c_red_scarl = np.array([0.82, 0.13, 0.15])
    c_yellow    = np.array([0.93, 0.77, 0.10])
    c_green_rim = np.array([0.36, 0.62, 0.16])
    c_green_tip = np.array([0.27, 0.50, 0.13])
    c_inner_ros = np.array([0.88, 0.72, 0.66])
    c_inner_yel = np.array([0.84, 0.84, 0.56])

    pts_o = np.zeros((n_v, n_u, 3))
    pts_i = np.zeros((n_v, n_u, 3))
    cols_o = np.zeros((n_v, n_u, 3))
    cols_i = np.zeros((n_v, n_u, 3))

    for i, v in enumerate(v_vals):
        lx = -4.2 + v * (length + 4.2)
        bell = math.sin(math.pi * (v ** 0.66)) ** 0.78
        base_wrap = (1.0 - v) ** 2.6

        keel_y = h_keel * (0.24 * base_wrap + 0.90 * bell)
        lip_y = -h_lip * (math.sin(math.pi * (v ** 0.78)) ** 0.85)
        beak_lift = 4.2 * (v ** 2.8)

        cy = 0.5 * (keel_y + lip_y)
        ry_o = max(0.35, 0.5 * (keel_y - lip_y))
        rz_o = max(0.35, half_z * (0.24 * base_wrap + 0.88 * (math.sin(math.pi * (v ** 0.70)) ** 0.78)))

        wt = wall_t * (0.18 + 0.82 * math.sin(math.pi * v))
        ry_i = max(0.20, ry_o - wt)
        rz_i = max(0.20, rz_o - wt)

        for j, u in enumerate(u_vals):
            theta = u * math.radians(114.0)
            ct, st = math.cos(theta), math.sin(theta)

            ly_o = cy + ry_o * ct + beak_lift
            lz_o = rz_o * st
            ly_i = cy + ry_i * ct + beak_lift
            lz_i = rz_i * st

            pts_o[i, j] = node_pt + lx * e_l + ly_o * e_u + lz_o * e_z
            pts_i[i, j] = node_pt + lx * e_l + ly_i * e_u + lz_i * e_z

            # Gradiente cromatico real: cuerpo rojo escarlata -> banda amarilla -> margen/apice verde
            abs_u = abs(u)
            edge_zone = max(v ** 2.1, (abs_u ** 2.2) * (0.42 + 0.58 * v))
            pub_tex = 0.04 * math.sin(24.0 * v + 14.0 * u)

            if edge_zone < 0.55:
                m_r = float(_smoothstep(0.0, 0.55, edge_zone))
                co = (1.0 - 0.35 * (1.0 - m_r)) * c_red_scarl + (0.35 * (1.0 - m_r)) * c_red_deep
            elif edge_zone < 0.78:
                m_y = float(_smoothstep(0.55, 0.76, edge_zone))
                co = (1.0 - m_y) * c_red_scarl + m_y * c_yellow
            else:
                m_g = float(_smoothstep(0.78, 0.96, edge_zone))
                g_tgt = c_green_tip if v > 0.78 else c_green_rim
                co = (1.0 - m_g) * c_yellow + m_g * g_tgt

            cols_o[i, j] = np.clip(co + pub_tex, 0.0, 1.0)

            mi = float(_smoothstep(0.35, 0.95, abs_u))
            cols_i[i, j] = np.clip((1.0 - mi) * c_inner_ros + mi * c_inner_yel, 0.0, 1.0)

    _add_double_shell_grid(pts_o, pts_i, cols_o, cols_i, vertices, colors, faces)


def _build_terminal_bract(node_pt, length, vertices, colors, faces):
    """Construye la bractea apical terminal colgante que cierra el eje de la inflorescencia."""
    n_v, n_u = 22, 16
    v_vals = np.linspace(0.0, 1.0, n_v)
    u_vals = np.linspace(-1.0, 1.0, n_u)

    c_red = np.array([0.80, 0.13, 0.15])
    c_yel = np.array([0.92, 0.76, 0.10])
    c_grn = np.array([0.34, 0.60, 0.16])
    c_inn = np.array([0.86, 0.74, 0.66])

    pts_o = np.zeros((n_v, n_u, 3))
    pts_i = np.zeros((n_v, n_u, 3))
    cols_o = np.zeros((n_v, n_u, 3))
    cols_i = np.zeros((n_v, n_u, 3))

    for i, v in enumerate(v_vals):
        py = node_pt[1] + 4.0 - v * (length + 4.0)
        bell = math.sin(math.pi * (v ** 0.72)) ** 0.80
        rx_o = max(0.3, 10.5 * (0.24 * (1.0 - v) ** 2.5 + 0.86 * bell))
        rz_o = max(0.3, 8.5 * (0.24 * (1.0 - v) ** 2.5 + 0.86 * bell))
        wt = 1.6 * (0.2 + 0.8 * math.sin(math.pi * v))

        for j, u in enumerate(u_vals):
            th = u * math.radians(150.0)
            pts_o[i, j] = [node_pt[0] + rx_o * math.cos(th), py, rz_o * math.sin(th)]
            pts_i[i, j] = [node_pt[0] + max(0.15, rx_o - wt) * math.cos(th), py, max(0.15, rz_o - wt) * math.sin(th)]

            ez = max(v ** 1.9, (abs(u) ** 2.4) * (0.3 + 0.7 * v))
            if ez < 0.56:
                co = c_red
            elif ez < 0.80:
                m = float(_smoothstep(0.56, 0.78, ez))
                co = (1.0 - m) * c_red + m * c_yel
            else:
                m = float(_smoothstep(0.80, 0.96, ez))
                co = (1.0 - m) * c_yel + m * c_grn
            cols_o[i, j] = co
            cols_i[i, j] = c_inn

    _add_double_shell_grid(pts_o, pts_i, cols_o, cols_i, vertices, colors, faces)


def build_heliconiaceae_flower(cfg):
    """
    Generador morfometrico v2 para Heliconia rostrata Ruiz & Pav. (COL-ATL-007):
    - Pedunculo pendulo y raquis flexuoso en zigzag con corteza roja y parenquima vascular interno.
    - 10 bracteas cincinales disticas cimbiformes de doble pared + 1 bractea apical terminal.
    - Cincinos con pedicelos vilosos, bracteolas, botones y flores tubulares (tubo + 1 sepalo libre).
    - Androceo de 5 estambres fertiles + 1 estaminodio blanco espatulado diagnostico (14.5 x 4.2 mm).
    - Gineceo con ovario infero trilocular (ovulos internos visibles en z = 0) y estilo delgado.
    - Esquizocarpos drupaceos azul metalico en bracteas proximales con pirenos leñosos internos.
    """
    NL = chr(10)
    arq = cfg.get("arquitectura_floral") or {}

    ped_len = float(arq.get("pedunculo_largo_mm", 95.0))
    ped_rad = float(arq.get("pedunculo_diametro_mm", 8.4)) * 0.5
    n_bracts = int(arq.get("bracteas_numero", 10))
    b_len_base = float(arq.get("bractea_largo_basal_mm", 96.0))
    b_len_tip = float(arq.get("bractea_largo_apical_mm", 68.0))

    # Paleta botanica calibrada
    c_ped_red   = np.array([0.74, 0.14, 0.16])
    c_rach_red  = np.array([0.78, 0.13, 0.15])
    c_rach_pith = np.array([0.92, 0.80, 0.76])
    c_pedicel   = np.array([0.90, 0.90, 0.78])
    c_bracteole = np.array([0.89, 0.88, 0.76])
    c_per_base  = np.array([0.94, 0.94, 0.87])
    c_per_yel   = np.array([0.94, 0.81, 0.12])
    c_per_grn   = np.array([0.42, 0.68, 0.18])
    c_filament  = np.array([0.94, 0.92, 0.80])
    c_anther    = np.array([0.86, 0.75, 0.42])
    c_staminode = np.array([0.97, 0.96, 0.92])
    c_ovary_grn = np.array([0.55, 0.72, 0.34])
    c_ovary_in  = np.array([0.78, 0.86, 0.58])
    c_ovule_crm = np.array([0.96, 0.95, 0.84])
    c_style     = np.array([0.94, 0.93, 0.84])
    c_drupe_exo = np.array([0.09, 0.20, 0.48])  # Azul metalico oscuro maduro
    c_drupe_mes = np.array([0.62, 0.78, 0.92])  # Mesocarpo carnoso azul cielo
    c_pyrene    = np.array([0.31, 0.22, 0.15])  # Endocarpo leñoso pardo rugoso

    vertices, colors = [], []
    groups = {
        "Pedunculo_Pendulo": [],
        "Raquis_Flexuoso_Zigzag": [],
        "Raquis_Parenquima_Vascular": [],
        "Bracteas_Cincinales_Cimbiformes": [],
        "Pedicelos_Bracteolas_Cincino": [],
        "Perianto_Tubo_Sepalo_Libre": [],
        "Androceo_5_Estambres": [],
        "Estaminodio_Diagnostico": [],
        "Ovario_Infero_Estilo": [],
        "Esquizocarpo_Drupa_Azul": [],
        "Pirenos_Endocarpo_Lenoso": [],
    }

    # =========================================================================
    # 1. PEDUNCULO PENDULO Y RAQUIS FLEXUOSO EN ZIGZAG (+ PARENQUIMA INTERNO)
    # =========================================================================
    y_top = 148.0
    n_ped = 20
    t_ped = np.linspace(0.0, 1.0, n_ped)
    ped_pts = np.column_stack([
        -4.5 * (1.0 - t_ped) ** 1.5 + 2.5 * np.sin(math.pi * t_ped),
        y_top + ped_len * (1.0 - t_ped),
        np.zeros(n_ped)
    ])
    ped_rad_arr = np.linspace(ped_rad * 1.06, ped_rad * 0.96, n_ped)
    ped_cols = np.array([
        np.clip(c_ped_red * (0.94 + 0.08 * math.sin(18.0 * t)), 0.0, 1.0)
        for t in t_ped
    ])
    _add_closed_tube(ped_pts, ped_rad_arr, ped_cols, 16, vertices, colors,
                     groups["Pedunculo_Pendulo"], cap_start=True, cap_end=True)

    # Nodos dísticos en zigzag del raquis
    nodes = [np.array([0.0, y_top, 0.0])]
    bract_meta = []
    cur_y = y_top
    for k in range(n_bracts):
        frac = k / max(1, n_bracts - 1)
        step_y = 33.0 * (1.0 - frac) + 22.0 * frac
        cur_y -= step_y if k > 0 else 8.0
        side = -1.0 if (k % 2 == 0) else 1.0
        amp_x = 10.2 * (1.0 - 0.36 * frac)
        n_pt = np.array([side * amp_x, cur_y, 0.0])
        nodes.append(n_pt)
        bract_meta.append((k, n_pt, side, frac))

    term_pt = np.array([0.0, cur_y - 18.0, 0.0])
    nodes.append(term_pt)

    # Interpolar curva suave flexuosa en zigzag pasando por todos los nodos
    rach_pts = []
    rach_rad = []
    pith_rad = []
    for idx in range(len(nodes) - 1):
        p0, p1 = nodes[idx], nodes[idx + 1]
        sub_n = 9
        for s in range(sub_n):
            t = s / float(sub_n)
            ts = t * t * (3.0 - 2.0 * t)
            px = p0[0] + (p1[0] - p0[0]) * ts
            py = p0[1] + (p1[1] - p0[1]) * t
            rach_pts.append([px, py, 0.0])
            g_frac = (idx + t) / max(1, len(nodes) - 1)
            nodal_bump = 0.65 * math.exp(-((t - 0.0) / 0.18) ** 2)
            ro = (4.35 * (1.0 - 0.42 * g_frac)) + nodal_bump
            rach_rad.append(ro)
            pith_rad.append(ro * 0.72)
    rach_pts.append(nodes[-1].tolist())
    rach_rad.append(2.3)
    pith_rad.append(1.6)

    rach_pts = np.array(rach_pts)
    rach_rad = np.array(rach_rad)
    pith_rad = np.array(pith_rad)

    rach_cols = np.array([
        np.clip(c_rach_red * (0.93 + 0.09 * math.sin(0.9 * i)), 0.0, 1.0)
        for i in range(len(rach_pts))
    ])
    pith_cols = np.array([
        np.clip(c_rach_pith * (0.95 + 0.06 * math.cos(1.3 * i)), 0.0, 1.0)
        for i in range(len(rach_pts))
    ])

    _add_closed_tube(rach_pts, rach_rad, rach_cols, 16, vertices, colors,
                     groups["Raquis_Flexuoso_Zigzag"], cap_start=True, cap_end=True)
    _add_closed_tube(rach_pts, pith_rad, pith_cols, 14, vertices, colors,
                     groups["Raquis_Parenquima_Vascular"], cap_start=True, cap_end=True)

    # =========================================================================
    # 2. BRACTEAS CIMBIFORMES DISTICAS, CINCINOS FLORALES Y DRUPAS AZULES
    # =========================================================================
    for k, node_pt, side, frac in bract_meta:
        b_len = b_len_base * (1.0 - frac) + b_len_tip * frac
        h_keel = 22.5 * (1.0 - 0.25 * frac)
        h_lip = 13.0 * (1.0 - 0.25 * frac)
        half_z = 16.5 * (1.0 - 0.24 * frac)
        droop_deg = 12.0 + 14.0 * frac

        _build_cymbiform_bract(
            node_pt, side, b_len, h_keel, h_lip, half_z, droop_deg, 2.3,
            vertices, colors, groups["Bracteas_Cincinales_Cimbiformes"]
        )

        ang = math.radians(droop_deg)
        e_l = np.array([side * math.cos(ang), -math.sin(ang), 0.0])
        e_u = np.array([side * math.sin(ang), math.cos(ang), 0.0])
        e_z = np.array([0.0, 0.0, 1.0])

        # --- A. BRACTEAS PROXIMALES SUPERIORES (k = 0, 1): ESQUIZOCARPOS AZULES ---
        if k in (0, 1):
            # Pedicelo engrosado + drupa madura seccionable en z = 0
            ped_start = node_pt + 14.0 * e_l + 3.0 * e_u
            drupe_ctr = node_pt + (b_len * 0.44) * e_l - 3.5 * e_u
            p_curve = np.array([ped_start, 0.5 * (ped_start + drupe_ctr) + 1.5 * e_u, drupe_ctr - 5.0 * e_l])
            _add_closed_tube(p_curve, np.array([2.2, 2.5, 2.8]),
                             np.tile(c_pedicel, (3, 1)), 10, vertices, colors,
                             groups["Pedicelos_Bracteolas_Cincino"])

            # Drupa principal (exocarpo azul metalico + mesocarpo carnoso interno + 2 pirenos leñosos)
            _add_ellipsoid(drupe_ctr, (7.0, 6.8, 6.8), c_drupe_exo, 12, 16,
                           vertices, colors, groups["Esquizocarpo_Drupa_Azul"])
            _add_ellipsoid(drupe_ctr, (6.0, 5.8, 5.8), c_drupe_mes, 10, 14,
                           vertices, colors, groups["Esquizocarpo_Drupa_Azul"], inner_invert=True)

            # 2 pirenos leñosos rugosos visibles en z <= 0 + 1 posterior
            pyr_offsets = [
                (-1.2 * side, 2.0, -2.0),
                (1.4 * side, -2.0, -2.0),
                (0.0, 0.0, 2.4),
            ]
            for ox, oy, oz in pyr_offsets:
                p_c = drupe_ctr + np.array([ox, oy, oz])
                _add_ellipsoid(p_c, (3.2, 2.2, 2.0), c_pyrene, 8, 10,
                               vertices, colors, groups["Pirenos_Endocarpo_Lenoso"],
                               rot_z=side * 0.45, rugose_amp=0.11, color_var=0.22)

            # Segunda drupa ligeramente mas externa (asomando del bote como en la foto objetivo)
            if k == 1:
                d2_ctr = node_pt + (b_len * 0.64) * e_l - 7.5 * e_u - 4.5 * e_z
                _add_ellipsoid(d2_ctr, (6.2, 6.0, 6.0), c_drupe_exo, 10, 14,
                               vertices, colors, groups["Esquizocarpo_Drupa_Azul"])
                _add_ellipsoid(d2_ctr + np.array([0.0, 0.0, -1.2]), (2.6, 1.9, 1.8), c_pyrene, 6, 8,
                               vertices, colors, groups["Pirenos_Endocarpo_Lenoso"], rugose_amp=0.10)

        # --- B. BRACTEAS EN ANTESIS (k = 2..8): CINCINOS Y FLORES TUBULARES ---
        if 2 <= k <= 8:
            cinc_origin = node_pt + 13.0 * e_l + 2.0 * e_u
            ov_ctr = node_pt + 24.0 * e_l - 1.5 * e_u

            # Pedicelo viloso principal + bracteola floral membranosa
            ped_fl = np.array([cinc_origin, 0.5 * (cinc_origin + ov_ctr), ov_ctr - 3.0 * e_l])
            _add_closed_tube(ped_fl, np.array([1.7, 1.5, 1.6]), np.tile(c_pedicel, (3, 1)),
                             8, vertices, colors, groups["Pedicelos_Bracteolas_Cincino"])

            # 3 botones florales en desarrollo empacados dentro de la cavidad
            for b_i, (bl, bu, bz, blen) in enumerate([
                (17.0, 6.5, -3.6, 20.0),
                (20.0, 3.8, -5.2, 24.0),
                (22.0, 5.2, 3.6, 21.0),
            ]):
                b_p0 = node_pt + bl * e_l + bu * e_u + bz * e_z
                b_p1 = b_p0 + (blen * 0.55) * e_l - 2.5 * e_u
                b_p2 = b_p0 + blen * e_l - 7.5 * e_u
                _add_closed_tube(
                    np.array([b_p0, b_p1, b_p2]),
                    np.array([2.2, 2.6, 0.7]),
                    np.array([c_bracteole, c_per_yel * 0.95, c_per_grn]),
                    8, vertices, colors, groups["Pedicelos_Bracteolas_Cincino"]
                )

            # Ovario infero trilocular (8 x 4.8 mm) con 3 ovulos internos visibles en corte z = 0
            ov_rot = math.radians(-side * (droop_deg + 14.0))
            _add_ellipsoid(ov_ctr, (4.4, 2.7, 2.7), c_ovary_grn, 9, 12,
                           vertices, colors, groups["Ovario_Infero_Estilo"], rot_z=ov_rot)
            _add_ellipsoid(ov_ctr, (3.4, 2.0, 2.0), c_ovary_in, 7, 10,
                           vertices, colors, groups["Ovario_Infero_Estilo"], rot_z=ov_rot, inner_invert=True)

            for ov_off in [(-1.2, 0.5, -0.7), (0.2, -0.6, -0.8), (1.3, 0.3, -0.7)]:
                ov_p = ov_ctr + ov_off[0] * e_l + ov_off[1] * e_u + ov_off[2] * e_z
                _add_ellipsoid(ov_p, (0.95, 0.62, 0.62), c_ovule_crm, 6, 8,
                               vertices, colors, groups["Ovario_Infero_Estilo"])

            # Flor abierta (44 mm): tubo basal + perianto fusionado superior + 1 sepalo libre inferior
            fl_len = 44.0 * (1.0 - 0.14 * frac)
            fl_start = ov_ctr + 3.8 * e_l - 0.8 * e_u
            n_fl = 16
            t_fl = np.linspace(0.0, 1.0, n_fl)

            # Eje curvo suave del perianto asomando hacia abajo del bote
            fl_axis = np.array([
                fl_start + (t * fl_len) * e_l - (2.5 * t + 14.0 * (t ** 2.1)) * e_u
                for t in t_fl
            ])
            fl_r = 2.65 * (0.92 + 0.20 * np.sin(math.pi * t_fl)) * (1.0 - 0.55 * (t_fl ** 2.6))
            fl_cols = []
            for t in t_fl:
                if t < 0.22:
                    c = c_per_base
                elif t < 0.80:
                    m = float(_smoothstep(0.22, 0.45, t))
                    c = (1.0 - m) * c_per_base + m * c_per_yel
                else:
                    m = float(_smoothstep(0.80, 0.98, t))
                    c = (1.0 - m) * c_per_yel + m * c_per_grn
                fl_cols.append(c)
            fl_cols = np.array(fl_cols)

            # Tubo/capucha perigonial (2 sepalos ventrales + 3 petalos)
            _add_closed_tube(fl_axis, fl_r, fl_cols, 12, vertices, colors,
                             groups["Perianto_Tubo_Sepalo_Libre"], rx_scale=1.0, ry_scale=0.85)

            # 1 Sepalo dorsal libre (se separa del tubo a los 9 mm y se curva hacia abajo)
            n_sep = 12
            t_sep = np.linspace(0.0, 1.0, n_sep)
            sep_start = fl_axis[3] - 1.2 * e_u
            sep_pts = np.array([
                sep_start + (t * fl_len * 0.78) * e_l - (6.0 * t + 20.0 * (t ** 1.8)) * e_u - 0.4 * e_z
                for t in t_sep
            ])
            sep_r = 1.65 * (1.0 - 0.72 * (t_sep ** 1.8))
            sep_cols = np.array([
                (1.0 - float(_smoothstep(0.65, 1.0, t))) * c_per_yel + float(_smoothstep(0.65, 1.0, t)) * c_per_grn
                for t in t_sep
            ])
            _add_closed_tube(sep_pts, sep_r, sep_cols, 8, vertices, colors,
                             groups["Perianto_Tubo_Sepalo_Libre"], rx_scale=0.55, ry_scale=1.2)

            # Segunda flor emergiendo ligeramente desplazada (solo en bracteas centrales k=3..6)
            if 3 <= k <= 6:
                fl2_axis = np.array([
                    fl_start - 2.5 * e_u - 4.2 * e_z + (t * fl_len * 0.88) * e_l - (5.0 * t + 16.0 * (t ** 2.0)) * e_u
                    for t in t_fl
                ])
                _add_closed_tube(fl2_axis, fl_r * 0.82, fl_cols, 10, vertices, colors,
                                 groups["Perianto_Tubo_Sepalo_Libre"])

            # 5 Estambres fertiles (filamentos + anteras lineales de 11 mm)
            stamen_zs = [-1.5, -0.9, -0.3, 0.3, 0.9]
            for s_idx, sz in enumerate(stamen_zs):
                y_off = (s_idx - 2) * 0.45
                st_pts = np.array([
                    fl_start + (t * fl_len * 0.78) * e_l
                    - (1.8 * t + 11.2 * (t ** 2.0) - y_off) * e_u + sz * e_z
                    for t in np.linspace(0.05, 1.0, 9)
                ])
                _add_closed_tube(st_pts[:7], np.full(7, 0.36), np.tile(c_filament, (7, 1)),
                                 6, vertices, colors, groups["Androceo_5_Estambres"])
                _add_closed_tube(st_pts[6:], np.array([0.62, 0.68, 0.48]),
                                 np.tile(c_anther, (3, 1)), 6, vertices, colors,
                                 groups["Androceo_5_Estambres"])

            # 1 Estaminodio diagnostico blanco espatulado/oblanceolado (14.5 x 4.2 mm)
            st_base = fl_start + 3.5 * e_l + 1.4 * e_u - 0.5 * e_z
            t_sm = np.linspace(0.0, 1.0, 8)
            sm_pts = np.array([
                st_base + (t * 14.5) * e_l + (1.2 * math.sin(math.pi * t) - 1.4 * t) * e_u
                for t in t_sm
            ])
            sm_rad = np.array([0.85 + 1.45 * math.sin(math.pi * (t ** 0.75)) for t in t_sm])
            _add_closed_tube(sm_pts, sm_rad, np.tile(c_staminode, (8, 1)), 8,
                             vertices, colors, groups["Estaminodio_Diagnostico"],
                             rx_scale=1.1, ry_scale=0.38)

            # Estilo delgado y estigma capitado saliendo del apice del ovario
            sty_pts = np.array([
                ov_ctr + 3.2 * e_l + (t * fl_len * 0.84) * e_l
                - (2.0 * t + 12.2 * (t ** 2.05)) * e_u - 0.4 * e_z
                for t in np.linspace(0.0, 1.0, 10)
            ])
            _add_closed_tube(sty_pts, np.linspace(0.55, 0.42, 10), np.tile(c_style, (10, 1)),
                             6, vertices, colors, groups["Ovario_Infero_Estilo"])
            _add_ellipsoid(sty_pts[-1], (0.85, 0.75, 0.75), c_style, 5, 8,
                           vertices, colors, groups["Ovario_Infero_Estilo"])

    # Bractea apical terminal colgante
    _build_terminal_bract(term_pt, 66.0, vertices, colors, groups["Bracteas_Cincinales_Cimbiformes"])

    # =========================================================================
    # ENSAMBLAJE DEL OBJ CON VERTEX COLORS Y 11 GRUPOS ANATOMICOS
    # =========================================================================
    lines = []
    for v, c in zip(vertices, colors):
        lines.append(f"v {v[0]:.4f} {v[1]:.4f} {v[2]:.4f} {c[0]:.4f} {c[1]:.4f} {c[2]:.4f}" + NL)

    for grp_name, grp_faces in groups.items():
        if not grp_faces:
            continue
        lines.append(f"g {grp_name}" + NL)
        for f_idx in grp_faces:
            lines.append(f"f {f_idx[0]} {f_idx[1]} {f_idx[2]}" + NL)

    return "".join(lines)


build_heliconiaceae_inflorescence = build_heliconiaceae_flower
