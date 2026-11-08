import yaml
import sys
import os
import math
import json
import numpy as np

NL = chr(10)

def load_config(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def build_vertex(x, y, z):
    return f"v {x:.4f} {y:.4f} {z:.4f}" + NL

def build_face(v1, v2, v3):
    return f"f {v1} {v2} {v3}" + NL

def hex_to_rgb(hex_color):
    hex_color = str(hex_color).strip().lstrip('#')
    if len(hex_color) != 6:
        return (0.5, 0.5, 0.5)
    try:
        return tuple(int(hex_color[i:i+2], 16) / 255.0 for i in (0, 2, 4))
    except ValueError:
        return (0.5, 0.5, 0.5)

def np_hex_to_rgb(hex_str):
    hex_str = str(hex_str).strip().lstrip('#')
    return np.array([int(hex_str[i:i+2], 16) / 255.0 for i in (0, 2, 4)])

def create_material_mtl(cfg, mtl_filepath):
    perianto = cfg.get('perianto') or {}
    androceo = cfg.get('androceo') or {}
    gineceo = cfg.get('gineceo') or {}
    caliz = perianto.get('caliz') or {}
    corola = perianto.get('corola') or {}

    colors = {
        "Mat_Caliz": hex_to_rgb(caliz.get('color_hex', '#5A8F32')),
        "Mat_CorolaGarganta": hex_to_rgb(corola.get('color_garganta_hex', '#4A1238')),
        "Mat_CorolaLimbo": hex_to_rgb(corola.get('color_limbo_hex', '#9F7CBF')),
        "Mat_Filamento": hex_to_rgb(androceo.get('color_filamento_hex', '#D4DCB8')),
        "Mat_Antera": hex_to_rgb(androceo.get('color_antera_hex', '#D2CA4E')),
        "Mat_Ovario": hex_to_rgb(gineceo.get('color_ovario_hex', '#8DB84A')),
        "Mat_Estilo": hex_to_rgb(gineceo.get('color_estilo_hex', '#D4DCB8')),
        "Mat_CoronaVioleta": hex_to_rgb("#7A4FA0"),
        "Mat_Blanco": (0.95, 0.95, 0.98),
        # Colores para Orchidaceae (Cattleya)
        "Mat_PetaloLila": hex_to_rgb("#D8B8E8"),
        "Mat_LabeloPurpura": hex_to_rgb("#9E1256"),
        "Mat_LabeloAmarillo": hex_to_rgb("#FFB703"),
        "Mat_Columna": hex_to_rgb("#F8F5F2")
    }
    with open(mtl_filepath, 'w', encoding='utf-8') as f:
        f.write("# Materiales generados automaticamente" + NL)
        for mat_name, rgb in colors.items():
            f.write(NL + f"newmtl {mat_name}" + NL)
            f.write(f"Kd {rgb[0]:.4f} {rgb[1]:.4f} {rgb[2]:.4f}" + NL)
            f.write("Ka 0.2 0.2 0.2" + NL + "Ks 0.15 0.15 0.15" + NL + "Ns 12" + NL)
    return {k: '#' + ''.join(f'{int(c*255):02x}' for c in v) for k, v in colors.items()}

def add_tube_along_curve(curve_pts, radii, colors_ring, n_slices, vertices, colors, faces):
    n_rings = len(curve_pts)
    base_idx = len(vertices)
    theta_vals = np.linspace(0, 2 * np.pi, n_slices, endpoint=False)

    for i in range(n_rings):
        p = curve_pts[i]
        if i < n_rings - 1:
            tang = curve_pts[i + 1] - p
        else:
            tang = p - curve_pts[i - 1]
        norm_t = np.linalg.norm(tang)
        tang = tang / (norm_t if norm_t > 1e-6 else 1.0)

        ref = np.array([0.0, 0.0, 1.0]) if abs(tang[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
        n1 = np.cross(tang, ref)
        n1 /= np.linalg.norm(n1)
        n2 = np.cross(tang, n1)

        for j, th in enumerate(theta_vals):
            r = radii[i, j] if radii.ndim == 2 else radii[i]
            pt = p + r * (np.cos(th) * n1 + np.sin(th) * n2)
            vertices.append(pt.tolist())
            c = colors_ring[i, j] if colors_ring.ndim == 3 else colors_ring[i]
            colors.append(c.tolist())

    for i in range(n_rings - 1):
        for j in range(n_slices):
            j_next = (j + 1) % n_slices
            p1 = base_idx + i * n_slices + j + 1
            p2 = base_idx + i * n_slices + j_next + 1
            p3 = base_idx + (i + 1) * n_slices + j_next + 1
            p4 = base_idx + (i + 1) * n_slices + j + 1
            faces.append((p1, p2, p3))
            faces.append((p1, p3, p4))

def add_tube(pts, r0, r1, sides, v_offset):
    out = []
    n = len(pts)
    for i, (x, y, z) in enumerate(pts):
        t = i / max(1, n - 1)
        r = r0 * (1 - t) + r1 * t
        if i < n - 1:
            dx, dy, dz = pts[i+1][0] - x, pts[i+1][1] - y, pts[i+1][2] - z
        else:
            dx, dy, dz = x - pts[i-1][0], y - pts[i-1][1], z - pts[i-1][2]
        length = math.sqrt(dx*dx + dy*dy + dz*dz) or 1.0
        tx, ty, tz = dx/length, dy/length, dz/length
        ux, uy, uz = (0, 1, 0) if abs(ty) < 0.9 else (1, 0, 0)
        nx, ny, nz = ty*uz - tz*uy, tz*ux - tx*uz, tx*uy - ty*ux
        nl = math.sqrt(nx*nx + ny*ny + nz*nz) or 1.0
        nx, ny, nz = nx/nl, ny/nl, nz/nl
        bx, by, bz = ty*nz - tz*ny, tz*nx - tx*nz, tx*ny - ty*nx
        for s in range(sides):
            ang = 2 * math.pi * s / sides
            ca, sa = math.cos(ang), math.sin(ang)
            out.append(build_vertex(x + r*(ca*nx + sa*bx), y + r*(ca*ny + sa*by), z + r*(ca*nz + sa*bz)))
    for i in range(n - 1):
        for s in range(sides):
            p1 = v_offset + i*sides + s
            p2 = v_offset + i*sides + (s + 1) % sides
            p3 = v_offset + (i + 1)*sides + s
            p4 = v_offset + (i + 1)*sides + (s + 1) % sides
            out.append(build_face(p1, p2, p3))
            out.append(build_face(p2, p4, p3))
    return "".join(out), v_offset + n * sides

def build_sanjorgense_original_obj(cfg):
    c_cfg = cfg['perianto']['corola']
    a_cfg = cfg.get('androceo', {})
    g_cfg = cfg.get('gineceo', {})

    spathe_len = float(c_cfg.get('longitud_limbo_mm', 65.0))
    acumen_len = float(c_cfg.get('longitud_tubo_mm', 15.0))
    total_spathe = spathe_len + acumen_len
    spathe_w = float(c_cfg.get('ancho_petalo_mm', 38.0)) * 0.55

    c_wine = np_hex_to_rgb(c_cfg.get('color_garganta_hex', '#8A1822'))
    c_dark_wine = c_wine * 0.65
    c_green = np_hex_to_rgb(c_cfg.get('color_limbo_hex', '#7A9F2E'))
    c_stipe = np_hex_to_rgb(a_cfg.get('color_filamento_hex', '#C85242'))
    c_spadix = np_hex_to_rgb(g_cfg.get('color_estilo_hex', '#B8D844'))
    c_spadix_tip = np_hex_to_rgb(g_cfg.get('color_apice_hex', '#D49442'))
    c_peduncle = np_hex_to_rgb(cfg['perianto']['caliz'].get('color_hex', '#8C7D38'))

    vertices, colors, faces = [], [], []

    n_v, n_u = 95, 55
    v_vals = np.linspace(0.0, 1.0, n_v)
    u_vals = np.linspace(-1.0, 1.0, n_u)
    body_frac = spathe_len / total_spathe
    base_idx = len(vertices)

    for v in v_vals:
        if v <= body_frac:
            tv = v / body_frac
            w_profile = np.sin(np.pi * (tv ** 0.68))
            depth_profile = np.sin(np.pi * (tv ** 0.8)) * (spathe_w * 0.72)
        else:
            ta = (v - body_frac) / (1.0 - body_frac)
            w_profile = (1.0 - ta) ** 2.2 * 0.18
            depth_profile = (1.0 - ta) * 2.5

        y_spine = v * total_spathe * 0.78
        z_arch = np.sin(v * np.pi * 0.72) * 22.0 - (v ** 3) * 8.0

        for u in u_vals:
            x = u * spathe_w * w_profile
            hood_curve = (1.0 - (u ** 2)) * depth_profile
            y = y_spine + (u ** 2) * 2.5
            z = z_arch - hood_curve

            mottle = (
                0.09 * np.sin(38.0 * v + 17.0 * u) * np.cos(27.0 * v - 21.0 * u)
                + 0.05 * np.sin(75.0 * v + 43.0 * u)
            )
            trans_center = 0.44 + 0.08 * (1.0 - u ** 2)
            mix = np.clip((v - trans_center + mottle) / 0.16, 0.0, 1.0)

            base_col = (1.0 - min(v * 2.5, 1.0)) * c_dark_wine + min(v * 2.5, 1.0) * c_wine
            edge_green = np.clip((abs(u) - 0.78) / 0.22, 0.0, 1.0) * 0.55
            mix_final = np.clip(mix + edge_green, 0.0, 1.0)
            col = (1.0 - mix_final) * base_col + mix_final * c_green

            vertices.append([x, y, z])
            colors.append(col.tolist())

    for i in range(n_v - 1):
        for j in range(n_u - 1):
            p1 = base_idx + i * n_u + j + 1
            p2 = base_idx + i * n_u + (j + 1) + 1
            p3 = base_idx + (i + 1) * n_u + (j + 1) + 1
            p4 = base_idx + (i + 1) * n_u + j + 1
            faces.append((p1, p2, p3))
            faces.append((p1, p3, p4))

    stipe_len = float(a_cfg.get('filamento_longitud_mm', 14.0))
    stipe_r = float(a_cfg.get('filamento_grosor_mm', 2.2))
    n_st = 20
    t_st = np.linspace(0, 1, n_st)
    stipe_pts = np.column_stack([
        np.zeros(n_st),
        3.0 - t_st * 6.5,
        -2.0 + np.sin(t_st * np.pi * 0.5) * stipe_len
    ])
    stipe_radii = np.linspace(stipe_r * 1.1, stipe_r * 0.95, n_st)
    stipe_cols = np.tile(c_stipe, (n_st, 1))
    add_tube_along_curve(stipe_pts, stipe_radii, stipe_cols, 24, vertices, colors, faces)

    spadix_len = float(g_cfg.get('estilo_longitud_mm', 70.0))
    spadix_r_base = float(g_cfg.get('estilo_grosor_mm', g_cfg.get('diametro_espadice_mm', 9.5))) / 2.0
    n_sp = 90
    n_sl = 44
    s_vals = np.linspace(0, 1, n_sp)
    start_sp = stipe_pts[-1]

    spadix_pts = np.column_stack([
        np.zeros(n_sp),
        start_sp[1] - s_vals * spadix_len,
        start_sp[2] + np.sin(s_vals * np.pi) * 2.2
    ])

    radii_sp = np.zeros((n_sp, n_sl))
    cols_sp = np.zeros((n_sp, n_sl, 3))
    theta_sp = np.linspace(0, 2 * np.pi, n_sl, endpoint=False)

    for i, s in enumerate(s_vals):
        taper = (1.0 - 0.38 * (s / 0.93)) if s < 0.93 else 0.62 * np.sqrt(max(1.0 - (s - 0.93) / 0.07, 0.02))
        r_mean = spadix_r_base * taper
        tip_mix = np.clip((s - 0.80) / 0.20, 0.0, 1.0)
        c_ring = (1.0 - tip_mix) * c_spadix + tip_mix * c_spadix_tip

        for j, th in enumerate(theta_sp):
            bump = (np.cos(13 * th + (i % 2) * 1.5) * np.sin(55 * s * np.pi)) ** 2
            radii_sp[i, j] = r_mean + (0.48 * bump if s < 0.96 else 0.1)
            cols_sp[i, j] = c_ring * (0.90 + 0.16 * bump)

    add_tube_along_curve(spadix_pts, radii_sp, cols_sp, n_sl, vertices, colors, faces)

    n_ped = 30
    t_ped = np.linspace(0, 1, n_ped)
    ped_pts = np.column_stack([
        np.zeros(n_ped),
        3.0 - t_ped * 85.0,
        -2.0 - np.sin(t_ped * np.pi * 0.5) * 14.0
    ])
    ped_radii = np.linspace(2.6, 3.1, n_ped)
    ped_cols = np.tile(c_peduncle, (n_ped, 1))
    add_tube_along_curve(ped_pts, ped_radii, ped_cols, 20, vertices, colors, faces)

    lines = []
    for v, c in zip(vertices, colors):
        lines.append(f"v {v[0]:.4f} {v[1]:.4f} {v[2]:.4f} {c[0]:.4f} {c[1]:.4f} {c[2]:.4f}" + NL)
    for f_idx in faces:
        lines.append(f"f {f_idx[0]} {f_idx[1]} {f_idx[2]}" + NL)
    return "".join(lines)

def build_andraeanum_obj(cfg):
    c_cfg = cfg['perianto']['corola']
    g_cfg = cfg.get('gineceo', {})

    spathe_len = float(c_cfg.get('longitud_limbo_mm', 90.0))
    spathe_w = float(c_cfg.get('ancho_petalo_mm', 85.0))

    c_red = np_hex_to_rgb(c_cfg.get('color_limbo_hex', '#D81122'))
    c_dark_red = np_hex_to_rgb(c_cfg.get('color_garganta_hex', '#8A0A18'))
    c_spadix = np_hex_to_rgb(g_cfg.get('color_estilo_hex', '#F5DC70'))
    c_spadix_tip = np_hex_to_rgb(g_cfg.get('color_apice_hex', '#E8B828'))
    c_peduncle = np_hex_to_rgb(cfg['perianto']['caliz'].get('color_hex', '#3B7322'))

    vertices, colors, faces = [], [], []
    base_idx = 0

    n_v, n_u = 80, 80
    v_vals = np.linspace(-0.25, 1.0, n_v)
    u_vals = np.linspace(-1.0, 1.0, n_u)

    for v in v_vals:
        if v < 0:
            w_profile = np.sqrt(max(0.001, 1.0 - (v / -0.25) ** 2)) * 0.85
            y_spine = v * 18.0
        else:
            w_profile = (1.0 - v) ** 0.65 * (1.0 + 0.48 * np.sin(v * np.pi))
            y_spine = v * spathe_len

        z_arch = -np.sin(max(0.0, v) * np.pi) * 14.0

        for u in u_vals:
            x = u * w_profile * (spathe_w / 2.0)
            y = y_spine
            depth = (abs(u) ** 1.3) * 5.5
            z = z_arch + depth

            if v < 0.16 and abs(u) < 0.32:
                cleft = (0.32 - abs(u)) * (0.16 - v) * 45.0
                y -= cleft
                z -= cleft * 0.35

            veins = 1.4 * np.sin(10 * np.pi * abs(u)) * np.cos(4 * np.pi * v)
            bullate = 0.85 * np.sin(36 * np.pi * u) * np.sin(34 * np.pi * v)
            z += veins + bullate

            mix = np.clip((abs(u) + v) / 1.8, 0.0, 1.0)
            base_col = (1.0 - mix) * c_dark_red + mix * c_red
            highlight = np.clip(bullate * 0.45, 0.0, 0.25)
            col = np.clip(base_col + highlight, 0.0, 1.0)

            vertices.append([x, y, z])
            colors.append(col.tolist())

    for i in range(n_v - 1):
        for j in range(n_u - 1):
            p1 = base_idx + i * n_u + j + 1
            p2 = base_idx + i * n_u + (j + 1) + 1
            p3 = base_idx + (i + 1) * n_u + (j + 1) + 1
            p4 = base_idx + (i + 1) * n_u + j + 1
            faces.append((p1, p2, p3))
            faces.append((p1, p3, p4))

    spadix_len = float(g_cfg.get('estilo_longitud_mm', 68.0))
    spadix_r_base = float(g_cfg.get('estilo_grosor_mm', g_cfg.get('diametro_espadice_mm', 8.5))) / 2.0
    n_sp = 65
    n_sl = 36
    s_vals = np.linspace(0, 1, n_sp)

    spadix_pts = np.column_stack([
        np.zeros(n_sp),
        s_vals * spadix_len + 1.5,
        -np.sin(s_vals * np.pi * 0.5) * 6.5
    ])

    radii_sp = np.zeros((n_sp, n_sl))
    cols_sp = np.zeros((n_sp, n_sl, 3))
    theta_sp = np.linspace(0, 2 * np.pi, n_sl, endpoint=False)

    for i, s in enumerate(s_vals):
        taper = 1.0 - 0.22 * s
        r_mean = spadix_r_base * taper
        tip_mix = np.clip(s * 1.3, 0.0, 1.0)
        c_ring = (1.0 - tip_mix) * c_spadix + tip_mix * c_spadix_tip

        for j, th in enumerate(theta_sp):
            parastichy = np.cos(14 * th + 26 * s * np.pi) * np.sin(26 * th - 14 * s * np.pi)
            bump = 0.24 * parastichy
            radii_sp[i, j] = r_mean + bump
            cols_sp[i, j] = np.clip(c_ring * (0.92 + 0.22 * bump), 0.0, 1.0)

    add_tube_along_curve(spadix_pts, radii_sp, cols_sp, n_sl, vertices, colors, faces)

    n_ped = 20
    t_ped = np.linspace(0, 1, n_ped)
    ped_pts = np.column_stack([
        np.zeros(n_ped),
        -t_ped * 80.0,
        np.zeros(n_ped)
    ])
    ped_radii = np.linspace(2.5, 3.2, n_ped)
    ped_cols = np.tile(c_peduncle, (n_ped, 1))
    add_tube_along_curve(ped_pts, ped_radii, ped_cols, 16, vertices, colors, faces)

    lines = []
    for v, c in zip(vertices, colors):
        lines.append(f"v {v[0]:.4f} {v[1]:.4f} {v[2]:.4f} {c[0]:.4f} {c[1]:.4f} {c[2]:.4f}" + NL)
    for f_idx in faces:
        lines.append(f"f {f_idx[0]} {f_idx[1]} {f_idx[2]}" + NL)
    return "".join(lines)

def build_araceae_inflorescence(cfg):
    especie = cfg.get('colecta', {}).get('especie', '').lower()
    disposicion = cfg.get('arquitectura_floral', {}).get('disposicion', 'erecta').lower()

    if "sanjorgense" in especie or disposicion == "pendula":
        return build_sanjorgense_original_obj(cfg)
    else:
        return build_andraeanum_obj(cfg)

def build_passiflora_flower(cfg):
    obj_data = ""
    v_offset = 1
    is_incarnata = "incarnata" in cfg['colecta']['especie'].lower()

    corola = cfg.get('perianto', {}).get('corola', {})
    l_petal = float(corola.get('longitud_limbo_mm', 42.0))
    w_petal = float(corola.get('ancho_petalo_mm', 18.0))
    l_sepal = l_petal * 1.04

    obj_data += "usemtl Mat_Caliz" + NL
    ped_pts = [
        (0.0, -38.0, -8.0),
        (0.0, -30.0, -7.0),
        (0.0, -22.0, -5.0),
        (0.0, -15.0, -2.5),
        (0.0, -9.0, 0.0)
    ]
    seg_ped, v_offset = add_tube(ped_pts, 1.8, 2.2, 12, v_offset)
    obj_data += seg_ped

    n_cup_rings, sides_cup = 8, 20
    for i in range(n_cup_rings):
        t = i / (n_cup_rings - 1)
        y_c = -9.0 + t * 9.0
        r_c = 2.2 + 5.8 * math.sin(t * math.pi * 0.5)
        for s in range(sides_cup):
            ang = s * (2.0 * math.pi / sides_cup)
            rib = 1.0 + 0.05 * math.cos(10 * ang)
            px = r_c * rib * math.cos(ang)
            pz = r_c * rib * math.sin(ang)
            obj_data += build_vertex(px, y_c, pz)

    for i in range(n_cup_rings - 1):
        for s in range(sides_cup):
            p1 = v_offset + i * sides_cup + s
            p2 = v_offset + i * sides_cup + (s + 1) % sides_cup
            p3 = v_offset + (i + 1) * sides_cup + s
            p4 = v_offset + (i + 1) * sides_cup + (s + 1) % sides_cup
            obj_data += build_face(p1, p2, p3)
            obj_data += build_face(p2, p4, p3)
    v_offset += n_cup_rings * sides_cup

    obj_data += "usemtl Mat_CorolaLimbo" + NL
    ru, rv = 16, 8

    for whorl in ['sepal', 'petal']:
        length = l_sepal if whorl == 'sepal' else l_petal
        width = w_petal * (1.05 if whorl == 'sepal' else 0.95)
        offset_angle = 0.0 if whorl == 'sepal' else (math.pi / 5.0)
        y_layer = -0.8 if whorl == 'sepal' else 0.0

        for k in range(5):
            base_ang = k * (2.0 * math.pi / 5.0) + offset_angle
            ca, sa = math.cos(base_ang), math.sin(base_ang)

            for i in range(ru + 1):
                u = i / ru
                r = 7.5 + length * u

                if u < 0.18:
                    w_profile = (u / 0.18) ** 0.55
                elif u < 0.82:
                    w_profile = 1.0
                else:
                    t_tip = (u - 0.82) / 0.18
                    w_profile = math.sqrt(max(0.001, 1.0 - t_tip * t_tip))

                w_local = (width / 2.0) * w_profile
                arch_y = y_layer + 3.8 * math.sin(math.pi * u * 0.6) - 16.0 * (u ** 2.2)

                for j in range(rv + 1):
                    v = (j / rv) - 0.5
                    lat = v * 2.0 * w_local
                    cup = -1.4 * (v * v) * (1.0 - u * 0.3)

                    px = r * ca - lat * sa
                    pz = r * sa + lat * ca
                    py = arch_y + cup

                    if whorl == 'sepal' and 0.80 < u < 0.94 and abs(v) < 0.18:
                        py += 2.2 * math.sin((u - 0.80) / 0.14 * math.pi)

                    obj_data += build_vertex(px, py, pz)

            for i in range(ru):
                for j in range(rv):
                    p1 = v_offset + i * (rv + 1) + j
                    p2 = p1 + 1
                    p3 = p1 + (rv + 1)
                    p4 = p3 + 1
                    obj_data += build_face(p1, p2, p3)
                    obj_data += build_face(p2, p4, p3)
            v_offset += (ru + 1) * (rv + 1)

    l_filam = float(corola.get('longitud_tubo_mm', 36.0))
    series_radii = [7.2, 6.4, 5.6]
    series_counts = [72, 72, 48] if is_incarnata else [64, 48, 36]

    for s_idx, (r_start, num_fil) in enumerate(zip(series_radii, series_counts)):
        scale_len = 1.0 - (s_idx * 0.14)
        for i in range(num_fil):
            angle = i * (2.0 * math.pi / num_fil) + (s_idx * 0.05)
            pts_dark, pts_white, pts_tip = [], [], []
            steps = 18

            for j in range(steps):
                u = j / (steps - 1)
                d_theta, d_y = 0.0, 0.0
                if is_incarnata and u > 0.32:
                    d_theta = 0.26 * ((u - 0.32) ** 1.2) * math.sin(12.0 * math.pi * u + (i % 7) * 1.1)
                    d_y = 3.6 * ((u - 0.32) ** 1.5) * math.cos(9.0 * math.pi * u + (i % 5) * 0.8)

                elev = 1.8 * math.sin(u * math.pi) + d_y - 2.5 * (u ** 2)
                r_ext = r_start + l_filam * scale_len * u
                ang = angle + d_theta
                pt = (r_ext * math.cos(ang), 0.6 + elev, r_ext * math.sin(ang))

                if u <= 0.30:
                    pts_dark.append(pt)
                if 0.26 <= u <= 0.58:
                    pts_white.append(pt)
                if u >= 0.54:
                    pts_tip.append(pt)

            obj_data += "usemtl Mat_CorolaGarganta" + NL
            seg1, v_offset = add_tube(pts_dark, 0.46, 0.36, 4, v_offset)
            obj_data += seg1

            obj_data += "usemtl Mat_Blanco" + NL
            seg2, v_offset = add_tube(pts_white, 0.36, 0.28, 4, v_offset)
            obj_data += seg2

            obj_data += "usemtl Mat_CoronaVioleta" + NL
            seg3, v_offset = add_tube(pts_tip, 0.28, 0.10, 4, v_offset)
            obj_data += seg3

    obj_data += "usemtl Mat_CorolaGarganta" + NL
    for i in range(48):
        ang = i * (2.0 * math.pi / 48.0)
        pts_op = [
            (4.8 * math.cos(ang), 0.6, 4.8 * math.sin(ang)),
            (5.6 * math.cos(ang), 3.2, 5.6 * math.sin(ang)),
            (5.0 * math.cos(ang), 5.5, 5.0 * math.sin(ang))
        ]
        seg_op, v_offset = add_tube(pts_op, 0.38, 0.14, 4, v_offset)
        obj_data += seg_op

    androceo = cfg.get('androceo') or {}
    gineceo = cfg.get('gineceo') or {}
    l_androg = float(androceo.get('filamento_longitud_mm', 22.0))
    w_androg = float(androceo.get('filamento_grosor_mm', 2.2)) / 2.0

    obj_data += "usemtl Mat_Estilo" + NL
    col_pts = [(0, i * (l_androg / 10.0), 0) for i in range(11)]
    seg_col, v_offset = add_tube(col_pts, w_androg * 1.1, w_androg * 0.92, 12, v_offset)
    obj_data += seg_col

    l_antera = float(androceo.get('antera_longitud_mm', 8.0))
    for i in range(5):
        a = i * (2.0 * math.pi / 5.0)
        ca, sa = math.cos(a), math.sin(a)
        arm_pts = [
            (0, l_androg, 0),
            (4.0 * ca, l_androg + 1.2, 4.0 * sa),
            (8.5 * ca, l_androg - 1.5, 8.5 * sa)
        ]
        obj_data += "usemtl Mat_Filamento" + NL
        seg_arm, v_offset = add_tube(arm_pts, 0.72, 0.48, 6, v_offset)
        obj_data += seg_arm

        tx, tz = -sa, ca
        ant_pts = [
            (8.5 * ca - (l_antera / 2.0) * tx, l_androg - 2.4, 8.5 * sa - (l_antera / 2.0) * tz),
            (8.5 * ca, l_androg - 2.0, 8.5 * sa),
            (8.5 * ca + (l_antera / 2.0) * tx, l_androg - 2.4, 8.5 * sa + (l_antera / 2.0) * tz)
        ]
        obj_data += "usemtl Mat_Antera" + NL
        seg_ant, v_offset = add_tube(ant_pts, 1.45, 1.45, 8, v_offset)
        obj_data += seg_ant

    obj_data += "usemtl Mat_Ovario" + NL
    ov_r = 3.2 if is_incarnata else 2.5
    ov_pts = [
        (0, l_androg, 0),
        (0, l_androg + ov_r * 0.5, 0),
        (0, l_androg + ov_r, 0),
        (0, l_androg + ov_r * 1.5, 0),
        (0, l_androg + ov_r * 1.8, 0)
    ]
    seg_ov, v_offset = add_tube(ov_pts, ov_r * 0.65, 0.4, 16, v_offset)
    obj_data += seg_ov

    l_estilo = float(gineceo.get('estilo_longitud_mm', 9.5))
    for i in range(3):
        a = i * (2.0 * math.pi / 3.0) + math.pi / 6.0
        ca, sa = math.cos(a), math.sin(a)
        st_pts = [
            (0, l_androg + ov_r * 1.7, 0),
            (l_estilo * 0.4 * ca, l_androg + ov_r * 1.9 + 2.0, l_estilo * 0.4 * sa),
            (l_estilo * 0.8 * ca, l_androg + ov_r * 1.9 + 0.5, l_estilo * 0.8 * sa),
            (l_estilo * 1.1 * ca, l_androg + ov_r * 1.9 - 2.5, l_estilo * 1.1 * sa)
        ]
        obj_data += "usemtl Mat_Estilo" + NL
        seg_st, v_offset = add_tube(st_pts, 0.75, 1.15, 8, v_offset)
        obj_data += seg_st

        stig_pts = [
            (l_estilo * 1.1 * ca - 1.4 * sa, l_androg + ov_r * 1.9 - 2.8, l_estilo * 1.1 * sa + 1.4 * ca),
            (l_estilo * 1.1 * ca + 1.4 * sa, l_androg + ov_r * 1.9 - 2.8, l_estilo * 1.1 * sa - 1.4 * ca)
        ]
        obj_data += "usemtl Mat_Ovario" + NL
        seg_sg, v_offset = add_tube(stig_pts, 1.8, 1.8, 10, v_offset)
        obj_data += seg_sg

    return obj_data

def build_asteraceae_capitulum(cfg):
    obj_data = ""
    v_offset = 1
    caliz_cfg = cfg.get('perianto', {}).get('caliz') or {}
    corola_cfg = cfg.get('perianto', {}).get('corola') or {}
    scale = 0.62
    r_disco = 47.5 * scale
    n_filarias = int(caliz_cfg.get('sepalos_numero', 48))
    l_filaria = float(caliz_cfg.get('longitud_tubo_mm', 28.0)) * scale
    n_ligulas = int(corola_cfg.get('petalos_numero', 42))
    l_tubo_lig = float(corola_cfg.get('longitud_tubo_mm', 5.5)) * scale
    l_ligula = float(corola_cfg.get('longitud_limbo_mm', 72.0)) * scale
    w_ligula = float(corola_cfg.get('ancho_petalo_mm', 21.0)) * scale

    tilt_rad = math.radians(34.0)
    ct, st = math.cos(tilt_rad), math.sin(tilt_rad)
    def orient_pt(x, y, z):
        return (x, y * ct - z * st, y * st + z * ct)

    obj_data += "usemtl Mat_Caliz" + NL
    n_ped_rings, sides_ped = 16, 18
    for i in range(n_ped_rings):
        t = i / (n_ped_rings - 1)
        py = -85.0 * (1.0 - t) - 4.5 * t
        pz = -22.0 * ((1.0 - t) ** 1.8)
        r_ring = 4.8 + 18.5 * (t ** 3.0)
        for s in range(sides_ped):
            ang = s * (2.0 * math.pi / sides_ped)
            rib_mod = 1.0 + 0.06 * math.cos(ang * 9.0) + 0.02 * math.sin(ang * 18.0)
            tx, ty, tz = orient_pt(r_ring * rib_mod * math.cos(ang), py, r_ring * rib_mod * math.sin(ang) + pz)
            obj_data += build_vertex(tx, ty, tz)
    for i in range(n_ped_rings - 1):
        for s in range(sides_ped):
            p1 = v_offset + i * sides_ped + s
            p2 = v_offset + i * sides_ped + (s + 1) % sides_ped
            p3 = v_offset + (i + 1) * sides_ped + s
            p4 = v_offset + (i + 1) * sides_ped + (s + 1) % sides_ped
            obj_data += build_face(p1, p2, p3)
            obj_data += build_face(p2, p4, p3)
    v_offset += n_ped_rings * sides_ped

    ru_f, rv_f = 9, 5
    for k in range(n_filarias):
        whorl = k % 3
        ang = k * (2.0 * math.pi / n_filarias) + (whorl * 0.18) + (math.sin(k * 2.1) * 0.04)
        ca, sa = math.cos(ang), math.sin(ang)
        if whorl == 0:
            r_ins, y_ins, l_bract, w_bract, recurve = r_disco * 0.72, -6.0, l_filaria * 1.15, 5.2, 9.0
        elif whorl == 1:
            r_ins, y_ins, l_bract, w_bract, recurve = r_disco * 0.86, -3.8, l_filaria * 0.95, 4.8, 3.2
        else:
            r_ins, y_ins, l_bract, w_bract, recurve = r_disco * 0.98, -1.6, l_filaria * 0.78, 4.2, -1.5
        for i in range(ru_f + 1):
            u = i / ru_f
            r_curr = r_ins + l_bract * u
            w_loc = w_bract * math.sin(math.pi * (u ** 0.58)) * (1.0 - 0.75 * u)
            y_curr = y_ins + 2.5 * math.sin(u * math.pi * 0.6) - recurve * (u ** 2.2)
            for j in range(rv_f + 1):
                v = (j / rv_f) - 0.5
                lat = v * 2.0 * w_loc
                cup = -1.1 * (v * v) * (1.0 - u * 0.5)
                tx, ty, tz = orient_pt(r_curr * ca - lat * sa, y_curr + cup, r_curr * sa + lat * ca)
                obj_data += build_vertex(tx, ty, tz)
        for i in range(ru_f):
            for j in range(rv_f):
                p1 = v_offset + i * (rv_f + 1) + j
                p2 = p1 + 1
                p3 = p1 + (rv_f + 1)
                p4 = p3 + 1
                obj_data += build_face(p1, p2, p3)
                obj_data += build_face(p2, p4, p3)
        v_offset += (ru_f + 1) * (rv_f + 1)

    obj_data += "usemtl Mat_Ovario" + NL
    ru_d, rv_d = 12, 32
    for i in range(ru_d + 1):
        u = i / ru_d
        r_curr = r_disco * u
        y_curr = 4.8 * (1.0 - (u ** 2.2))
        for j in range(rv_d + 1):
            ang = j * (2.0 * math.pi / rv_d)
            tx, ty, tz = orient_pt(r_curr * math.cos(ang), y_curr, r_curr * math.sin(ang))
            obj_data += build_vertex(tx, ty, tz)
    for i in range(ru_d):
        for j in range(rv_d):
            p1 = v_offset + i * (rv_d + 1) + j
            p2 = p1 + 1
            p3 = p1 + (rv_d + 1)
            p4 = p3 + 1
            obj_data += build_face(p1, p2, p3)
            obj_data += build_face(p2, p4, p3)
    v_offset += (ru_d + 1) * (rv_d + 1)

    ru_l, rv_l = 14, 6
    for k in range(n_ligulas):
        layer = k % 3
        base_ang = k * (2.0 * math.pi / n_ligulas) + math.sin(k * 3.7) * 0.038 + math.cos(k * 1.9) * 0.02
        ca, sa = math.cos(base_ang), math.sin(base_ang)
        if layer == 0:
            y_base, r_base, l_len, w_local_scale, tilt_pitch, curl_amp = -1.2 + math.sin(k * 1.3) * 0.4, r_disco * 0.96, l_ligula * 1.05, w_ligula * 0.98, -0.16 + math.sin(k * 2.3) * 0.06, -5.8
        elif layer == 1:
            y_base, r_base, l_len, w_local_scale, tilt_pitch, curl_amp = 0.6 + math.cos(k * 2.1) * 0.4, r_disco * 0.98, l_ligula * 1.0, w_ligula * 1.04, 0.02 + math.sin(k * 3.1) * 0.05, -2.2
        else:
            y_base, r_base, l_len, w_local_scale, tilt_pitch, curl_amp = 2.4 + math.sin(k * 2.7) * 0.5, r_disco * 0.92, l_ligula * 0.88, w_ligula * 0.92, 0.22 + math.cos(k * 1.7) * 0.08, 3.6

        obj_data += "usemtl Mat_CorolaGarganta" + NL
        tub_pts = [orient_pt((r_base - 1.2) * ca, y_base, (r_base - 1.2) * sa), orient_pt((r_base + l_tubo_lig) * ca, y_base + 1.2, (r_base + l_tubo_lig) * sa)]
        seg_t, v_offset = add_tube(tub_pts, 1.1, 1.45, 5, v_offset)
        obj_data += seg_t

        obj_data += "usemtl Mat_CorolaLimbo" + NL
        twist_k = math.sin(k * 2.7 + layer) * 0.18
        for i in range(ru_l + 1):
            u = i / ru_l
            r_curr = r_base + l_tubo_lig * 0.8 + l_len * u
            w_curr = (w_local_scale / 2.0) * math.sin(math.pi * (u ** 0.62)) * (1.0 - 0.22 * (u ** 2.2))
            arch_long = y_base + 1.2 + (tilt_pitch * l_len * u) + 3.8 * math.sin(math.pi * u) + curl_amp * (u ** 2.4)
            for j in range(rv_l + 1):
                v = (j / rv_l) - 0.5
                lat = v * 2.0 * w_curr
                vein_ruffle = 0.55 * math.cos(v * math.pi * 3.0) * math.sin(math.pi * (u ** 0.7)) - 0.95 * (v * v) + (v * twist_k * 4.2 * u)
                tx, ty, tz = orient_pt(r_curr * ca - lat * sa, arch_long + vein_ruffle, r_curr * sa + lat * ca)
                obj_data += build_vertex(tx, ty, tz)
        for i in range(ru_l):
            for j in range(rv_l):
                p1 = v_offset + i * (rv_l + 1) + j
                p2 = p1 + 1
                p3 = p1 + (rv_l + 1)
                p4 = p3 + 1
                obj_data += build_face(p1, p2, p3)
                obj_data += build_face(p2, p4, p3)
        v_offset += (ru_l + 1) * (rv_l + 1)

    n_total_flosculos = 520
    golden_angle = math.radians(137.50776)
    c_vogel = (r_disco * 0.93) / math.sqrt(n_total_flosculos)
    flosculos_centro, flosculos_periferia_tubo, flosculos_periferia_antera, flosculos_periferia_estilo = [], [], [], []

    for n in range(1, n_total_flosculos + 1):
        theta_n = n * golden_angle
        r_n = c_vogel * math.sqrt(n)
        frac = r_n / r_disco
        px, pz = r_n * math.cos(theta_n), r_n * math.sin(theta_n)
        py_base = 4.8 * (1.0 - (frac ** 2.2))
        if frac < 0.46:
            flosculos_centro.append([orient_pt(px, py_base, pz), orient_pt(px, py_base + 3.2, pz)])
        else:
            twist_stg = 1.025 if (n % 2 == 0) else 0.975
            flosculos_periferia_tubo.append([orient_pt(px, py_base, pz), orient_pt(px, py_base + 3.1, pz)])
            flosculos_periferia_antera.append([orient_pt(px, py_base + 3.0, pz), orient_pt(px, py_base + 5.3, pz)])
            flosculos_periferia_estilo.append([orient_pt(px, py_base + 5.0, pz), orient_pt(px * twist_stg, py_base + 6.6, pz * twist_stg)])

    obj_data += "usemtl Mat_Antera" + NL
    for pts_f in flosculos_centro:
        seg_f, v_offset = add_tube(pts_f, 0.78, 0.42, 5, v_offset)
        obj_data += seg_f
    obj_data += "usemtl Mat_CorolaGarganta" + NL
    for pts_cor in flosculos_periferia_tubo:
        seg_c, v_offset = add_tube(pts_cor, 0.72, 0.94, 5, v_offset)
        obj_data += seg_c
    obj_data += "usemtl Mat_Filamento" + NL
    for pts_ant in flosculos_periferia_antera:
        seg_a, v_offset = add_tube(pts_ant, 0.52, 0.46, 5, v_offset)
        obj_data += seg_a
    obj_data += "usemtl Mat_Estilo" + NL
    for pts_est in flosculos_periferia_estilo:
        seg_e, v_offset = add_tube(pts_est, 0.42, 0.78, 4, v_offset)
        obj_data += seg_e
    return obj_data

def build_orchidaceae_flower(cfg):
    """
    Modelo morfométrico de Cattleya trianae (Orchidaceae):
    - 3 sépalos lanceolados (1 dorsal erecto y 2 laterales subfalcados descendentes).
    - 2 pétalos romboidales anchos con ondulaciones y fimbrias marginales.
    - 1 labelo trilobulado convoluto (tubo envolvente y limbo frontal emarginado).
    - Tricolor en el labelo: amarillo oro en garganta, magenta-púrpura central y lila exterior.
    - Columna semicilíndrica arqueada y ovario pedicelado 6-acanalado.
    """
    c_cfg = cfg['perianto']['corola']
    a_cfg = cfg.get('androceo', {})
    g_cfg = cfg.get('gineceo', {})

    l_petal = float(c_cfg.get('longitud_limbo_mm', 85.0))
    w_petal = float(c_cfg.get('ancho_petalo_mm', 60.0))
    l_sepal = l_petal * 0.98
    w_sepal = w_petal * 0.36

    l_lip = float(c_cfg.get('longitud_tubo_mm', 72.0))
    w_lip = float(c_cfg.get('ancho_labelo_mm', 52.0))

    c_lilac = np_hex_to_rgb(cfg['perianto']['caliz'].get('color_hex', '#D8B8E8'))
    c_yellow = np_hex_to_rgb(c_cfg.get('color_garganta_hex', '#FFB703'))
    c_purple = np_hex_to_rgb(c_cfg.get('color_limbo_hex', '#9E1256'))
    c_column = np_hex_to_rgb(a_cfg.get('color_filamento_hex', '#F8F5F2'))
    c_ovary = np_hex_to_rgb(g_cfg.get('color_ovario_hex', '#5A8A34'))

    vertices, colors, faces = [], [], []
    base_idx = 0

    # 1. Ovario pedicelado ínfero (6-acanalado y curvado hacia atrás)
    n_ped, sides_ped = 16, 6
    t_ped = np.linspace(0.0, 1.0, n_ped)
    ped_pts = np.column_stack([
        np.zeros(n_ped),
        -t_ped * 28.0,
        -t_ped * 45.0 + 5.0 * np.sin(t_ped * np.pi)
    ])
    add_tube_along_curve(ped_pts, np.linspace(2.8, 3.6, n_ped), np.tile(c_ovary, (n_ped, 1)), sides_ped, vertices, colors, faces)
    base_idx = len(vertices)

    # 2. Sépalos (3: Dorsal a 90°, Laterales a -32° y -148°)
    sepal_angles = [np.pi / 2.0, -np.pi * 0.18, -np.pi * 0.82]
    ru_s, rv_s = 18, 8
    u_vals_s = np.linspace(0.0, 1.0, ru_s + 1)
    v_vals_s = np.linspace(-0.5, 0.5, rv_s + 1)

    for base_ang in sepal_angles:
        ca, sa = np.cos(base_ang), np.sin(base_ang)
        for u in u_vals_s:
            r = 3.0 + l_sepal * u
            w_loc = (w_sepal / 2.0) * np.sin(np.pi * (u ** 0.72)) * (1.0 - 0.22 * u)
            arch_z = -4.5 * (u ** 1.8) + 1.2 * np.sin(np.pi * u)

            for v in v_vals_s:
                lat = v * 2.0 * w_loc
                px = r * ca - lat * sa
                py = r * sa + lat * ca
                pz = arch_z - 1.4 * (v * v)
                vertices.append([px, py, pz])
                colors.append(c_lilac.tolist())

        for i in range(ru_s):
            for j in range(rv_s):
                p1 = base_idx + i * (rv_s + 1) + j + 1
                p2 = base_idx + i * (rv_s + 1) + (j + 1) + 1
                p3 = base_idx + (i + 1) * (rv_s + 1) + (j + 1) + 1
                p4 = base_idx + (i + 1) * (rv_s + 1) + j + 1
                faces.append((p1, p2, p3))
                faces.append((p1, p3, p4))
        base_idx = len(vertices)

    # 3. Pétalos laterales romboidales ondulados
    petal_angles = [np.radians(14.0), np.radians(166.0)]
    ru_p, rv_p = 22, 14
    u_vals_p = np.linspace(0.0, 1.0, ru_p + 1)
    v_vals_p = np.linspace(-0.5, 0.5, rv_p + 1)

    for base_ang in petal_angles:
        ca, sa = np.cos(base_ang), np.sin(base_ang)
        is_left = base_ang > np.pi / 2.0

        for u in u_vals_p:
            r = 4.0 + l_petal * u
            w_loc = (w_petal / 2.0) * np.sin(np.pi * (u ** 0.62))
            arch_z = 7.0 * np.sin(np.pi * u) - 10.0 * (u ** 2.2)

            for v in v_vals_p:
                lat = v * 2.0 * w_loc
                edge_factor = (abs(v) / 0.5) ** 1.8
                ruffle = 4.2 * edge_factor * math.sin(7.5 * np.pi * u + (2.0 if is_left else 0.0))

                px = r * ca - lat * sa
                py = r * sa + lat * ca
                pz = arch_z + ruffle - 2.8 * (v * v)

                center_glow = 1.0 - 0.15 * (abs(v) / 0.5)
                col_petal = np.clip(c_lilac * center_glow, 0.0, 1.0)

                vertices.append([px, py, pz])
                colors.append(col_petal.tolist())

        for i in range(ru_p):
            for j in range(rv_p):
                p1 = base_idx + i * (rv_p + 1) + j + 1
                p2 = base_idx + i * (rv_p + 1) + (j + 1) + 1
                p3 = base_idx + (i + 1) * (rv_p + 1) + (j + 1) + 1
                p4 = base_idx + (i + 1) * (rv_p + 1) + j + 1
                faces.append((p1, p2, p3))
                faces.append((p1, p3, p4))
        base_idx = len(vertices)

    # 4. Labelo trilobulado tricolor
    ru_l, rv_l = 32, 22
    u_vals_l = np.linspace(0.0, 1.0, ru_l + 1)
    v_vals_l = np.linspace(-0.5, 0.5, rv_l + 1)

    for u in u_vals_l:
        y_center = -u * l_lip * 0.78
        z_center = 2.5 + u * 24.0 - 18.0 * (u ** 1.9)

        tube_radius = 5.2 + 8.5 * u
        lip_width = w_lip * np.sin(np.pi * (u ** 0.75)) if u > 0.42 else tube_radius * np.pi

        for v in v_vals_l:
            if u < 0.42:
                theta = v * np.pi * 1.82
                px = tube_radius * np.sin(theta)
                py = y_center - tube_radius * 0.48 * (1.0 - np.cos(theta))
                pz = z_center + tube_radius * np.cos(theta)
                col = c_yellow if abs(v) < 0.3 else c_lilac
            else:
                t_flare = (u - 0.42) / 0.58
                lat = v * 2.0 * lip_width
                edge_factor = (abs(v) / 0.5) ** 1.6
                ruffle = 5.2 * edge_factor * math.sin(11.0 * math.pi * t_flare + v * 14.0)

                notch = 0.0
                if abs(v) < 0.16 and u > 0.82:
                    notch = -6.0 * (u - 0.82) / 0.18 * (1.0 - abs(v) / 0.16)

                px = lat
                py = y_center + ruffle + notch - 7.5 * (v * v)
                pz = z_center + ruffle * 0.4

                radial = math.sqrt((lat / (w_lip * 0.5)) ** 2 + ((u - 0.48) / 0.52) ** 2)
                if radial < 0.38:
                    col = c_yellow
                elif radial < 0.78:
                    mix_p = (radial - 0.38) / 0.40
                    col = (1.0 - mix_p) * c_yellow + mix_p * c_purple
                else:
                    mix_l = min(1.0, (radial - 0.78) / 0.22)
                    col = (1.0 - mix_l) * c_purple + mix_l * c_lilac

            vertices.append([px, py, pz])
            colors.append(col.tolist())

    for i in range(ru_l):
        for j in range(rv_l):
            p1 = base_idx + i * (rv_l + 1) + j + 1
            p2 = base_idx + i * (rv_l + 1) + (j + 1) + 1
            p3 = base_idx + (i + 1) * (rv_l + 1) + (j + 1) + 1
            p4 = base_idx + (i + 1) * (rv_l + 1) + j + 1
            faces.append((p1, p2, p3))
            faces.append((p1, p3, p4))
        base_idx = len(vertices)

    # 5. Ginostemio (columna arqueada con antera terminal)
    l_col = float(a_cfg.get('filamento_longitud_mm', 32.0))
    n_col = 16
    t_col = np.linspace(0.0, 1.0, n_col)
    col_pts = np.column_stack([
        np.zeros(n_col),
        -t_col * l_col * 0.72,
        3.5 + t_col * 15.0 - 5.0 * (t_col ** 2)
    ])
    add_tube_along_curve(col_pts, np.linspace(3.6, 2.6, n_col), np.tile(c_column, (n_col, 1)), 10, vertices, colors, faces)

    ant_pt = col_pts[-1]
    ant_pts = np.array([
        ant_pt,
        [ant_pt[0], ant_pt[1] - 2.8, ant_pt[2] + 0.8]
    ])
    c_anther = np_hex_to_rgb(a_cfg.get('color_antera_hex', '#F4D03F'))
    add_tube_along_curve(ant_pts, np.array([2.4, 1.2]), np.tile(c_anther, (2, 1)), 8, vertices, colors, faces)

    lines = []
    for v, c in zip(vertices, colors):
        lines.append(f"v {v[0]:.4f} {v[1]:.4f} {v[2]:.4f} {c[0]:.4f} {c[1]:.4f} {c[2]:.4f}" + NL)
    for f_idx in faces:
        lines.append(f"f {f_idx[0]} {f_idx[1]} {f_idx[2]}" + NL)

    return "".join(lines)

def build_heliconiaceae_inflorescence(cfg):
    """
    Modelo morfométrico de Heliconia rostrata (Inflorescencia en tirso péndulo):
    - Raquis flexuoso (en zigzag) central rojo carmín.
    - 14 brácteas cimbiformes dísticas alternas (en forma de barca o quilla profunda).
    - Patrón tricolor: base rojo escarlata -> margen amarillo canario -> ápice verde esmeralda.
    """
    c_cfg = cfg['perianto']['corola']
    a_cfg = cfg.get('androceo', {})

    bract_len = float(c_cfg.get('longitud_limbo_mm', 120.0))
    bract_depth = float(c_cfg.get('longitud_tubo_mm', 60.0))
    bract_w = float(c_cfg.get('ancho_petalo_mm', 45.0))
    num_bracts = int(c_cfg.get('petalos_numero', 14))

    c_red = np_hex_to_rgb(c_cfg.get('color_garganta_hex', '#E6192B'))
    c_yellow = np_hex_to_rgb(c_cfg.get('color_limbo_hex', '#FFD700'))
    c_green = np_hex_to_rgb(a_cfg.get('color_filamento_hex', '#008B45'))
    c_rachis = np_hex_to_rgb(cfg['perianto']['caliz'].get('color_hex', '#B00020'))

    vertices, colors, faces = [], [], []
    base_idx = 0

    # 1. Raquis flexuoso central (en zigzag)
    n_rachis = num_bracts * 10
    rachis_pts = np.zeros((n_rachis, 3))
    for i in range(n_rachis):
        t = i / float(n_rachis - 1)
        y = -t * (num_bracts * 42.0)
        x = 12.0 * math.sin(t * num_bracts * math.pi)
        rachis_pts[i] = [x, y, 0.0]

    add_tube_along_curve(rachis_pts, np.linspace(5.5, 2.8, n_rachis), np.tile(c_rachis, (n_rachis, 1)), 16, vertices, colors, faces)
    base_idx = len(vertices)

    # 2. Brácteas cimbiformes dísticas
    ru, rv = 24, 16
    u_vals = np.linspace(0.0, 1.0, ru + 1)
    v_vals = np.linspace(-0.5, 0.5, rv + 1)

    for b in range(num_bracts):
        is_right = b % 2 == 0
        sign = 1.0 if is_right else -1.0

        t_node = (b + 0.5) / float(num_bracts)
        y_node = -t_node * (num_bracts * 42.0)
        x_node = 12.0 * math.sin(t_node * num_bracts * math.pi)

        tilt = math.radians(24.0)
        ct, st = math.cos(tilt), math.sin(tilt)

        for u in u_vals:
            l_curr = bract_len * u
            w_curr = bract_w * 0.5 * math.sin(math.pi * (u ** 0.6))
            depth = bract_depth * (1.0 - u) * math.sin(math.pi * u)
            arch = -42.0 * (u ** 2.4)

            for v in v_vals:
                lat = v * 2.0 * w_curr
                cup = -depth * (1.0 - (abs(v) / 0.5) ** 1.5)

                lx = lat
                ly = arch + cup
                lz = l_curr

                rx = (ly * ct - lz * st) * sign
                ry = ly * st + lz * ct
                rz = lx

                px = x_node + rx
                py = y_node + ry
                pz = rz

                if u < 0.65:
                    col = c_red
                elif u < 0.85:
                    mix = (u - 0.65) / 0.20
                    col = (1.0 - mix) * c_red + mix * c_yellow
                else:
                    mix = min((u - 0.85) / 0.15, 1.0)
                    col = (1.0 - mix) * c_yellow + mix * c_green

                vertices.append([px, py, pz])
                colors.append(col.tolist())

        for i in range(ru):
            for j in range(rv):
                p1 = base_idx + i * (rv + 1) + j + 1
                p2 = base_idx + i * (rv + 1) + (j + 1) + 1
                p3 = base_idx + (i + 1) * (rv + 1) + (j + 1) + 1
                p4 = base_idx + (i + 1) * (rv + 1) + j + 1
                faces.append((p1, p2, p3))
                faces.append((p1, p3, p4))
        base_idx = len(vertices)

    lines = []
    for v, c in zip(vertices, colors):
        lines.append(f"v {v[0]:.4f} {v[1]:.4f} {v[2]:.4f} {c[0]:.4f} {c[1]:.4f} {c[2]:.4f}" + NL)
    for f_idx in faces:
        lines.append(f"f {f_idx[0]} {f_idx[1]} {f_idx[2]}" + NL)

    return "".join(lines)

def export_interactive_viewer_html(cfg, obj_data, color_map, html_filepath):
    sp_name = cfg['colecta'].get('especie', 'Flor Desconocida')
    fam = cfg['colecta'].get('familia', 'Indeterminada')
    id_m = cfg['colecta'].get('id_muestra', 'COL-000')
    loc = cfg['colecta'].get('localidad', 'Colombia')
    fecha = cfg['colecta'].get('fecha', 'N/A')

    foto_campo = cfg['colecta'].get('foto_campo', '')
    if foto_campo and not foto_campo.startswith('../') and not foto_campo.startswith(('http://', 'https://')):
        foto_campo = '../' + foto_campo.lstrip('/')

    html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Visor 3D - {sp_name}</title>
    <style>
        html, body {{ width: 100vw; height: 100vh; margin: 0; padding: 0; overflow: hidden; background-color: #0f1218; background-image: radial-gradient(circle at center, #1e2430 0%, #0f1218 100%); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
        .hud-panel {{ position: absolute; top: 18px; left: 18px; background: rgba(15, 20, 28, 0.88); color: #e2e8f0; padding: 16px 20px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.1); z-index: 10; font-size: 0.88rem; line-height: 1.6; backdrop-filter: blur(8px); max-width: 320px; }}
        .hud-panel h2 {{ margin: 0 0 8px 0; font-style: italic; color: #58a6ff; font-size: 1.35rem; }}
        .hud-hint {{ color: #58a6ff; font-size: 0.78rem; margin-top: 8px; }}
        .photo-panel {{
            position: absolute; bottom: 20px; right: 20px;
            width: 210px; background: rgba(15, 20, 28, 0.92);
            border: 2px solid #58a6ff; border-radius: 10px;
            overflow: hidden; z-index: 10; box-shadow: 0 8px 24px rgba(0,0,0,0.6);
            transform-origin: bottom right;
            transition: transform 0.3s cubic-bezier(0.25, 0.8, 0.25, 1), box-shadow 0.3s ease, border-color 0.3s ease;
            cursor: pointer;
        }}
        .photo-panel:hover {{
            transform: scale(1.4);
            border-color: #79c0ff;
            box-shadow: 0 16px 36px rgba(0,0,0,0.85), 0 0 16px rgba(88, 166, 255, 0.35);
        }}
        .photo-panel img {{ width: 100%; height: 165px; object-fit: cover; display: block; }}
        .photo-label {{ background: #161b22; color: #cbd5e0; text-align: center; font-size: 0.72rem; font-weight: 700; letter-spacing: 1px; padding: 7px 0; text-transform: uppercase; }}
        .back-btn {{ position: absolute; bottom: 20px; left: 20px; background: #238636; color: #ffffff; text-decoration: none; padding: 10px 18px; border-radius: 6px; font-size: 0.85rem; font-weight: 600; z-index: 10; display: inline-flex; align-items: center; gap: 6px; box-shadow: 0 4px 12px rgba(0,0,0,0.4); transition: background 0.2s; }}
        .back-btn:hover {{ background: #2ea043; }}
    </style>
</head>
<body>
    <div class="hud-panel">
        <h2>{sp_name}</h2>
        <div><strong>Familia:</strong> {fam}</div>
        <div><strong>Muestra:</strong> {id_m}</div>
        <div><strong>Localidad:</strong> {loc}</div>
        <div><strong>Fecha:</strong> {fecha}</div>
        <div class="hud-hint">• Rotar: Clic izquierdo | Zoom: Rueda | Mover: Clic derecho</div>
    </div>
    <a href="../index.html" class="back-btn">⬅ Volver al catálogo</a>
    <div class="photo-panel">
        <img src="{foto_campo}" alt="{sp_name}" onerror="this.parentElement.style.display='none';">
        <div class="photo-label">REGISTRO DE CAMPO</div>
    </div>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
    <script>
        const objRaw = {json.dumps(obj_data)};
        const palette = {json.dumps(color_map)};
        const scene = new THREE.Scene();
        const camera = new THREE.PerspectiveCamera(42, window.innerWidth / window.innerHeight, 0.1, 3000);
        const renderer = new THREE.WebGLRenderer({{ antialias: true, alpha: true }});
        renderer.setSize(window.innerWidth, window.innerHeight);
        renderer.setPixelRatio(window.devicePixelRatio);
        document.body.appendChild(renderer.domElement);
        const controls = new THREE.OrbitControls(camera, renderer.domElement);
        controls.enableDamping = true;
        controls.dampingFactor = 0.06;
        scene.add(new THREE.AmbientLight(0xffffff, 0.75));
        const dirLight1 = new THREE.DirectionalLight(0xfff8e7, 0.78);
        dirLight1.position.set(60, 80, 90);
        scene.add(dirLight1);
        const dirLight2 = new THREE.DirectionalLight(0x88bbff, 0.38);
        dirLight2.position.set(-60, -40, -60);
        scene.add(dirLight2);

        const vertices = [];
        const vColors = [];
        const vcPositions = [];
        const vcColors = [];
        const groups = {{}};
        let currentMat = "Mat_CorolaLimbo";
        const NL_CHAR = String.fromCharCode(10);

        objRaw.split(NL_CHAR).forEach(line => {{
            const parts = line.trim().split(' ').filter(Boolean);
            if (!parts.length) return;
            if (parts[0] === 'v') {{
                vertices.push([parseFloat(parts[1]), parseFloat(parts[2]), parseFloat(parts[3])]);
                if (parts.length >= 7) {{
                    vColors.push([parseFloat(parts[4]), parseFloat(parts[5]), parseFloat(parts[6])]);
                }} else {{
                    vColors.push(null);
                }}
            }} else if (parts[0] === 'usemtl') {{
                currentMat = parts[1];
                if (!groups[currentMat]) groups[currentMat] = [];
            }} else if (parts[0] === 'f') {{
                const idx = parts.slice(1).map(p => parseInt(p.split('/')[0], 10) - 1);
                if (idx.length >= 3 && vertices[idx[0]] && vertices[idx[1]] && vertices[idx[2]]) {{
                    if (vColors[idx[0]]) {{
                        vcPositions.push(...vertices[idx[0]], ...vertices[idx[1]], ...vertices[idx[2]]);
                        vcColors.push(...vColors[idx[0]], ...vColors[idx[1]], ...vColors[idx[2]]);
                    }} else {{
                        if (!groups[currentMat]) groups[currentMat] = [];
                        groups[currentMat].push(...vertices[idx[0]], ...vertices[idx[1]], ...vertices[idx[2]]);
                    }}
                }}
            }}
        }});

        const flowerGroup = new THREE.Group();
        if (vcPositions.length > 0) {{
            const geom = new THREE.BufferGeometry();
            geom.setAttribute('position', new THREE.Float32BufferAttribute(vcPositions, 3));
            geom.setAttribute('color', new THREE.Float32BufferAttribute(vcColors, 3));
            geom.computeVertexNormals();
            const mat = new THREE.MeshStandardMaterial({{ vertexColors: true, roughness: 0.42, metalness: 0.05, side: THREE.DoubleSide }});
            flowerGroup.add(new THREE.Mesh(geom, mat));
        }}

        Object.keys(groups).forEach(matName => {{
            const pos = groups[matName];
            if (pos.length === 0) return;
            const geom = new THREE.BufferGeometry();
            geom.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
            geom.computeVertexNormals();
            const mat = new THREE.MeshStandardMaterial({{ color: palette[matName] || '#ffffff', roughness: 0.44, metalness: 0.05, side: THREE.DoubleSide }});
            flowerGroup.add(new THREE.Mesh(geom, mat));
        }});

        scene.add(flowerGroup);

        if (vcPositions.length > 0) {{
            const box = new THREE.Box3().setFromObject(flowerGroup);
            const center = box.getCenter(new THREE.Vector3());
            const size = box.getSize(new THREE.Vector3());
            flowerGroup.position.sub(center);
            const maxDim = Math.max(size.x, size.y, size.z) || 100;
            camera.position.set(maxDim * 0.85, maxDim * 0.25, maxDim * 1.15);
            controls.target.set(0, 0, 0);
            controls.update();
        }} else {{
            camera.position.set(0, 75, 145);
            controls.target.set(0, 0, 0);
            controls.update();
        }}

        window.addEventListener('resize', () => {{
            camera.aspect = window.innerWidth / window.innerHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(window.innerWidth, window.innerHeight);
        }});
        function animate() {{ requestAnimationFrame(animate); controls.update(); renderer.render(scene, camera); }}
        animate();
    </script>
</body>
</html>"""
    with open(html_filepath, 'w', encoding='utf-8') as f:
        f.write(html_content)

def generate_flower_3d(cfg):
    specie_filename = cfg['colecta']['especie'].lower().replace(" ", "_")
    os.makedirs('models', exist_ok=True)
    obj_filepath = os.path.join('models', f"{specie_filename}.obj")
    mtl_filepath = os.path.join('models', f"{specie_filename}.mtl")
    html_filepath = os.path.join('models', f"{specie_filename}.html")

    color_map = create_material_mtl(cfg, mtl_filepath)
    familia = cfg['colecta']['familia'].strip()

    if familia == "Araceae":
        obj_data = build_araceae_inflorescence(cfg)
    elif familia == "Asteraceae":
        obj_data = build_asteraceae_capitulum(cfg)
    elif familia == "Orchidaceae":
        obj_data = build_orchidaceae_flower(cfg)
    elif familia == "Heliconiaceae":
        obj_data = build_heliconiaceae_inflorescence(cfg)
    else:
        obj_data = build_passiflora_flower(cfg)

    with open(obj_filepath, 'w', encoding='utf-8') as f:
        f.write(f"mtllib {specie_filename}.mtl" + NL + obj_data)

    export_interactive_viewer_html(cfg, obj_data, color_map, html_filepath)
    print(f"✅ Modelo 3D generado en: {html_filepath}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(1)
    generate_flower_3d(load_config(sys.argv[1]))