import math
import numpy as np
from geometry import *


def _add_closed_tube(pts, radii, cols, n_sl, vertices, colors, face_list, cap_start=True, cap_end=True):
    """
    Envuelve add_tube_along_curve añadiendo tapas sólidas (caps) en el inicio y el final
    para evitar cilindros huecos o agujeros apicales en el espádice y el pedúnculo.
    """
    start_v_idx = len(vertices)
    add_tube_along_curve(pts, radii, cols, n_sl, vertices, colors, face_list)
    n_pts = len(pts)

    if cap_start:
        c0 = cols[0] if np.ndim(cols) == 2 else cols[0, 0]
        vertices.append(pts[0].tolist())
        colors.append(np.clip(c0, 0.0, 1.0).tolist())
        center_start = len(vertices)
        for j in range(n_sl):
            p1 = start_v_idx + j + 1
            p2 = start_v_idx + ((j + 1) % n_sl) + 1
            face_list.append((center_start, p2, p1))

    if cap_end:
        c_end = cols[-1] if np.ndim(cols) == 2 else cols[-1, 0]
        vertices.append(pts[-1].tolist())
        colors.append(np.clip(c_end, 0.0, 1.0).tolist())
        center_end = len(vertices)
        last_ring_offset = start_v_idx + (n_pts - 1) * n_sl
        for j in range(n_sl):
            p1 = last_ring_offset + j + 1
            p2 = last_ring_offset + ((j + 1) % n_sl) + 1
            face_list.append((center_end, p1, p2))


