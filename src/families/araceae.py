import os
import math
import numpy as np
from geometry import *


def _load_spathe_photometric_relief(photo_path, grid_size=128):
    """
    Segmenta la espata roja de la fotografia de campo mediante dominancia antocianica
    (R - max(G, B)) y extrae un mapa normalizado de alta frecuencia para matizar el color.
    """
    if not photo_path or not os.path.exists(photo_path):
        return None
    img = None
    try:
        from PIL import Image
        img = np.asarray(Image.open(photo_path).convert('RGB'), dtype=np.float32) / 255.0
    except Exception:
        try:
            import matplotlib.image as mpimg
            raw = mpimg.imread(photo_path)
            img = raw[..., :3].astype(np.float32)
            if img.max() > 1.0:
                img /= 255.0
        except Exception:
            return None

    redness = img[..., 0] - np.maximum(img[..., 1], img[..., 2])
    ys, xs = np.where(redness > 0.14)
    if len(xs) < 120:
        return None

    y0, y1 = int(ys.min()), int(ys.max()) + 1
    x0, x1 = int(xs.min()), int(xs.max()) + 1
    crop = img[y0:y1, x0:x1]
    lum = 0.299 * crop[..., 0] + 0.587 * crop[..., 1] + 0.114 * crop[..., 2]

    gy = np.linspace(0, lum.shape[0] - 1, grid_size).astype(int)
    gx = np.linspace(0, lum.shape[1] - 1, grid_size).astype(int)
    sampled = lum[np.ix_(gy, gx)]

    pad = np.pad(sampled, 4, mode='edge')
    smooth = sum(
        pad[4 + dy:4 + dy + grid_size, 4 + dx:4 + dx + grid_size]
        for dy in (-4, -2, 0, 2, 4) for dx in (-4, -2, 0, 2, 4)
    ) / 25.0
    high_pass = sampled - smooth
    std = float(np.std(high_pass))
    if std < 1e-5:
        return None
    return np.clip(high_pass / (2.5 * std), -1.0, 1.0)


def _add_closed_tube(pts, radii, cols, n_sl, vertices, colors, face_list, cap_start=True, cap_end=True):
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
            locules = math.sin(13 * th) * math.sin(55 * s * np.pi)
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
            primordia = (math.cos(26 * th) * math.cos(110 * s * np.pi)) ** 4
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


# =====================================================================================
#  Anthurium andraeanum  -  generador v3  (espata reticulada de venacion arqueada)
# =====================================================================================

