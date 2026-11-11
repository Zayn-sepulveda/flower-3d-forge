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
    Generador paramétrico de Anthurium andraeanum:
    1. Espata abierta y plana cordiforme (acorazonada con aurículas basales traseras).
    2. Textura bullada senoidal cruzada, sin picos de ruido.
    3. Espádice liso, orientado hacia adelante a 35°, subcónico y cerrado en el ápice.
    4. Conexión limpia con pedúnculo central.
    """
    c_cfg = cfg['perianto']['corola']
    g_cfg = cfg.get('gineceo', {})

    # Parámetros macro
    spathe_len = float(c_cfg.get('longitud_limbo_mm', 90.0))
    spathe_w = float(c_cfg.get('ancho_petalo_mm', 85.0))

    # Paleta de colores RGB exacta (Carmín puro sólido, Amarillo cremoso, Verde tallo)
    c_spathe  = np.array([0.85, 0.05, 0.15])  # Rojo carmín uniforme
    c_spadix  = np.array([0.95, 0.85, 0.20])  # Amarillo luminoso crema
    c_stem    = np.array([0.35, 0.55, 0.20])  # Verde manzana/oliva

    vertices, colors, faces = [], [], []

    # =========================================================================
    # 1. ESPATA (Bráctea Cordiforme Abierta y Bullada)
    # =========================================================================
    n_v, n_u = 85, 75
    # El rango 'v' va desde -0.2 (Lóbulos basales hacia atrás) hasta 1.0 (Ápice distal)
    v_vals = np.linspace(-0.25, 1.0, n_v)
    u_vals = np.linspace(-1.0, 1.0, n_u)
    base_idx_spathe = len(vertices)

    # Inclinación general de la espata hacia atrás (~20°)
    spathe_tilt = math.radians(-20.0)
    ca_sp, sa_sp = math.cos(spathe_tilt), math.sin(spathe_tilt)

    for v in v_vals:
        for u in u_vals:
            abs_u = abs(u)

            # Silueta Cordiforme paramétrica w(t)
            if v < 0.0:
                # Lóbulos traseros redondeados (aurículas)
                lobe_t = (v + 0.25) / 0.25
                max_w = spathe_w * 0.5 * math.sqrt(max(0.001, 1.0 - (1.0 - lobe_t)**2))
                y_base = v * spathe_len * 0.4
            else:
                # Cuerpo delantero que termina en acumen
                acumen = 0.05 * math.exp(-((v - 0.95) / 0.05)**2)
                max_w = spathe_w * 0.5 * ((1.0 - v)**0.65) + acumen * spathe_w
                y_base = v * spathe_len

            # Textura bullada bivariada (sin picos aleatorios, pura matemática suave)
            # A * sin(ku * u) * sin(kv * v)
            bull_z = 2.2 * math.sin(7.0 * math.pi * u) * math.sin(8.0 * math.pi * v)
            # Depresión de la nervadura central
            midrib_z = -3.0 * math.exp(-((u / 0.08)**2))
            # Curvatura cóncava suave global (plato)
            cup_z = 8.0 * (u**2) * (1.0 - 0.5 * max(0.0, v))

            x_loc = u * max_w
            y_loc = y_base
            z_loc = cup_z + bull_z + midrib_z

            # Aplicar inclinación de la espata
            px = x_loc
            py = y_loc * ca_sp - z_loc * sa_sp
            pz = y_loc * sa_sp + z_loc * ca_sp

            # Sombreado simulado: Oscurecer valles bullados ligeramente
            shade = 0.92 + 0.08 * math.sin(7.0 * math.pi * u) * math.sin(8.0 * math.pi * v)
            c_s = c_spathe * shade

            vertices.append([px, py, pz])
            colors.append(np.clip(c_s, 0.0, 1.0).tolist())

    for i in range(n_v - 1):
        for j in range(n_u - 1):
            p1 = base_idx_spathe + i * n_u + j + 1
            p2 = base_idx_spathe + i * n_u + (j + 1) + 1
            p3 = base_idx_spathe + (i + 1) * n_u + (j + 1) + 1
            p4 = base_idx_spathe + (i + 1) * n_u + j + 1
            faces.append((p1, p2, p3))
            faces.append((p1, p3, p4))

    # =========================================================================
    # 2. ESPÁDICE (Proyectado a 35°, liso, subcónico, cerrado apicalmente)
    # =========================================================================
    spadix_len = float(g_cfg.get('estilo_longitud_mm', 75.0))
    spadix_r_base = float(g_cfg.get('estilo_grosor_mm', g_cfg.get('diametro_espadice_mm', 8.5))) / 2.0
    
    n_sp, n_su = 40, 24
    t_spadix = np.linspace(0.0, 1.0, n_sp)
    u_spadix = np.linspace(0.0, 2.0 * math.pi, n_su, endpoint=False)
    base_idx_spadix = len(vertices)

    # Inclinación del espádice hacia adelante (Pitch de ~35°)
    pitch = math.radians(35.0)
    ca_p, sa_p = math.cos(pitch), math.sin(pitch)

    for ts in t_spadix:
        # Tapering sutil (r(t) = R * (1 - c*t))
        r_curr = spadix_r_base * (1.0 - 0.15 * ts)
        
        # Micro-teselado botánico suave (floretes romboidales finos, no churros retorcidos)
        floret = 0.3 * (math.cos(12.0 * ts * math.pi) * math.cos(20.0 * ts * math.pi))

        cy_sp = ts * spadix_len
        for us in u_spadix:
            r_loc = r_curr + floret
            x_loc = r_loc * math.cos(us)
            y_loc = cy_sp
            z_loc = r_loc * math.sin(us)

            # Rotar el espádice desde su base (el origen local)
            px = x_loc
            py = y_loc * ca_p - z_loc * sa_p
            pz = y_loc * sa_p + z_loc * ca_p + 1.5  # Elevado ligeramente del plano

            # Textura de color
            c_f = c_spadix * (0.95 + 0.05 * math.sin(12.0 * ts * math.pi))
            vertices.append([px, py, pz])
            colors.append(c_f.tolist())

    for i in range(n_sp - 1):
        for j in range(n_su):
            p1 = base_idx_spadix + i * n_su + j + 1
            p2 = base_idx_spadix + i * n_su + ((j + 1) % n_su) + 1
            p3 = base_idx_spadix + (i + 1) * n_su + ((j + 1) % n_su) + 1
            p4 = base_idx_spadix + (i + 1) * n_su + j + 1
            faces.append((p1, p2, p3))
            faces.append((p1, p3, p4))

    # Cierre Apical (Semiesfera/Casquete)
    r_apex = spadix_r_base * 0.85
    y_apex = 1.0 * spadix_len + r_apex
    apex_pt = [
        0.0,
        y_apex * ca_p,
        y_apex * sa_p + 1.5
    ]
    vertices.append(apex_pt)
    colors.append(c_spadix.tolist())
    apex_spadix_idx = len(vertices)

    last_ring_spadix = base_idx_spadix + (n_sp - 1) * n_su
    for j in range(n_su):
        faces.append((last_ring_spadix + j + 1, last_ring_spadix + ((j + 1) % n_su) + 1, apex_spadix_idx))

    # =========================================================================
    # 3. PEDÚNCULO (Tallo basal con inserción limpia)
    # =========================================================================
    n_pt, n_pu = 12, 16
    t_ped = np.linspace(0.0, 1.0, n_pt)
    u_ped = np.linspace(0.0, 2.0 * math.pi, n_pu, endpoint=False)
    base_idx_ped = len(vertices)

    for tp in t_ped:
        r_ped = 3.5 * (1.0 + 0.1 * tp)
        # Eje Y negativo, partiendo de Y=0 (el nodo de unión)
        cy_ped = -tp * 80.0
        
        for up in u_ped:
            px = r_ped * math.cos(up)
            py = cy_ped
            pz = r_ped * math.sin(up) - 1.5  # Ajustado al lóbulo
            
            # Sombreado cilíndrico
            c_p = c_stem * (0.9 + 0.1 * math.cos(up))
            vertices.append([px, py, pz])
            colors.append(np.clip(c_p, 0.0, 1.0).tolist())

    for i in range(n_pt - 1):
        for j in range(n_pu):
            p1 = base_idx_ped + i * n_pu + j + 1
            p2 = base_idx_ped + i * n_pu + ((j + 1) % n_pu) + 1
            p3 = base_idx_ped + (i + 1) * n_pu + ((j + 1) % n_pu) + 1
            p4 = base_idx_ped + (i + 1) * n_pu + j + 1
            faces.append((p1, p2, p3))
            faces.append((p1, p3, p4))

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