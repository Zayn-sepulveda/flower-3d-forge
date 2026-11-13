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
            bump = (math.cos(13 * th + (i % 2) * 1.5) * math.sin(55 * s * math.pi)) ** 2
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
    Morfología e histología interna en formato Atlas para Anthurium andraeanum (COL-NAR-002):
    - Espata cordiforme orgánica: Venación palmada-arcuada proyectada en coordenadas polares (theta = atan2(u,v))
      con nervio central profundo y cojinetes bullados (convexos) entre nervaduras.
    - Pedúnculo sólido frenado exactamente en el receptáculo dorsal (0, -0.5, -1.2).
    - Espádice proyectado a +62° respecto al tallo (~84° respecto a la espata reflexa) con 5 capas de disección.
    """
    c_cfg = cfg.get('perianto', {}).get('corola', {})
    g_cfg = cfg.get('gineceo', {})

    spathe_len = float(c_cfg.get('longitud_limbo_mm', 90.0))
    w_max = float(c_cfg.get('ancho_petalo_mm', 85.0)) * 0.62

    # Paleta cromática anatómica
    c_carmine = np.array([0.86, 0.05, 0.15])     # Rojo carmín ceroso principal
    c_vein_deep = np.array([0.55, 0.01, 0.06])   # Fondo hundido de venas (muy oscuro)
    c_gloss = np.array([0.96, 0.15, 0.22])       # Brillo especular en cojinetes convexos
    c_abaxial = np.array([0.75, 0.15, 0.18])     # Envés mate
    c_node_green = np.array([0.40, 0.55, 0.15])  # Transición en el receptáculo

    c_peduncle = np.array([0.23, 0.42, 0.14])    # Verde oliva
    c_spadix_base = np.array([0.95, 0.86, 0.24]) # Trama tépalos (exterior)
    c_spadix_tip = np.array([0.98, 0.94, 0.58])  # Ápice claro
    c_androceo = np.array([0.98, 0.93, 0.52])    # Polen (androceo estaminal)
    c_ovary = np.array([0.80, 0.91, 0.66])       # Tejido gineceo (verde pálido translúcido)
    c_ovule = np.array([0.98, 0.97, 0.88])       # Perlas ovulares brillantes
    c_axis = np.array([0.93, 0.90, 0.78])        # Haces vasculares (núcleo)

    vertices, colors = [], []
    groups = {}

    # =========================================================================
    # 1. ESPATA CORDIFORME BULLADA - Mapeo Polar Palmado-Arcuado
    # =========================================================================
    f_spathe = []
    v_min = -0.36
    n_v_neg = 32
    n_v_pos = 72
    n_u_half = 36

    v_neg = np.linspace(v_min, 0.0, n_v_neg, endpoint=False)
    v_pos = np.linspace(0.0, 1.0, n_v_pos)
    v_vals = np.concatenate([v_neg, v_pos])
    n_v = len(v_vals)
    u_locs = np.linspace(0.0, 1.0, n_u_half)

    pitch_spathe = math.radians(-22.0)
    cp_s, sp_s = math.cos(pitch_spathe), math.sin(pitch_spathe)

    for side in (-1.0, 1.0):
        top_grid = np.zeros((n_v, n_u_half), dtype=int)
        bot_grid = np.zeros((n_v, n_u_half), dtype=int)

        for i, v in enumerate(v_vals):
            # Perfil 2D del corazón
            if v < 0.0:
                tau = min(1.0, abs(v / v_min))
                ellipse_rad = math.sqrt(max(0.0, 1.0 - (tau ** 2)))
                x_lobe_center = w_max * (0.44 + 0.04 * (1.0 - tau))
                x_in = x_lobe_center * (1.0 - ellipse_rad)
                x_out = x_lobe_center + (w_max - x_lobe_center) * ellipse_rad
                y_base = v * spathe_len * 0.85
            else:
                x_in = 0.0
                acumen_taper = (1.0 - (v ** 1.15)) ** 0.62
                shoulder_round = 1.0 + 0.10 * math.sin(math.pi * (v ** 0.7))
                x_out = w_max * acumen_taper * shoulder_round
                y_base = v * spathe_len

            for j, u_loc in enumerate(u_locs):
                x_abs = x_in + u_loc * (x_out - x_in)
                x_lam = side * x_abs
                y_lam = y_base

                # -------------------------------------------------------------
                # MATEMÁTICA POLAR EXACTA: Venación y Tejido Bullado
                # -------------------------------------------------------------
                # 1. Coordenadas polares irradiando desde el receptáculo
                r_polar = math.sqrt(x_abs**2 + y_lam**2)
                r_norm = min(1.0, r_polar / max(1.0, spathe_len))
                
                # Ángulo desde el nervio central (eje Y) hacia los márgenes
                theta_polar = math.atan2(x_abs, y_lam)
                
                # Curvatura arcuada paramétrica (las venas se abren hacia los lados)
                theta_arcuate = theta_polar + 0.75 * (r_norm ** 1.25)
                n_veins = 5.5
                
                # 2. Nervio Central Profundo (z_central)
                # Zanja gaussiana profunda en x=0, atenuándose hacia el ápice (v=1)
                z_central = -1.8 * math.exp(-((x_abs / 2.5) ** 2)) * (1.0 - max(0.0, v))
                
                # 3. Tejido Bullado Intervenal (z_bullate)
                # Elevando al cuadrado el seno creamos cúpulas anchas (cojinetes) y surcos estrechos (venas)
                fade_margin = 1.0 - (u_loc ** 2.0)
                if v < 0.0:
                    fade_margin *= math.sqrt(max(0.0, 1.0 - ((v / v_min) ** 2)))
                
                z_bullate = 1.65 * (math.sin(n_veins * theta_arcuate) ** 2) * math.sin(math.pi * min(1.0, r_norm * 2.2)) * fade_margin
                
                # Forma de plato de la lámina general
                edge_dist = x_abs / max(1.0, w_max)
                z_cup = -3.5 * (edge_dist ** 1.8) * (1.0 - 0.4 * max(0.0, v))
                
                # Suma topológica de desplazamientos Z
                z_lam_ad = z_cup + z_central + z_bullate
                thickness = (1.2 + 0.8 * math.exp(-((x_abs / 2.5) ** 2))) * (1.0 - 0.4 * (u_loc ** 2))
                z_lam_ab = z_lam_ad - thickness

                # 4. Inclinación Global de la Espata (-22° Pivotando en 0,0,0)
                y_ad = y_lam * cp_s - z_lam_ad * sp_s
                z_ad = y_lam * sp_s + z_lam_ad * cp_s
                y_ab = y_lam * cp_s - z_lam_ab * sp_s
                z_ab = y_lam * sp_s + z_lam_ab * cp_s

                # 5. Colorimetría de Contraste Céreo
                # Las venas profundas y el nervio central toman sombra, los abultamientos toman brillo
                is_midrib = math.exp(-((x_abs / 2.5) ** 2))
                vein_valley = 1.0 - (math.sin(n_veins * theta_arcuate) ** 2)
                
                col_ad = (
                    c_carmine * (1.0 - 0.4 * is_midrib)
                    + (c_gloss - c_carmine) * (0.6 * (z_bullate / 1.65))
                    - (c_carmine - c_vein_deep) * (0.5 * vein_valley * fade_margin)
                )
                
                node_blend = math.exp(-((r_polar / 5.0) ** 2))
                col_ad = (1.0 - 0.5 * node_blend) * col_ad + (0.5 * node_blend) * c_node_green
                col_ab = (1.0 - 0.6 * node_blend) * c_abaxial + (0.6 * node_blend) * c_node_green

                vertices.append([x_lam, y_ad, z_ad])
                colors.append(np.clip(col_ad, 0.0, 1.0).tolist())
                top_grid[i, j] = len(vertices)

                vertices.append([x_lam, y_ab, z_ab])
                colors.append(np.clip(col_ab, 0.0, 1.0).tolist())
                bot_grid[i, j] = len(vertices)

        # Malla para cada hemisferio
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
    # 2. PEDÚNCULO SÓLIDO (Frenado en el Nodo 0,0,0)
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
    ped_cols = np.tile(c_peduncle, (n_ped, 1))

    _add_closed_tube(ped_pts, ped_radii, ped_cols, 24, vertices, colors, f_ped, cap_start=True, cap_end=True)
    groups["Pedunculo_Tallo"] = f_ped

    # =========================================================================
    # EJE DEL ESPÁDICE: +62° (Perpendicularidad orgánica)
    # =========================================================================
    spadix_len = float(g_cfg.get('estilo_longitud_mm', 68.0))
    spadix_r_base = float(g_cfg.get('diametro_espadice_mm', 8.5)) / 2.0
    n_sp, n_sl = 96, 44
    s_vals = np.linspace(0.0, 1.0, n_sp)
    theta_sp = np.linspace(0.0, 2.0 * np.pi, n_sl, endpoint=False)

    inc_rad = math.radians(62.0)
    spadix_pts = np.column_stack([
        np.zeros(n_sp),
        s_vals * spadix_len * math.cos(inc_rad) + np.sin(s_vals * np.pi) * 2.2,
        s_vals * spadix_len * math.sin(inc_rad)
    ])

    def _spadix_taper(s):
        if s < 0.88: return 1.0 - 0.26 * (s / 0.88)
        else: return 0.74 * math.sqrt(max(0.0, 1.0 - (((s - 0.88) / 0.12) ** 2)))

    # =========================================================================
    # 3 a 7. ANATOMÍA INTERNA: 5 Capas de Disección Concéntricas
    # =========================================================================
    f_spadix_ext, f_androceo, f_ovary, f_ovules, f_axis = [], [], [], [], []
    r_ext, r_and, r_ov, r_ovm, r_ax = np.zeros((5, n_sp, n_sl))
    c_ext, c_and, c_ov, c_ovm = np.zeros((4, n_sp, n_sl, 3))
    c_ax_flat = np.tile(c_axis, (n_sp, 1))

    for i, s in enumerate(s_vals):
        taper = _spadix_taper(s)
        r_mean = spadix_r_base * taper
        c_ring = (1.0 - s) * c_spadix_base + s * c_spadix_tip
        
        # 7. Eje Vascular (22% Radio)
        r_ax[i, :] = max(0.03, r_mean * 0.22 + 0.06 * math.sin(s * 50.0 * math.pi) * (1.0 - s))

        for j, th in enumerate(theta_sp):
            # 3. Perianto Externo (100%)
            parastichy = (math.cos(15.0 * th + 48.0 * s * math.pi) * math.cos(15.0 * th - 48.0 * s * math.pi)) ** 2
            r_ext[i, j] = max(0.04, r_mean + 0.34 * parastichy * (1.0 - (s ** 4)))
            c_ext[i, j] = np.clip(c_ring * (0.92 + 0.12 * parastichy), 0.0, 1.0)

            # 4. Androceo / Estambres (88%)
            granules = (math.sin(30.0 * th + (i % 2) * 0.8) * math.sin(85.0 * s * math.pi)) ** 2
            r_and[i, j] = max(0.03, r_mean * 0.88 + 0.20 * granules * (1.0 - (s ** 3)))
            c_and[i, j] = np.clip(c_androceo * (0.88 + 0.18 * granules), 0.0, 1.0)

            # 5. Gineceo / Matriz Ovárica (70%)
            honeycomb = math.cos(15.0 * th) * math.sin(55.0 * s * math.pi)
            r_ov[i, j] = max(0.02, r_mean * 0.70 + 0.16 * honeycomb * (1.0 - (s ** 3)))
            c_ov[i, j] = np.clip(c_ovary * (0.88 + 0.14 * honeycomb), 0.0, 1.0)

            # 6. Óvulos Internos Brillantes (42%)
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