def build_sanjorgense_original_obj(cfg):
    """Morfología de Anthurium sanjorgense con anatomía interna completa para disección."""
    c_cfg = cfg['perianto']['corola']
    a_cfg = cfg.get('androceo', {})
    g_cfg = cfg.get('gineceo', {})

    spathe_len = float(c_cfg.get('longitud_limbo_mm', 65.0))
    acumen_len = float(c_cfg.get('longitud_tubo_mm', 15.0))
    total_spathe = spathe_len + acumen_len
    spathe_w = float(c_cfg.get('ancho_petalo_mm', 38.0)) * 0.55

    c_wine = np.array([0.54, 0.09, 0.13])
    c_green = np.array([0.47, 0.62, 0.18])
    c_stipe = np_hex_to_rgb(a_cfg.get('color_filamento_hex', '#C85242'))
    c_spadix = np_hex_to_rgb(g_cfg.get('color_estilo_hex', '#B8D844'))
    c_spadix_tip = np_hex_to_rgb(g_cfg.get('color_apice_hex', '#D49442'))
    c_peduncle = np.array([0.29, 0.36, 0.13])

    c_ovary_tissue = np.array([0.85, 0.90, 0.75])
    c_ovule = np.array([0.98, 0.95, 0.85])
    c_axis = np.array([0.94, 0.92, 0.82])

    vertices, colors = [], []
    groups = {}

    f_spathe = []
    n_v, n_u = 95, 55
    v_vals = np.linspace(0.0, 1.0, n_v)
    u_vals = np.linspace(-1.0, 1.0, n_u)
    base_idx = len(vertices)

    for v in v_vals:
        w_profile = math.sin(math.pi * (v ** 0.68)) * (1.0 - (v ** 2))
        depth_profile = 22.0 * (1.0 - v) * (v ** 0.4)

        y_spine = v * total_spathe * 0.78
        z_arch = np.sin(v * np.pi * 0.72) * 22.0 - (v ** 3) * 8.0

        for u in u_vals:
            x = u * spathe_w * w_profile
            hood_curve = (1.0 - (u ** 2)) * depth_profile
            y = y_spine + (u ** 2) * 2.5
            z = z_arch - hood_curve

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

    f_stipe = []
    stipe_len = 3.0
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
    _add_closed_tube(stipe_pts, stipe_radii, stipe_cols, 24, vertices, colors, f_stipe, cap_start=True, cap_end=True)
    groups["Estipite_Basal"] = f_stipe

    spadix_len = float(g_cfg.get('estilo_longitud_mm', 70.0))
    spadix_r_base = float(g_cfg.get('estilo_grosor_mm', g_cfg.get('diametro_espadice_mm', 9.5))) / 2.0
    n_sp, n_sl = 90, 44
    s_vals = np.linspace(0, 1, n_sp)
    start_sp = stipe_pts[-1]

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
        taper = 1.0 - 0.38 * (s / 0.93) if s < 0.93 else 0.62 * math.sqrt(max(1.0 - (s - 0.93) / 0.07, 0.0))
        r_mean = spadix_r_base * taper
        tip_mix = np.clip((s - 0.80) / 0.20, 0.0, 1.0)
        c_ring = (1.0 - tip_mix) * c_spadix + tip_mix * c_spadix_tip

        for j, th in enumerate(theta_sp):
            bump = (math.cos(13 * th + (i % 2) * 1.5) * math.sin(55 * s * np.pi)) ** 2
            radii_sp[i, j] = r_mean + (0.48 * bump * (1.0 - s) if s < 0.95 else 0.02)
            cols_sp[i, j] = np.clip(c_ring * (0.90 + 0.16 * bump), 0.0, 1.0)

    _add_closed_tube(spadix_pts, radii_sp, cols_sp, n_sl, vertices, colors, f_spadix, cap_start=True, cap_end=True)
    groups["Espadice_Florifero"] = f_spadix

    f_ovary = []
    ovary_radii = np.zeros((n_sp, n_sl))
    cols_ovary = np.zeros((n_sp, n_sl, 3))
    for i, s in enumerate(s_vals):
        taper = 1.0 - 0.38 * (s / 0.93) if s < 0.93 else 0.62 * math.sqrt(max(1.0 - (s - 0.93) / 0.07, 0.0))
        r_mean = spadix_r_base * taper * 0.85
        for j, th in enumerate(theta_sp):
            locules = math.sin(13 * th) * math.sin(55 * s * math.pi)
            ovary_radii[i, j] = r_mean + (0.15 * locules if s < 0.95 else 0.01)
            cols_ovary[i, j] = np.clip(c_ovary_tissue * (0.85 + 0.15 * locules), 0.0, 1.0)
    _add_closed_tube(spadix_pts, ovary_radii, cols_ovary, n_sl, vertices, colors, f_ovary, cap_start=True, cap_end=True)
    groups["Gineceo_Ovarios"] = f_ovary

    f_ovules = []
    ovule_radii = np.zeros((n_sp, n_sl))
    cols_ovules = np.zeros((n_sp, n_sl, 3))
    for i, s in enumerate(s_vals):
        taper = 1.0 - 0.38 * (s / 0.93) if s < 0.93 else 0.62 * math.sqrt(max(1.0 - (s - 0.93) / 0.07, 0.0))
        r_mean = spadix_r_base * taper * 0.55
        for j, th in enumerate(theta_sp):
            primordia = (math.cos(26 * th) * math.cos(110 * s * math.pi)) ** 4
            ovule_radii[i, j] = r_mean + (0.25 * primordia * (1.0 - s))
            cols_ovules[i, j] = np.clip(c_ovule * (0.7 + 0.3 * primordia), 0.0, 1.0)
    _add_closed_tube(spadix_pts, ovule_radii, cols_ovules, n_sl, vertices, colors, f_ovules, cap_start=True, cap_end=True)
    groups["Ovulos_Internos"] = f_ovules

    f_axis = []
    axis_radii = np.zeros(n_sp)
    for i, s in enumerate(s_vals):
        taper = 1.0 - 0.38 * (s / 0.93) if s < 0.93 else 0.62 * math.sqrt(max(1.0 - (s - 0.93) / 0.07, 0.0))
        base_r = spadix_r_base * taper * 0.28
        nodal_bulge = 0.15 * math.sin(s * 60 * math.pi) * (1.0 - s)
        axis_radii[i] = max(0.05, base_r + nodal_bulge)
    _add_closed_tube(spadix_pts, axis_radii, np.tile(c_axis, (n_sp, 1)), 12, vertices, colors, f_axis, cap_start=True, cap_end=True)
    groups["Eje_Vascular_Interno"] = f_axis

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
    _add_closed_tube(ped_pts, ped_radii, ped_cols, 20, vertices, colors, f_ped, cap_start=True, cap_end=True)
    groups["Pedunculo_Tallo"] = f_ped

    lines = []
    for v, c in zip(vertices, colors):
        lines.append(f"v {v[0]:.4f} {v[1]:.4f} {v[2]:.4f} {c[0]:.4f} {c[1]:.4f} {c[2]:.4f}" + NL)
    for grp_name, grp_faces in groups.items():
        lines.append(f"g {grp_name}" + NL)
        for f_idx in grp_faces:
            lines.append(f"f {f_idx[0]} {f_idx[1]} {f_idx[2]}" + NL)
    return "".join(lines)


