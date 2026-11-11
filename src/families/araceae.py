import math
import numpy as np
from geometry import *


def build_sanjorgense_original_obj(cfg):
    """Morfología de Anthurium sanjorgense con anatomía interna completa para disección."""
    c_cfg = cfg['perianto']['corola']
    a_cfg = cfg.get('androceo', {})
    g_cfg = cfg.get('gineceo', {})

    spathe_len = float(c_cfg.get('longitud_limbo_mm', 65.0))
    acumen_len = float(c_cfg.get('longitud_tubo_mm', 15.0))
    total_spathe = spathe_len + acumen_len
    spathe_w = float(c_cfg.get('ancho_petalo_mm', 38.0)) * 0.55

    # 1. Corrección cromática: Colores botánicos exactos sin ruido pseudoaleatorio
    c_wine = np.array([0.54, 0.09, 0.13])  # Rojo vino base
    c_green = np.array([0.47, 0.62, 0.18]) # Verde para bordes y venas
    c_stipe = np_hex_to_rgb(a_cfg.get('color_filamento_hex', '#C85242'))
    c_spadix = np_hex_to_rgb(g_cfg.get('color_estilo_hex', '#B8D844'))
    c_spadix_tip = np_hex_to_rgb(g_cfg.get('color_apice_hex', '#D49442'))
    c_peduncle = np.array([0.29, 0.36, 0.13]) # 5. Verde oliva oscuro (corregido)
    
    # Paleta de anatomía interna
    c_ovary_tissue = np.array([0.85, 0.90, 0.75]) # Matriz ovárica
    c_ovule = np.array([0.98, 0.95, 0.85])        # Óvulos
    c_axis = np.array([0.94, 0.92, 0.82])         # Eje vascular

    vertices, colors = [], []
    groups = {}

    # =========================================================================
    # 1. ESPATA CUCULADA (Forma cóncava rematada en acumen)
    # =========================================================================
    f_spathe = []
    n_v, n_u = 95, 55
    v_vals = np.linspace(0.0, 1.0, n_v)
    u_vals = np.linspace(-1.0, 1.0, n_u)
    base_idx = len(vertices)

    for v in v_vals:
        # Perfil cóncavo basal que se estrecha hacia el acumen distal
        w_profile = math.sin(math.pi * (v ** 0.68)) * (1.0 - (v ** 2))
        depth_profile = 22.0 * (1.0 - v) * (v ** 0.4) 

        y_spine = v * total_spathe * 0.78
        z_arch = np.sin(v * np.pi * 0.72) * 22.0 - (v ** 3) * 8.0

        for u in u_vals:
            x = u * spathe_w * w_profile
            hood_curve = (1.0 - (u ** 2)) * depth_profile
            y = y_spine + (u ** 2) * 2.5
            z = z_arch - hood_curve

            # Coloración paramétrica: Verde en bordes (u) y venas longitudinales (v)
            edge_mask = abs(u) ** 2.5
            vein_mask = 0.18 * math.cos(u * 14.0) * math.sin(v * 4.0 * math.pi)
            green_mix = np.clip(edge_mask + vein_mask, 0.0, 1.0)
            
            col = (1.0 - green_mix) * c_wine + green_mix * c_green

            vertices.append([x, y, z])
            colors.append(col.tolist())

    for i in range(n_v - 1):
        for j in range(n_u - 1):
            p1 = base_idx + i * n_u + j + 1
            p2 = base_idx + i * n_u + (j + 1) + 1
            p3 = base_idx + (i + 1) * n_u + (j + 1) + 1
            p4 = base_idx + (i + 1) * n_u + j + 1
            f_spathe.append((p1, p2, p3))
            f_spathe.append((p1, p3, p4))
    groups["Espata_Cuculada"] = f_spathe

    # =========================================================================
    # 2. ESTÍPITE ARTICULADO (Acortamiento drástico al 20%)
    # =========================================================================
    f_stipe = []
    stipe_len = 3.0  # Acortado para nacer casi desde el receptáculo
    stipe_r = float(a_cfg.get('filamento_grosor_mm', 2.2))
    n_st = 15
    t_st = np.linspace(0, 1, n_st)
    stipe_pts = np.column_stack([
        np.zeros(n_st),
        3.0 - t_st * stipe_len,
        -2.0 + np.sin(t_st * np.pi * 0.5) * (stipe_len * 0.8)
    ])
    stipe_radii = np.linspace(stipe_r * 1.1, stipe_r * 0.95, n_st)
    stipe_cols = np.tile(c_stipe, (n_st, 1))
    add_tube_along_curve(stipe_pts, stipe_radii, stipe_cols, 24, vertices, colors, f_stipe)
    groups["Estipite_Basal"] = f_stipe

    # =========================================================================
    # 3. ESPÁDICE EXTERNO (Proyección orgánica en Z)
    # =========================================================================
    spadix_len = float(g_cfg.get('estilo_longitud_mm', 70.0))
    spadix_r_base = float(g_cfg.get('estilo_grosor_mm', g_cfg.get('diametro_espadice_mm', 9.5))) / 2.0
    n_sp, n_sl = 90, 44
    s_vals = np.linspace(0, 1, n_sp)
    start_sp = stipe_pts[-1]

    # Caída orgánica: seno de baja amplitud en Z
    spadix_pts = np.column_stack([
        np.zeros(n_sp),
        start_sp[1] - s_vals * spadix_len,
        start_sp[2] + np.sin(s_vals * np.pi) * 12.0
    ])

    f_spadix = []
    radii_sp = np.zeros((n_sp, n_sl))
    cols_sp = np.zeros((n_sp, n_sl, 3))
    theta_sp = np.linspace(0, 2 * np.pi, n_sl, endpoint=False)

    for i, s in enumerate(s_vals):
        taper = 1.0 - 0.38 * (s / 0.93) if s < 0.93 else 0.62 * math.sqrt(max(1.0 - (s - 0.93) / 0.07, 0.02))
        r_mean = spadix_r_base * taper
        tip_mix = np.clip((s - 0.80) / 0.20, 0.0, 1.0)
        c_ring = (1.0 - tip_mix) * c_spadix + tip_mix * c_spadix_tip

        for j, th in enumerate(theta_sp):
            bump = (math.cos(13 * th + (i % 2) * 1.5) * math.sin(55 * s * math.pi)) ** 2
            radii_sp[i, j] = r_mean + (0.48 * bump if s < 0.96 else 0.1)
            cols_sp[i, j] = c_ring * (0.90 + 0.16 * bump)

    add_tube_along_curve(spadix_pts, radii_sp, cols_sp, n_sl, vertices, colors, f_spadix)
    groups["Espadice_Florifero"] = f_spadix

    # =========================================================================
    # 4. ANATOMÍA INTERNA (Para Rayos X y Disección)
    # =========================================================================
    
    # 4.A Capa Ovárica (85% del radio)
    f_ovary = []
    ovary_radii = np.zeros((n_sp, n_sl))
    cols_ovary = np.zeros((n_sp, n_sl, 3))
    for i, s in enumerate(s_vals):
        taper = 1.0 - 0.38 * (s / 0.93) if s < 0.93 else 0.62 * math.sqrt(max(1.0 - (s - 0.93) / 0.07, 0.02))
        r_mean = spadix_r_base * taper * 0.85
        for j, th in enumerate(theta_sp):
            locules = math.sin(13 * th) * math.sin(55 * s * math.pi)
            ovary_radii[i, j] = r_mean + (0.15 * locules if s < 0.96 else 0.0)
            cols_ovary[i, j] = c_ovary_tissue * (0.85 + 0.15 * locules)
    add_tube_along_curve(spadix_pts, ovary_radii, cols_ovary, n_sl, vertices, colors, f_ovary)
    groups["Gineceo_Ovarios"] = f_ovary

    # 4.B Capa Seminal / Óvulos (55% del radio)
    f_ovules = []
    ovule_radii = np.zeros((n_sp, n_sl))
    cols_ovules = np.zeros((n_sp, n_sl, 3))
    for i, s in enumerate(s_vals):
        taper = 1.0 - 0.38 * (s / 0.93) if s < 0.93 else 0.62 * math.sqrt(max(1.0 - (s - 0.93) / 0.07, 0.02))
        r_mean = spadix_r_base * taper * 0.55
        for j, th in enumerate(theta_sp):
            primordia = (math.cos(26 * th) * math.cos(110 * s * math.pi)) ** 4
            ovule_radii[i, j] = r_mean + (0.25 * primordia)
            cols_ovules[i, j] = c_ovule * (0.7 + 0.3 * primordia)
    add_tube_along_curve(spadix_pts, ovule_radii, cols_ovules, n_sl, vertices, colors, f_ovules)
    groups["Ovulos_Internos"] = f_ovules

    # 4.C Eje Vascular (Con abultamiento nodal)
    f_axis = []
    axis_radii = np.zeros(n_sp)
    for i, s in enumerate(s_vals):
        taper = 1.0 - 0.38 * (s / 0.93) if s < 0.93 else 0.62 * math.sqrt(max(1.0 - (s - 0.93) / 0.07, 0.02))
        base_r = spadix_r_base * taper * 0.28
        nodal_bulge = 0.15 * math.sin(s * 60 * math.pi)
        axis_radii[i] = base_r + nodal_bulge
    add_tube_along_curve(spadix_pts, axis_radii, np.tile(c_axis, (n_sp, 1)), 12, vertices, colors, f_axis)
    groups["Eje_Vascular_Interno"] = f_axis

    # =========================================================================
    # 5. PEDÚNCULO VERDE OLIVA OSCURO
    # =========================================================================
    f_ped = []
    n_ped = 30
    t_ped = np.linspace(0, 1, n_ped)
    ped_pts = np.column_stack([
        np.zeros(n_ped),
        3.0 - t_ped * 85.0,
        -2.0 - np.sin(t_ped * np.pi * 0.5) * 14.0
    ])
    ped_radii = np.linspace(2.6, 3.1, n_ped)
    ped_cols = np.tile(c_peduncle, (n_ped, 1))
    add_tube_along_curve(ped_pts, ped_radii, ped_cols, 20, vertices, colors, f_ped)
    groups["Pedunculo_Tallo"] = f_ped

    # Ensamblaje OBJ Modular
    lines = []
    for v, c in zip(vertices, colors):
        lines.append(f"v {v[0]:.4f} {v[1]:.4f} {v[2]:.4f} {c[0]:.4f} {c[1]:.4f} {c[2]:.4f}" + NL)
    for grp_name, grp_faces in groups.items():
        lines.append(f"g {grp_name}" + NL)
        for f_idx in grp_faces:
            lines.append(f"f {f_idx[0]} {f_idx[1]} {f_idx[2]}" + NL)
    return "".join(lines)


def build_andraeanum_obj(cfg):
    pass # (Mantén intacta tu función de andraeanum aquí)

def build_araceae_inflorescence(cfg):
    especie = cfg.get('colecta', {}).get('especie', '').lower()
    disposicion = cfg.get('arquitectura_floral', {}).get('disposicion', 'erecta').lower()
    if "sanjorgense" in especie or disposicion == "pendula":
        return build_sanjorgense_original_obj(cfg)
    else:
        return build_andraeanum_obj(cfg)