def _ss(a, b, x):
    """smoothstep(a, b, x) vectorizado."""
    t = np.clip((np.asarray(x, dtype=float) - a) / (b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _lowfreq(x, y, seed=0.0):
    """Ruido suave determinista en [-1, 1] (suma de senos). Rompe la regularidad de 'tira de lavar'."""
    n = (np.sin(0.19 * x + 1.7 + seed) * np.cos(0.23 * y - 0.6 + 2.0 * seed)
         + 0.6 * np.sin(0.11 * x - 0.31 * y + 3.1 + seed)
         + 0.4 * np.cos(0.37 * x + 0.29 * y - 1.3 * seed))
    return np.clip(n / 1.6, -1.0, 1.0)


def _spathe_halfwidth(y, L, D, Wh, y_w, Ac, pU=1.8, qU=1.35, pL=1.9):
    """
    Semi-ancho de la espata a la altura y (mm, y=0 en el nodo, +y hacia el apice).
    y >= y_w : cuerpo ovado-acuminado (lados convexos que se vuelven concavos en el acumen)
    y <  y_w : lobulos basales redondeados (superelipse)
    """
    y = np.asarray(y, dtype=float)
    s = np.clip((y - y_w) / max(L - y_w, 1e-6), 0.0, 1.0)
    up = Wh * np.clip(1.0 - s ** pU, 0.0, 1.0) ** qU
    sa = np.clip((y - (L - Ac)) / max(Ac, 1e-6), 0.0, 1.0)
    up = up * (1.0 - 0.30 * _ss(0.0, 1.0, sa))
    eta = np.clip((y_w - y) / (y_w + D), 0.0, 1.0)
    lo = Wh * np.clip(1.0 - eta ** pL, 0.0, 1.0) ** (1.0 / pL)
    return np.where(y >= y_w, up, lo)


def _flower_lattice(s_vals, thetas, length_mm, radius_mm, n_flowers):
    """
    Distancia (mm, sobre la superficie) de cada vertice (s, theta) a la flor mas cercana (d1) y a la
    segunda mas cercana (d2) en una filotaxis espiral (angulo de divergencia 137.5 grados).
    Con 300-450 flores sale la red romboidal de parastiquios 5/8/13 de un espadice real.
    """
    golden = math.radians(137.50776)
    n = np.arange(n_flowers)
    z_f = (n + 0.5) / n_flowers * length_mm * 0.985
    th_f = (n * golden) % (2.0 * math.pi)
    d1 = np.zeros((len(s_vals), len(thetas)))
    d2 = np.zeros_like(d1)
    for i, s in enumerate(s_vals):
        z = s * length_mm
        lo = np.searchsorted(z_f, z - 4.2)
        hi = np.searchsorted(z_f, z + 4.2)
        lo, hi = max(0, lo - 1), min(n_flowers, hi + 1)
        dth = np.abs(thetas[:, None] - th_f[None, lo:hi])
        dth = np.minimum(dth, 2.0 * math.pi - dth) * radius_mm
        dd = dth ** 2 + (z - z_f[None, lo:hi]) ** 2
        part = np.partition(dd, 1, axis=1)
        d1[i] = np.sqrt(part[:, 0])
        d2[i] = np.sqrt(part[:, 1])
    return d1, d2


def _spadix_curve(n, length_mm, alpha_deg, bend_deg, m_vec, n_vec, start):
    """
    Eje del espadice. alpha = angulo respecto al nervio medio de la espata (dato: 22-83 grados, media 48),
    medido en el plano (m, n). El espadice se curva `bend_deg` hacia el apice de la espata (arqueo suave).
    """
    s = np.linspace(0.0, 1.0, n)
    ang = np.radians(alpha_deg + 0.5 * bend_deg - bend_deg * s)
    dirs = np.cos(ang)[:, None] * m_vec[None, :] + np.sin(ang)[:, None] * n_vec[None, :]
    ds = length_mm / (n - 1)
    pos = np.vstack([np.zeros(3), np.cumsum(0.5 * (dirs[1:] + dirs[:-1]) * ds, axis=0)])
    return start[None, :] + pos, s


def build_andraeanum_obj(cfg):
    c_cfg = cfg.get('perianto', {}).get('corola', {})
    g_cfg = cfg.get('gineceo', {})
    a_cfg = cfg.get('androceo', {})
    arq_cfg = cfg.get('arquitectura_floral', {})
    photo_path = cfg.get('colecta', {}).get('foto_campo', 'images/anthurium_andraeanum.jpg')
    photo_map = _load_spathe_photometric_relief(photo_path, grid_size=128)   # solo COLOR, ya no relieve

    # ---------------- parametros (mm / grados) ----------------
    L = float(c_cfg.get('longitud_limbo_mm', 118.0))            # nodo -> apice
    Wfull = float(c_cfg.get('ancho_petalo_mm', 98.0))           # ancho maximo total de la espata
    Wh = 0.5 * Wfull
    D = float(c_cfg.get('lobe_length_ratio', 0.32)) * L         # profundidad de los lobulos bajo el nodo
    Ac = float(np.clip(c_cfg.get('longitud_acumen_mm', 22.0), 8.0, 0.3 * L))
    wall = float(c_cfg.get('grosor_pared_mm', 1.2))
    sinus_open = float(c_cfg.get('seno_apertura_mm', 15.0))     # semi-abertura del seno en el fondo de los lobulos
    y_w = 0.14 * L                                              # altura del punto mas ancho
    p_sin = 1.6                                                 # borde interno del seno: x = a*|y|^1.6 (estrecho arriba, abierto abajo)
    a_sin = sinus_open / (D ** p_sin)

    pitch = math.radians(float(arq_cfg.get('angulo_espata_reflexa_grados', -38.0)))
    cp, sp = math.cos(pitch), math.sin(pitch)
    m_vec = np.array([0.0, cp, sp])        # direccion del nervio medio (nodo -> apice)
    n_vec = np.array([0.0, -sp, cp])       # normal adaxial (cara que mira al espadice)

    # paleta (RGB 0-1) medida sobre la imagen objetivo: p5 #890E11 | p50 #CE4754 | p75 #F0666A | p95 #E5A9AB
    c_body = np.array([0.78, 0.16, 0.23])
    c_cell = np.array([0.56, 0.05, 0.10])
    c_ridge = np.array([0.92, 0.42, 0.46])
    c_rim = np.array([0.94, 0.64, 0.66])
    c_abax = np.array([0.80, 0.30, 0.36])
    c_node = np.array([0.55, 0.60, 0.26])
    c_peduncle = np.array([0.24, 0.38, 0.14])
    c_collar = np.array([0.42, 0.22, 0.14])
    c_sp_base = np.array([0.86, 0.71, 0.58])     # #DAB593
    c_sp_mid = np.array([0.88, 0.77, 0.57])      # #E0C491
    c_sp_tip = np.array([0.90, 0.75, 0.26])      # amarillo apical (#E4C05D saturado)
    c_sp_ring = np.array([0.80, 0.54, 0.30])     # anillo ocre en la insercion
    c_pearl = np.array([0.97, 0.92, 0.79])
    c_androceo = np.array([0.98, 0.93, 0.52])
    c_ovary = np.array([0.80, 0.91, 0.66])
    c_ovule = np.array([0.98, 0.97, 0.88])
    c_axis = np.array([0.93, 0.90, 0.78])

    vertices, colors = [], []
    groups = {}

    # =====================================================================================
    # 1) ESPATA  (malla continua sin costura; adaxial + abaxial + bordes cerrados)
    # =====================================================================================
    yy_f = np.linspace(-D, 0.0, 4000)
    ok = _spathe_halfwidth(yy_f, L, D, Wh, y_w, Ac) >= a_sin * np.abs(yy_f) ** p_sin + 0.3
    y_min = float(yy_f[ok][0])                                  # esquina inferior de los lobulos

    dy = 1.0
    n_neg = max(10, int(round(-y_min / dy)))
    n_pos = max(40, int(round(L / dy)))
    y_rows = np.concatenate([np.linspace(y_min, 0.0, n_neg, endpoint=False), np.linspace(0.0, L, n_pos)])
    nr = len(y_rows)
    n_half = 52
    nc = 2 * n_half
    uh = np.linspace(0.0, 1.0, n_half)
    U = np.concatenate([uh[::-1], uh])
    S = np.concatenate([-np.ones(n_half), np.ones(n_half)])

    xo = _spathe_halfwidth(y_rows, L, D, Wh, y_w, Ac)[:, None]
    xi = np.where(y_rows < 0.0, a_sin * np.abs(y_rows) ** p_sin, 0.0)[:, None]
    cap = np.sqrt(2.0 * 40.0 * np.maximum(y_rows - y_min, 0.0))[:, None]          # esquina del lobulo redondeada
    xo = np.where(y_rows[:, None] < 0.0, xi + np.minimum(xo - xi, cap), xo)
    dxo_dy = np.gradient(xo[:, 0], y_rows)[:, None]
    YY = np.repeat(y_rows[:, None], nc, axis=1)
    u = np.repeat(U[None, :], nr, axis=0)
    side = np.repeat(S[None, :], nr, axis=0)
    XA = xi + u * (xo - xi)
    X = side * XA
    strip = np.maximum(xo - xi, 1e-6)
    t = np.clip(YY / L, -1.0, 1.0)
    tp = np.clip(t, 0.0, 1.0)
    r_node = np.sqrt(X ** 2 + YY ** 2)

    # ---- venacion: nervios primarios ARQUEADOS (siguen el margen) + peldaños transversales ----
    Kp = 4.0
    wq = 0.80
    q = np.clip(u, 0.0, 1.0) ** wq
    lane = q * Kp
    n_l = np.minimum(np.floor(lane), Kp - 1.0)
    a_fr = lane - n_l
    dq_du = wq * np.maximum(u, 0.04) ** (wq - 1.0)
    lane_w = np.maximum(strip / (Kp * dq_du), 0.3)              # ancho de cada carril en mm

    warp = _lowfreq(XA * 1.0, YY * 1.0, 0.7)
    d_p = np.minimum(a_fr, 1.0 - a_fr) * lane_w
    w_mid = 1.0 - 0.65 * np.exp(-(XA / 1.6) ** 2)               # nervio medio mas discreto
    R_prim = np.exp(-(d_p / 1.25) ** 2) * w_mid

    lam = 6.5 * (1.0 + 3.6 * (1.0 - (n_l + 0.5) / Kp) ** 1.9)   # peldaños: ~6.5 mm en el margen, ~25 mm al centro
    y_eff = YY + XA * dxo_dy * u                                # peldaño perpendicular al carril (siguen el arco)
    b = (y_eff + 4.5 * warp) / lam + 0.43 * n_l + 0.37 * (side > 0) + 0.18 * _lowfreq(YY, XA, 5.1)
    b_fr = b - np.floor(b)
    d_r = np.minimum(b_fr, 1.0 - b_fr) * lam
    R_rung = np.exp(-(d_r / 1.05) ** 2) * (0.75 + 0.25 * _lowfreq(YY * 0.7, XA * 0.7, 1.9))

    V = 1.0 - (1.0 - 0.85 * R_prim) * (1.0 - 0.75 * R_rung)               # mascara de nervios (0..1)
    cell = np.clip(1.0 - V, 0.0, 1.0) * np.sin(np.pi * a_fr) ** 0.5 * np.sin(np.pi * b_fr) ** 0.5

    rim = _ss(0.945, 0.995, u)
    env = _ss(2.5, 10.0, r_node) * (1.0 - 0.55 * _ss(0.88, 1.0, tp))
    z_rel = env * (0.95 * V - 2.0 * cell) + 0.9 * rim

    # ---- forma 3D de la lamina ----
    sa = np.clip((YY - (L - Ac)) / Ac, 0.0, 1.0)
    lobe_f = _ss(0.0, 1.0, np.clip(-YY / max(-y_min, 1e-6), 0.0, 1.0))
    lift = np.where(side < 0, 0.55, 0.20) * (-y_min)            # lobulo A se enrolla mas que el B
    z_lobe = lobe_f * lift * (0.35 + 0.65 * u ** 1.2)
    z_cup = 0.15 * Wh * u ** 2 * (1.0 - 0.6 * tp)
    z_long = -0.075 * L * tp ** 2
    z_acu = -0.22 * Ac * sa ** 2
    z_und = (0.020 * Wfull * u ** 3 * np.sin(2.0 * np.pi * YY / (0.30 * L) + 0.8 * side)
             + 0.012 * Wfull * u ** 3 * np.sin(2.0 * np.pi * YY / (0.17 * L) + 2.1))
    z_roll = 0.08 * X
    z_ad = z_cup + z_long + z_acu + z_lobe + z_und + z_roll + z_rel
    thick = wall * (0.95 - 0.40 * u ** 2) + 0.5 * np.exp(-(XA / 2.0) ** 2) * (1.0 - tp)
    z_ab = z_ad - thick

    y_ad = YY * cp - z_ad * sp
    zw_ad = YY * sp + z_ad * cp
    y_ab = YY * cp - z_ab * sp
    zw_ab = YY * sp + z_ab * cp

    # ---- color ----
    tint = np.zeros_like(u)
    if photo_map is not None:
        px = np.clip((0.5 + 0.48 * side * XA / max(Wh, 1.0)) * 127, 0, 127).astype(int)
        py = np.clip((1.0 - (YY - y_min) / (L - y_min)) * 127, 0, 127).astype(int)
        tint = photo_map[py, px]
    col = np.tile(c_body, (nr, nc, 1))
    col = (1 - 0.85 * cell[..., None] ** 1.0) * col + 0.85 * cell[..., None] ** 1.0 * c_cell
    col = (1 - 0.55 * (V * env)[..., None]) * col + 0.55 * (V * env)[..., None] * c_ridge
    col = (1 - 0.65 * rim[..., None]) * col + 0.65 * rim[..., None] * c_rim
    col = col * (1.0 + 0.07 * _lowfreq(XA, YY, 2.3) + 0.04 * tint)[..., None]
    nb = np.exp(-(r_node / 4.8) ** 2)[..., None]
    col_ad = np.clip((1 - 0.55 * nb) * col + 0.55 * nb * c_node, 0, 1)
    col_ab = np.clip((1 - 0.55 * V[..., None]) * c_abax + 0.55 * V[..., None] * np.array([0.90, 0.46, 0.50]), 0, 1)
    col_ab = np.clip((1 - 0.55 * nb) * col_ab + 0.55 * nb * c_node, 0, 1)

    # ---- indices (se sueldan las columnas centrales donde no hay seno) ----
    base = len(vertices)
    pos_ad = np.stack([X, y_ad, zw_ad], axis=-1).reshape(-1, 3)
    pos_ab = np.stack([X, y_ab, zw_ab], axis=-1).reshape(-1, 3)
    vertices.extend(pos_ad.tolist()); colors.extend(col_ad.reshape(-1, 3).tolist())
    vertices.extend(pos_ab.tolist()); colors.extend(col_ab.reshape(-1, 3).tolist())
    T_idx = np.arange(nr * nc).reshape(nr, nc) + base + 1
    B_idx = T_idx + nr * nc
    for i in range(nr):
        if y_rows[i] >= 0.0:
            T_idx[i, n_half] = T_idx[i, n_half - 1]
            B_idx[i, n_half] = B_idx[i, n_half - 1]

    f_spathe = []
    for i in range(nr - 1):
        both_neg = (y_rows[i] < 0.0) and (y_rows[i + 1] < 0.0)
        for j in range(nc - 1):
            if both_neg and j == n_half - 1:
                continue
            a, bb, c, d = T_idx[i, j], T_idx[i, j + 1], T_idx[i + 1, j + 1], T_idx[i + 1, j]
            f_spathe += [(a, bb, c), (a, c, d)]
            a, bb, c, d = B_idx[i, j], B_idx[i, j + 1], B_idx[i + 1, j + 1], B_idx[i + 1, j]
            f_spathe += [(a, c, bb), (a, d, c)]
        # bordes (cierran el grosor de la lamina)
        for j_edge, flip in ((0, False), (nc - 1, True)):
            Ti, Tn, Bi, Bn = T_idx[i, j_edge], T_idx[i + 1, j_edge], B_idx[i, j_edge], B_idx[i + 1, j_edge]
            if flip:
                f_spathe += [(Ti, Bi, Tn), (Bi, Bn, Tn)]
            else:
                f_spathe += [(Ti, Tn, Bi), (Bi, Tn, Bn)]
        if both_neg:   # bordes internos del seno
            for j_edge, flip in ((n_half - 1, True), (n_half, False)):
                Ti, Tn, Bi, Bn = T_idx[i, j_edge], T_idx[i + 1, j_edge], B_idx[i, j_edge], B_idx[i + 1, j_edge]
                if flip:
                    f_spathe += [(Ti, Bi, Tn), (Bi, Bn, Tn)]
                else:
                    f_spathe += [(Ti, Tn, Bi), (Bi, Tn, Bn)]
    # descarta triangulos degenerados (apice, esquinas del lobulo, nodo)
    V_arr = np.array(vertices)
    F = np.array(f_spathe, dtype=np.int64)
    p0, p1, p2 = V_arr[F[:, 0] - 1], V_arr[F[:, 1] - 1], V_arr[F[:, 2] - 1]
    area2 = np.linalg.norm(np.cross(p1 - p0, p2 - p0), axis=1)
    f_spathe = [tuple(r) for r in F[area2 > 1e-9].tolist()]
    groups['Espata_Cordiforme'] = f_spathe

    # =====================================================================================
    # 2) PEDUNCULO  (Bezier cubica: sale por el dorso del nodo y se endereza hacia abajo)
    # =====================================================================================
    Lp = float(arq_cfg.get('pedunculo_longitud_mm', 250.0))
    p0_ped = -n_vec * (wall * 0.95 + 0.6)
    p3_ped = p0_ped + np.array([0.0, -0.96 * Lp, -0.10 * Lp])
    p1_ped = p0_ped - n_vec * (0.16 * Lp) + np.array([0.05 * Lp, 0.0, 0.0])
    p2_ped = p3_ped + np.array([-0.05 * Lp, 0.34 * Lp, 0.04 * Lp])
    n_ped = 90
    tt = np.linspace(0.0, 1.0, n_ped)[:, None]
    ped_pts = ((1 - tt) ** 3 * p0_ped + 3 * (1 - tt) ** 2 * tt * p1_ped
               + 3 * (1 - tt) * tt ** 2 * p2_ped + tt ** 3 * p3_ped)
    arc = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(ped_pts, axis=0), axis=1))])
    ped_radii = 2.7 + 1.5 * np.exp(-arc / 14.0)
    ped_cols = np.zeros((n_ped, 3))
    for i in range(n_ped):
        k = math.exp(-arc[i] / 26.0) * 0.40
        ped_cols[i] = (1 - k) * c_peduncle + k * c_collar
    f_ped = []
    _add_closed_tube(ped_pts, ped_radii, ped_cols, 24, vertices, colors, f_ped, cap_start=True, cap_end=True)
    groups['Pedunculo_Tallo'] = f_ped

    # =====================================================================================
    # 3) ESPADICE  (curvo, filotaxis 137.5 grados, perlas = estigmas; capas internas concentricas)
    # =====================================================================================
    Ls = float(g_cfg.get('estilo_longitud_mm', 80.0))
    Rs = float(g_cfg.get('diametro_espadice_mm', 9.2)) / 2.0
    alpha = float(arq_cfg.get('angulo_espadice_grados', 58.0))
    bend = float(arq_cfg.get('espadice_curvatura_grados', 20.0))
    stipe_mm = float(arq_cfg.get('estipite_longitud_mm', 2.0))
    n_flow = int(a_cfg.get('estambres_numero', 400))

    def taper(s):
        s = np.asarray(s, dtype=float)
        body = 1.0 - 0.12 * np.clip(s / 0.90, 0, 1)
        cap = np.sqrt(np.clip(1.0 - ((s - 0.92) / 0.08) ** 2, 0.0, 1.0))
        out = np.where(s < 0.92, body, 0.88 * cap)
        return out * (1.0 + 0.10 * np.exp(-s / 0.02))

    d0 = math.cos(math.radians(alpha + 0.5 * bend)) * m_vec + math.sin(math.radians(alpha + 0.5 * bend)) * n_vec
    sp_start = (stipe_mm - 1.2) * d0

    # --- capa externa (alta resolucion) ---
    n_sp, n_sl = 210, 84
    pts_ext, s_ext = _spadix_curve(n_sp, Ls, alpha, bend, m_vec, n_vec, sp_start)
    th_ext = np.linspace(0.0, 2.0 * np.pi, n_sl, endpoint=False)
    d1, d2 = _flower_lattice(s_ext, th_ext, Ls, Rs, n_flow)
    S2 = s_ext[:, None]
    r_mean = Rs * taper(s_ext)[:, None]
    pearl_h = 0.55 * (1.0 - 0.40 * _ss(0.5, 0.9, S2))
    pearl = pearl_h * np.exp(-(d1 / 0.62) ** 1.6) * (1.0 - _ss(0.93, 1.0, S2))
    frame = (0.10 + 0.12 * _ss(0.4, 0.9, S2)) * np.exp(-((d2 - d1) / 0.22) ** 2) * (1.0 - _ss(0.93, 1.0, S2))
    r_ext = np.maximum(0.05, r_mean + pearl + frame)
    mix = _ss(0.40, 0.72, S2)
    base_c = (1 - mix[..., None]) * ((1 - _ss(0.0, 0.5, S2))[..., None] * c_sp_base + _ss(0.0, 0.5, S2)[..., None] * c_sp_mid) \
        + mix[..., None] * c_sp_tip
    ring = np.exp(-S2 / 0.025)[..., None]
    base_c = (1 - 0.7 * ring) * base_c + 0.7 * ring * c_sp_ring
    pw = (pearl / 0.55)[..., None] * (1.0 - 0.6 * _ss(0.5, 0.9, S2)[..., None])
    c_ext = np.clip((1 - 0.55 * pw) * base_c + 0.55 * pw * c_pearl - 0.05 * (frame / 0.2)[..., None], 0.0, 1.0)
    f_ext = []
    _add_closed_tube(pts_ext, r_ext, c_ext, n_sl, vertices, colors, f_ext, cap_start=True, cap_end=True)
    groups['Espadice_Florifero_Externo'] = f_ext

    # --- capas internas (resolucion media, solo visibles al disecar) ---
    n_in, n_sl_in = 110, 40
    pts_in, s_in = _spadix_curve(n_in, Ls, alpha, bend, m_vec, n_vec, sp_start)
    th_in = np.linspace(0.0, 2.0 * np.pi, n_sl_in, endpoint=False)
    e1, e2 = _flower_lattice(s_in, th_in, Ls, Rs, n_flow)
    S3 = s_in[:, None]
    rm_in = Rs * taper(s_in)[:, None]
    fade = (1.0 - _ss(0.90, 1.0, S3))

    r_and = np.maximum(0.03, rm_in * 0.90 + 0.30 * np.exp(-(e1 / 0.95) ** 2) * fade)
    c_and = np.clip(c_androceo * (0.88 + 0.18 * np.exp(-(e1 / 0.95) ** 2))[..., None], 0, 1)
    r_ov = np.maximum(0.02, rm_in * 0.72 + 0.22 * np.exp(-((e2 - e1) / 0.5) ** 2) * fade)
    c_ov = np.clip(c_ovary * (0.88 + 0.14 * np.exp(-((e2 - e1) / 0.5) ** 2))[..., None], 0, 1)
    r_ovm = np.maximum(0.02, rm_in * 0.45 + 0.55 * np.exp(-(e1 / 0.80) ** 2) * fade)
    c_ovm = np.clip(c_ovule * (0.86 + 0.16 * np.exp(-(e1 / 0.80) ** 2))[..., None], 0, 1)
    r_ax = np.maximum(0.03, rm_in[:, 0] * 0.22 + 0.06 * np.sin(s_in * 50.0 * np.pi) * (1.0 - s_in))
    c_ax = np.tile(c_axis, (n_in, 1))

    f_and, f_ov, f_ovm, f_ax = [], [], [], []
    _add_closed_tube(pts_in, r_and, c_and, n_sl_in, vertices, colors, f_and, cap_start=True, cap_end=True)
    _add_closed_tube(pts_in, r_ov, c_ov, n_sl_in, vertices, colors, f_ov, cap_start=True, cap_end=True)
    _add_closed_tube(pts_in, r_ovm, c_ovm, n_sl_in, vertices, colors, f_ovm, cap_start=True, cap_end=True)
    _add_closed_tube(pts_in, r_ax, c_ax, 16, vertices, colors, f_ax, cap_start=True, cap_end=True)
    groups['Androceo_Micro_Estambres'] = f_and
    groups['Gineceo_Ovarios'] = f_ov
    groups['Ovulos_Internos_Placentarios'] = f_ovm
    groups['Eje_Vascular_Interno'] = f_ax

    lines = []
    for v, c in zip(vertices, colors):
        lines.append(f'v {v[0]:.4f} {v[1]:.4f} {v[2]:.4f} {c[0]:.4f} {c[1]:.4f} {c[2]:.4f}' + NL)
    for grp_name, grp_faces in groups.items():
        lines.append(f'g {grp_name}' + NL)
        for f_idx in grp_faces:
            lines.append(f'f {f_idx[0]} {f_idx[1]} {f_idx[2]}' + NL)
    return ''.join(lines)


def build_araceae_inflorescence(cfg):
    especie = cfg.get('colecta', {}).get('especie', '').lower()
    disposicion = cfg.get('arquitectura_floral', {}).get('disposicion', 'erecta').lower()
    if 'sanjorgense' in especie or disposicion == 'pendula':
        return build_sanjorgense_original_obj(cfg)
    else:
        return build_andraeanum_obj(cfg)