def build_andraeanum_obj(cfg):
    """
    Atlas Morfométrico Floral de Alta Precisión para Anthurium andraeanum (COL-NAR-002):
    - Contorno C1-continuo (sin escalones laterales en v=0) desde los lóbulos cordados
      basales hasta el ápice acuminado (acumen) curvado.
    - Campo de venación pinnado-pedado continuo mediante transición hiperbólica (tanh),
      surcos venosos profundos exponenciales, nervio colector submarginal y relieve
      celular bullado (ampollado) asimétrico entre nervaduras.
    - Espádice protógino con micro-relieve de tépalos y gotas estigmáticas en 5 capas.
    """
    c_cfg = cfg.get('perianto', {}).get('corola', {})
    g_cfg = cfg.get('gineceo', {})
    arq_cfg = cfg.get('arquitectura_floral', {})

    spathe_len = float(c_cfg.get('longitud_limbo_mm', 98.0))
    w_max = float(c_cfg.get('ancho_petalo_mm', 86.0)) * 0.58
    wall_thick = float(c_cfg.get('grosor_pared_mm', 1.8))

    # Paleta cromática histológica de alto contraste (antocianinas epidérmicas/hipodérmicas)
    c_carmine = np.array([0.82, 0.04, 0.11])      # Rojo carmín intenso base
    c_vein_deep = np.array([0.32, 0.01, 0.03])    # Sombra profunda en surcos venosos
    c_gloss = np.array([1.00, 0.30, 0.34])        # Brillo especular ceroso en crestas bulladas
    c_rim_dark = np.array([0.52, 0.02, 0.06])     # Borde submarginal intenso
    c_abaxial = np.array([0.72, 0.14, 0.17])      # Envés rosado-rojizo
    c_node_green = np.array([0.36, 0.54, 0.15])   # Transición clorofílica basal

    c_peduncle = np.array([0.22, 0.42, 0.13])     # Verde pedúnculo
    c_spadix_base = np.array([0.96, 0.94, 0.82])  # Zona femenina protógina (blanco-crema)
    c_spadix_mid = np.array([0.96, 0.84, 0.24])   # Transición amarilla
    c_spadix_tip = np.array([0.90, 0.68, 0.10])   # Ápice amarillo-dorado cálido
    c_androceo = np.array([0.98, 0.93, 0.52])     # Micro-estambres
    c_ovary = np.array([0.80, 0.91, 0.66])        # Matriz de ovarios biloculares
    c_ovule = np.array([0.98, 0.97, 0.88])        # Óvulos placentarios
    c_axis = np.array([0.93, 0.90, 0.78])         # Eje vascular central

    vertices, colors = [], []
    groups = {}

    # =========================================================================
    # 1. ESPATA CORDIFORME BULLADA (Continuidad C1 Exacta + Ampollas Orgánicas)
    # =========================================================================
    f_spathe = []
    v_min = -float(c_cfg.get('lobe_length_ratio', 0.35))
    n_v_neg = 42
    n_v_pos = 92
    n_u_half = 48

    v_neg = np.linspace(v_min, 0.0, n_v_neg, endpoint=False)
    v_pos = np.linspace(0.0, 1.0, n_v_pos)
    v_vals = np.concatenate([v_neg, v_pos])
    n_v = len(v_vals)
    u_locs = np.linspace(0.0, 1.0, n_u_half)

    pitch_deg = float(arq_cfg.get('angulo_espata_reflexa_grados', -38.0))
    pitch_spathe = math.radians(pitch_deg)
    cp_s, sp_s = math.cos(pitch_spathe), math.sin(pitch_spathe)

    for side in (-1.0, 1.0):
        top_grid = np.zeros((n_v, n_u_half), dtype=int)
        bot_grid = np.zeros((n_v, n_u_half), dtype=int)

        for i, v in enumerate(v_vals):
            # Contorno C1-continuo: en v=0 tanto v<0 como v>=0 valen exactamente w_max con derivada 0
            if v < 0.0:
                tau = min(1.0, abs(v / v_min))
                lobe_arc = math.sqrt(max(0.0, 1.0 - (tau ** 2)))
                x_c = 0.43 * w_max
                # Seno basal estrecho y redondeado que se cierra en x_c cuando tau=1
                x_in = x_c * (1.0 - lobe_arc) * (0.12 + 0.88 * (tau ** 1.8))
                # En tau=0 (v=0): x_out = 0.43*w_max + 0.57*w_max = 1.00 * w_max
                x_out = x_c + (w_max - x_c) * lobe_arc
                y_base = v * spathe_len * 0.82
            else:
                x_in = 0.0
                # En v=0: x_out = 1.00 * w_max y derivada dx_out/dv = 0 (CERO escalón lateral)
                env_main = ((1.0 - (v ** 1.85)) ** 0.82) * (1.0 - 0.38 * (v ** 2.2))
                acumen_cusp = 0.045 * (1.0 - v) * math.exp(-(((v - 0.91) / 0.06) ** 2))
                x_out = w_max * (env_main + acumen_cusp)
                y_base = v * spathe_len

            # Ligera asimetría orgánica en el acumen apical (como en especímenes reales)
            apex_bend_x = 2.8 * (max(0.0, (v - 0.72) / 0.28) ** 2.2)

            for j, u_loc in enumerate(u_locs):
                x_abs = x_in + u_loc * (x_out - x_in)
                x_lam = side * x_abs + apex_bend_x
                y_lam = y_base

                # Coordenadas normalizadas sobre la lámina
                X_n = x_abs / max(1.0, w_max)
                Y_n = y_lam / max(1.0, spathe_len)
                r_polar = math.sqrt(x_abs ** 2 + y_lam ** 2)

                # -------------------------------------------------------------
                # VENACIÓN PINNADA-PEDADA CONTINUA + TEJIDO BULLADO CELULAR
                # -------------------------------------------------------------
                # u_vein traza venas que suben en Y>0 (pinnadas) y bajan en Y<0 (pedadas)
                arch_dir = math.tanh(3.4 * (Y_n + 0.06))
                u_vein = Y_n - 0.38 * (X_n ** 1.15) * arch_dir + 0.08 * (X_n ** 2)

                # Surcos venosos primarios estrechos y profundos (perfil exponencial en V)
                s_primary = math.sin(6.2 * math.pi * u_vein)
                primary_groove = math.exp(-5.5 * (s_primary ** 2))
                primary_pillow = 1.0 - primary_groove

                # Nervio colector submarginal continuo a u_loc = 0.84
                collector_groove = math.exp(-(((u_loc - 0.84) / 0.036) ** 2)) * (1.0 - 0.45 * (max(0.0, v) ** 2))

                # Ampollas / Bullae celulares entre venas primarias (reticulado secundario y terciario)
                cell_w1 = math.sin(4.6 * math.pi * X_n + 1.4 * math.sin(5.0 * math.pi * Y_n)) ** 2
                cell_w2 = math.cos(3.2 * math.pi * u_vein - 2.4 * math.pi * X_n) ** 2
                tertiary_wrinkle = 0.18 * math.sin(14.0 * math.pi * X_n + 8.0 * math.pi * u_vein)
                blister_field = (0.58 + 0.42 * cell_w1 * (0.45 + 0.55 * cell_w2) + tertiary_wrinkle)

                # Atenuación suave en márgenes, seno y punta acuminada
                fade_margin = (1.0 - (u_loc ** 2.6)) * (1.0 - 0.55 * (max(0.0, v) ** 3))
                if v < 0.0:
                    fade_margin *= math.sqrt(max(0.0, 1.0 - ((v / v_min) ** 2)))

                # Nervio central hundido en el haz (v >= 0)
                midrib_mask = math.exp(-((x_abs / 2.0) ** 2)) * (1.0 - max(0.0, v) ** 1.4) if v >= -0.02 else 0.0
                z_central = -2.2 * midrib_mask

                # Relieve total bullado (cojinetes elevados + surcos primarios y colector hundidos)
                z_bullate = (
                    2.85 * primary_pillow * blister_field * fade_margin * math.sin(math.pi * min(1.0, u_loc * 1.10 + 0.06))
                    - 1.15 * primary_groove * fade_margin
                    - 1.05 * collector_groove
                )

                # Curvatura macroscópica de la espata (aurículas elevadas, dorso arqueado y acumen deflexo)
                lobe_lift = 4.8 * abs(min(0.0, v) / v_min) * (u_loc ** 1.1)
                acumen_droop = -5.2 * (max(0.0, (v - 0.65) / 0.35) ** 2.0)
                margin_undulation = 1.45 * (u_loc ** 3) * math.sin(4.5 * math.pi * v + 0.6 * side)
                z_cup = -3.6 * (X_n ** 1.65) * (1.0 - 0.35 * max(0.0, v)) + lobe_lift + acumen_droop + margin_undulation

                z_lam_ad = z_cup + z_central + z_bullate
                thickness = (wall_thick * 0.62 + 0.80 * midrib_mask) * (1.0 - 0.38 * (u_loc ** 2))
                z_lam_ab = z_lam_ad - thickness

                # Rotación reflexa de la espata
                y_ad = y_lam * cp_s - z_lam_ad * sp_s
                z_ad = y_lam * sp_s + z_lam_ad * cp_s
                y_ab = y_lam * cp_s - z_lam_ab * sp_s
                z_ab = y_lam * sp_s + z_lam_ab * cp_s

                # Colorimetría PBR por vértice: surcos venosos oscuros y cúpulas bulladas con brillo especular
                vein_shadow = np.clip((primary_groove * 0.85 + collector_groove * 0.75) * fade_margin + 0.45 * midrib_mask, 0.0, 1.0)
                dome_highlight = np.clip((z_bullate / 2.85), 0.0, 1.0) ** 1.35
                rim_shade = np.clip((u_loc - 0.86) / 0.14, 0.0, 1.0)

                col_ad = (
                    (1.0 - vein_shadow) * c_carmine
                    + vein_shadow * c_vein_deep
                    + (c_gloss - c_carmine) * (0.78 * dome_highlight)
                    - (c_carmine - c_rim_dark) * (0.35 * rim_shade)
                )

                node_blend = math.exp(-((r_polar / 4.6) ** 2))
                col_ad = (1.0 - 0.55 * node_blend) * col_ad + (0.55 * node_blend) * c_node_green
                col_ab = (1.0 - 0.60 * node_blend) * c_abaxial + (0.60 * node_blend) * c_node_green

                vertices.append([x_lam, y_ad, z_ad])
                colors.append(np.clip(col_ad, 0.0, 1.0).tolist())
                top_grid[i, j] = len(vertices)

                vertices.append([x_lam, y_ab, z_ab])
                colors.append(np.clip(col_ab, 0.0, 1.0).tolist())
                bot_grid[i, j] = len(vertices)

        for i in range(n_v - 1):
            for j in range(n_u_half - 1):
                if side > 0:
                    f_spathe.append((top_grid[i, j], top_grid[i, j + 1], top_grid[i + 1, j + 1]))
                    f_spathe.append((top_grid[i, j], top_grid[i + 1, j + 1], top_grid[i + 1, j]))
                    f_spathe.append((bot_grid[i, j + 1], bot_grid[i, j], bot_grid[i + 1, j + 1]))
                    f_spathe.append((bot_grid[i, j], bot_grid[i + 1, j], bot_grid[i + 1, j + 1]))
                else:
                    f_spathe.append((top_grid[i, j + 1], top_grid[i, j], top_grid[i + 1, j + 1]))
                    f_spathe.append((top_grid[i, j], top_grid[i + 1, j], top_grid[i + 1, j + 1]))
                    f_spathe.append((bot_grid[i, j], bot_grid[i, j + 1], bot_grid[i + 1, j + 1]))
                    f_spathe.append((bot_grid[i, j], bot_grid[i + 1, j + 1], bot_grid[i + 1, j]))

            if side > 0:
                f_spathe.append((top_grid[i, -1], bot_grid[i, -1], top_grid[i + 1, -1]))
                f_spathe.append((bot_grid[i, -1], bot_grid[i + 1, -1], top_grid[i + 1, -1]))
                if i < n_v_neg:
                    f_spathe.append((bot_grid[i, 0], top_grid[i, 0], top_grid[i + 1, 0]))
                    f_spathe.append((bot_grid[i, 0], top_grid[i + 1, 0], bot_grid[i + 1, 0]))
            else:
                f_spathe.append((bot_grid[i, -1], top_grid[i, -1], top_grid[i + 1, -1]))
                f_spathe.append((bot_grid[i, -1], top_grid[i + 1, -1], bot_grid[i + 1, -1]))
                if i < n_v_neg:
                    f_spathe.append((top_grid[i, 0], bot_grid[i, 0], top_grid[i + 1, 0]))
                    f_spathe.append((bot_grid[i, 0], bot_grid[i + 1, 0], top_grid[i + 1, 0]))

    groups["Espata_Cordiforme"] = f_spathe

    # =========================================================================
    # 2. PEDÚNCULO SÓLIDO Y ESTÍPITE BASAL (2.0 mm)
    # =========================================================================
    f_ped = []
    n_ped = 36
    t_ped = np.linspace(0.0, 1.0, n_ped)
    ped_pts = np.column_stack([
        np.zeros(n_ped),
        -0.4 - t_ped * 90.0,
        -0.8 - t_ped * 12.0
    ])
    ped_radii = 2.6 + 1.3 * np.exp(-t_ped * 15.0)
    ped_cols = np.zeros((n_ped, 3))
    for i, tp in enumerate(t_ped):
        top_tint = math.exp(-tp * 10.0) * 0.32
        ped_cols[i] = (1.0 - top_tint) * c_peduncle + top_tint * np.array([0.46, 0.22, 0.14])

    _add_closed_tube(ped_pts, ped_radii, ped_cols, 24, vertices, colors, f_ped, cap_start=True, cap_end=True)
    groups["Pedunculo_Tallo"] = f_ped

    # =========================================================================
    # 3 a 7. ESPÁDICE PROTÓGINO: 5 Capas Concéntricas con Pápilas Estigmáticas
    # =========================================================================
    spadix_len = float(g_cfg.get('estilo_longitud_mm', 70.0))
    spadix_r_base = float(g_cfg.get('diametro_espadice_mm', 9.2)) / 2.0
    stipe_mm = float(arq_cfg.get('estipite_longitud_mm', 2.0))
    n_sp, n_sl = 110, 52
    s_vals = np.linspace(0.0, 1.0, n_sp)
    theta_sp = np.linspace(0.0, 2.0 * np.pi, n_sl, endpoint=False)

    inc_rad = math.radians(float(arq_cfg.get('angulo_espadice_grados', 52.0)))
    spadix_pts = np.column_stack([
        np.zeros(n_sp),
        (stipe_mm + s_vals * spadix_len) * math.cos(inc_rad) + np.sin(s_vals * np.pi) * 2.0,
        (stipe_mm + s_vals * spadix_len) * math.sin(inc_rad)
    ])

    def _spadix_taper(s):
        if s < 0.88:
            return 1.0 - 0.26 * (s / 0.88)
        else:
            return 0.74 * math.sqrt(max(0.0, 1.0 - (((s - 0.88) / 0.12) ** 2)))

    f_spadix_ext, f_androceo, f_ovary, f_ovules, f_axis = [], [], [], [], []
    r_ext, r_and, r_ov, r_ovm, r_ax = np.zeros((5, n_sp, n_sl))
    c_ext, c_and, c_ov, c_ovm = np.zeros((4, n_sp, n_sl, 3))
    c_ax_flat = np.tile(c_axis, (n_sp, 1))

    for i, s in enumerate(s_vals):
        taper = _spadix_taper(s)
        r_mean = spadix_r_base * taper

        if s < 0.42:
            mix_s = s / 0.42
            c_ring = (1.0 - mix_s) * c_spadix_base + mix_s * c_spadix_mid
        else:
            mix_s = (s - 0.42) / 0.58
            c_ring = (1.0 - mix_s) * c_spadix_mid + mix_s * c_spadix_tip

        r_ax[i, :] = max(0.03, r_mean * 0.22 + 0.06 * math.sin(s * 50.0 * math.pi) * (1.0 - s))

        for j, th in enumerate(theta_sp):
            # 3. Perianto Externo: Tépalos romboidales + pápilas estigmáticas prominentes en zona basal/media
            floret_grid = math.cos(14.0 * th + 46.0 * s * math.pi) * math.cos(14.0 * th - 46.0 * s * math.pi)
            parastichy = floret_grid ** 2
            stigma_papilla = (max(0.0, floret_grid) ** 10) * (1.0 - 0.65 * (s ** 2))
            r_ext[i, j] = max(0.04, r_mean + (0.28 * parastichy + 0.52 * stigma_papilla) * (1.0 - (s ** 4)))
            c_ext[i, j] = np.clip(
                c_ring * (0.86 + 0.16 * parastichy) + np.array([0.14, 0.14, 0.18]) * stigma_papilla,
                0.0, 1.0
            )

            # 4. Androceo / 4 Micro-Estambres por flósculo (88%)
            granules = (math.sin(28.0 * th + (i % 2) * 0.8) * math.sin(85.0 * s * math.pi)) ** 2
            r_and[i, j] = max(0.03, r_mean * 0.88 + 0.20 * granules * (1.0 - (s ** 3)))
            c_and[i, j] = np.clip(c_androceo * (0.88 + 0.18 * granules), 0.0, 1.0)

            # 5. Gineceo / Matriz de Ovarios Biloculares (70%)
            honeycomb = math.cos(14.0 * th) * math.sin(55.0 * s * math.pi)
            r_ov[i, j] = max(0.02, r_mean * 0.70 + 0.16 * honeycomb * (1.0 - (s ** 3)))
            c_ov[i, j] = np.clip(c_ovary * (0.88 + 0.14 * honeycomb), 0.0, 1.0)

            # 6. Óvulos Placentarios Internos (42%)
            ovoid_bump = (math.cos(14.0 * th + (i % 2) * 0.5) * math.sin(46.0 * s * math.pi)) ** 4
            r_ovm[i, j] = max(0.02, r_mean * 0.42 + 0.62 * ovoid_bump * (1.0 - (s ** 2)))
            c_ovm[i, j] = np.clip(c_ovule * (0.88 + 0.15 * ovoid_bump), 0.0, 1.0)

    _add_closed_tube(spadix_pts, r_ext, c_ext, n_sl, vertices, colors, f_spadix_ext, cap_start=True, cap_end=True)
    _add_closed_tube(spadix_pts, r_and, c_and, n_sl, vertices, colors, f_androceo,   cap_start=True, cap_end=True)
    _add_closed_tube(spadix_pts, r_ov,  c_ov,  n_sl, vertices, colors, f_ovary,      cap_start=True, cap_end=True)
    _add_closed_tube(spadix_pts, r_ovm, c_ovm, n_sl, vertices, colors, f_ovules,     cap_start=True, cap_end=True)
    _add_closed_tube(spadix_pts, r_ax[:, 0], c_ax_flat, 16, vertices, colors, f_axis, cap_start=True, cap_end=True)

    groups["Espadice_Florifero_Externo"] = f_spadix_ext
    groups["Androceo_Micro_Estambres"] = f_androceo
    groups["Gineceo_Ovarios"] = f_ovary
    groups["Ovulos_Internos_Placentarios"] = f_ovules
    groups["Eje_Vascular_Interno"] = f_axis

    lines = []
    for v, c in zip(vertices, colors):
        lines.append(f"v {v[0]:.4f} {v[1]:.4f} {v[2]:.4f} {c[0]:.4f} {c[1]:.4f} {c[2]:.4f}" + NL)
    for grp_name, grp_faces in groups.items():
        lines.append(f"g {grp_name}" + NL)
        for f_idx in grp_faces:
            lines.append(f"f {f_idx[0]} {f_idx[1]} {f_idx[2]}" + NL)
    return "".join(lines)


def build_araceae_inflorescence(cfg):
    especie = cfg.get('colecta', {}).get('especie', '').lower()
    disposicion = cfg.get('arquitectura_floral', {}).get('disposicion', 'erecta').lower()
    if "sanjorgense" in especie or disposicion == "pendula":
        return build_sanjorgense_original_obj(cfg)
    else:
        return build_andraeanum_obj(cfg)
