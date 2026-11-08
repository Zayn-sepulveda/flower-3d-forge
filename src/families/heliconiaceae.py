import math
import numpy as np
from geometry import *

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

