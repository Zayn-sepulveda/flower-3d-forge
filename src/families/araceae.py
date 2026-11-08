import math
import numpy as np
from geometry import *

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

