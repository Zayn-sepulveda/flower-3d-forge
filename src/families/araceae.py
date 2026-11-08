import math
import numpy as np
from geometry import *

def build_sanjorgense_original_obj(cfg):
    """Morfología péndula cuculada de Anthurium sanjorgense (Intacta)."""
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
    n_sp, n_sl = 90, 44
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
    """
    Modelo morfométrico de alta precisión para Anthurium andraeanum:
    - Espata ampliamente cordiforme con aurículas basales redondeadas y seno central profundo.
    - Espata reclinada hacia atrás (~26°) formando un plato cóncavo que cradlea la inflorescencia.
    - Espádice erguido con leve proyección hacia adelante (~14°), eliminando el ángulo perpendicular.
    - Cierre apical sólido del espádice y base del pedúnculo sellada.
    """
    c_cfg = cfg['perianto']['corola']
    g_cfg = cfg.get('gineceo', {})

    spathe_len = float(c_cfg.get('longitud_limbo_mm', 95.0))
    spathe_w = float(c_cfg.get('ancho_petalo_mm', 94.0))

    c_red = np_hex_to_rgb(c_cfg.get('color_limbo_hex', '#E6152B'))
    c_dark_red = np_hex_to_rgb(c_cfg.get('color_garganta_hex', '#8A0A18'))
    c_spadix_base = np_hex_to_rgb(g_cfg.get('color_estilo_hex', '#FFF8DC'))
    c_spadix_tip = np_hex_to_rgb(g_cfg.get('color_apice_hex', '#FFD700'))
    c_peduncle = np_hex_to_rgb(cfg['perianto']['caliz'].get('color_hex', '#2E6E24'))

    vertices, colors, faces = [], [], []

    # 1. Espata cordiforme reclinada hacia atrás (ángulo suave de ~26°)
    n_v, n_u = 90, 90
    u_vals = np.linspace(-1.0, 1.0, n_u)
    v_norm = np.linspace(0.0, 1.0, n_v)
    base_idx_spathe = len(vertices)

    tilt_spathe = math.radians(26.0)
    cos_sp, sin_sp = math.cos(tilt_spathe), math.sin(tilt_spathe)

    for v in v_norm:
        for u in u_vals:
            # Lóbulos basales cordados (aurículas redondeadas a ambos lados del seno central)
            v_base_lobe = -0.34 * (math.sin(math.pi * abs(u)) ** 0.82)
            v_actual = (1.0 - v) * v_base_lobe + v * 1.0

            if v_actual < 0:
                w_lobe = 1.0 - 0.22 * ((v_actual / -0.34) ** 2)
                x_local = u * (spathe_w * 0.5) * w_lobe
            else:
                w_blade = ((1.0 - v_actual) ** 0.58) * (1.0 + 0.44 * math.sin(math.pi * v_actual))
                x_local = u * (spathe_w * 0.5) * w_blade

            y_local = v_actual * spathe_len

            # Concavidad en bandeja/plato con márgenes recurvados sutiles
            z_dish = 7.0 * (u ** 2) * (1.0 - 0.35 * v_actual) - 3.5 * math.sin(math.pi * max(0.0, v_actual))
            
            # Profundización del seno basal donde nace el espádice
            sinus_depth = -4.5 * (1.0 - abs(u)) * math.exp(-((v_actual / 0.16) ** 2)) if v_actual < 0.16 else 0.0

            # Textura ampollada (bullada) y venación radiating
            bullate = 0.85 * math.sin(28.0 * math.pi * u) * math.sin(26.0 * math.pi * (v_actual + 0.34))
            veins = 1.30 * math.sin(9.0 * math.pi * abs(u)) * math.cos(3.2 * math.pi * max(0.0, v_actual))

            z_local = z_dish + sinus_depth + bullate + veins

            # Rotación en el plano Y-Z para reclinar la espata hacia atrás
            px = x_local
            py = y_local * cos_sp - z_local * sin_sp
            pz = -y_local * sin_sp - z_local * cos_sp

            # Gradiente de color rojo carmín céreo
            mix = np.clip((abs(u) + max(0.0, v_actual)) / 1.6, 0.0, 1.0)
            base_col = (1.0 - mix) * c_dark_red + mix * c_red
            highlight = np.clip(bullate * 0.35, 0.0, 0.22)
            col = np.clip(base_col + highlight, 0.0, 1.0)

            vertices.append([px, py, pz])
            colors.append(col.tolist())

    for i in range(n_v - 1):
        for j in range(n_u - 1):
            p1 = base_idx_spathe + i * n_u + j + 1
            p2 = base_idx_spathe + i * n_u + (j + 1) + 1
            p3 = base_idx_spathe + (i + 1) * n_u + (j + 1) + 1
            p4 = base_idx_spathe + (i + 1) * n_u + j + 1
            faces.append((p1, p2, p3))
            faces.append((p1, p3, p4))

    # 2. Espádice erguido con suave inclinación frontal (~14°)
    spadix_len = float(g_cfg.get('estilo_longitud_mm', 74.0))
    spadix_r_base = float(g_cfg.get('estilo_grosor_mm', g_cfg.get('diametro_espadice_mm', 8.5))) / 2.0
    n_sp, n_sl = 70, 36
    s_vals = np.linspace(0.0, 1.0, n_sp)

    pitch_rad = math.radians(14.0)
    cos_p, sin_p = math.cos(pitch_rad), math.sin(pitch_rad)

    spadix_pts = np.column_stack([
        np.zeros(n_sp),
        1.5 + s_vals * (spadix_len * cos_p),
        0.5 + s_vals * (spadix_len * sin_p)
    ])

    base_idx_spadix = len(vertices)
    theta_sp = np.linspace(0, 2 * math.pi, n_sl, endpoint=False)

    for i, s in enumerate(s_vals):
        if s < 0.88:
            taper = 1.0 - 0.22 * s
            r_mean = spadix_r_base * taper
        else:
            t_tip = (s - 0.88) / 0.12
            r_mean = spadix_r_base * (1.0 - 0.22 * 0.88) * math.sqrt(max(0.01, 1.0 - t_tip ** 2))

        tip_mix = np.clip(s * 1.25, 0.0, 1.0)
        c_ring = (1.0 - tip_mix) * c_spadix_base + tip_mix * c_spadix_tip

        center_pt = spadix_pts[i]
        for j, th in enumerate(theta_sp):
            parastichy = math.cos(14 * th + 26 * s * math.pi) * math.sin(26 * th - 14 * s * math.pi)
            bump = 0.22 * parastichy if s < 0.92 else 0.04
            r_curr = r_mean + bump

            px = r_curr * math.cos(th)
            py = center_pt[1] - r_curr * math.sin(th) * sin_p
            pz = center_pt[2] + r_curr * math.sin(th) * cos_p

            c_vertex = np.clip(c_ring * (0.92 + 0.22 * bump), 0.0, 1.0)
            vertices.append([px, py, pz])
            colors.append(c_vertex.tolist())

    for i in range(n_sp - 1):
        for j in range(n_sl):
            p1 = base_idx_spadix + i * n_sl + j + 1
            p2 = base_idx_spadix + i * n_sl + ((j + 1) % n_sl) + 1
            p3 = base_idx_spadix + (i + 1) * n_sl + ((j + 1) % n_sl) + 1
            p4 = base_idx_spadix + (i + 1) * n_sl + j + 1
            faces.append((p1, p2, p3))
            faces.append((p1, p3, p4))

    # Tapa hermética esférica del ápice del espádice
    apex_pt = spadix_pts[-1] + np.array([0.0, 1.2 * cos_p, 1.2 * sin_p])
    vertices.append(apex_pt.tolist())
    colors.append(c_spadix_tip.tolist())
    apex_idx = len(vertices)

    last_ring_sp = base_idx_spadix + (n_sp - 1) * n_sl
    for j in range(n_sl):
        p1 = last_ring_sp + j + 1
        p2 = last_ring_sp + ((j + 1) % n_sl) + 1
        faces.append((p1, p2, apex_idx))

    # 3. Pedúnculo cilíndrico sellado
    n_ped, n_ped_sides = 24, 18
    t_ped = np.linspace(0.0, 1.0, n_ped)
    ped_pts = np.column_stack([
        np.zeros(n_ped),
        1.0 - t_ped * 82.0,
        np.zeros(n_ped)
    ])
    ped_radii = np.linspace(3.4, 3.8, n_ped)

    base_idx_ped = len(vertices)
    theta_ped = np.linspace(0, 2 * math.pi, n_ped_sides, endpoint=False)

    for i in range(n_ped):
        r_p = ped_radii[i]
        y_p = ped_pts[i][1]
        for j in range(n_ped_sides):
            px = r_p * math.cos(theta_ped[j])
            pz = r_p * math.sin(theta_ped[j])
            vertices.append([px, y_p, pz])
            colors.append(c_peduncle.tolist())

    for i in range(n_ped - 1):
        for j in range(n_ped_sides):
            p1 = base_idx_ped + i * n_ped_sides + j + 1
            p2 = base_idx_ped + i * n_ped_sides + ((j + 1) % n_ped_sides) + 1
            p3 = base_idx_ped + (i + 1) * n_ped_sides + ((j + 1) % n_ped_sides) + 1
            p4 = base_idx_ped + (i + 1) * n_ped_sides + j + 1
            faces.append((p1, p2, p3))
            faces.append((p1, p3, p4))

    # Base inferior sellada del pedúnculo
    bottom_center_pt = [0.0, ped_pts[-1][1], 0.0]
    vertices.append(bottom_center_pt)
    colors.append(c_peduncle.tolist())
    bottom_center_idx = len(vertices)

    last_ring_ped = base_idx_ped + (n_ped - 1) * n_ped_sides
    for j in range(n_ped_sides):
        p1 = last_ring_ped + j + 1
        p2 = last_ring_ped + ((j + 1) % n_ped_sides) + 1
        faces.append((p2, p1, bottom_center_idx))

    lines = []
    for v, c in zip(vertices, colors):
        lines.append(f"v {v[0]:.4f} {v[1]:.4f} {v[2]:.4f} {c[0]:.4f} {c[1]:.4f} {c[2]:.4f}" + NL)
    for f_idx in faces:
        lines.append(f"f {f_idx[0]} {f_idx[1]} {f_idx[2]}" + NL)
    return "".join(lines)


def build_araceae_inflorescence(cfg):
    """Enrutador de arquitectura floral para Araceae."""
    especie = cfg.get('colecta', {}).get('especie', '').lower()
    disposicion = cfg.get('arquitectura_floral', {}).get('disposicion', 'erecta').lower()

    if "sanjorgense" in especie or disposicion == "pendula":
        return build_sanjorgense_original_obj(cfg)
    else:
        return build_andraeanum_obj(cfg)