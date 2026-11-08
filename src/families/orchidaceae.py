import math
import numpy as np
from geometry import *

def build_orchidaceae_flower(cfg):
    c_cfg = cfg['perianto']['corola']
    a_cfg = cfg.get('androceo', {})
    g_cfg = cfg.get('gineceo', {})

    l_petal = float(c_cfg.get('longitud_limbo_mm', 85.0))
    w_petal = float(c_cfg.get('ancho_petalo_mm', 60.0))
    l_sepal = l_petal * 0.98
    w_sepal = w_petal * 0.36
    l_lip = float(c_cfg.get('longitud_tubo_mm', 72.0))
    w_lip = float(c_cfg.get('ancho_labelo_mm', 55.0))

    c_lilac = np_hex_to_rgb(cfg['perianto']['caliz'].get('color_hex', '#D8B8E8'))
    c_yellow = np_hex_to_rgb(c_cfg.get('color_garganta_hex', '#FFB703'))
    c_purple = np_hex_to_rgb(c_cfg.get('color_limbo_hex', '#9E1256'))
    c_column = np_hex_to_rgb(a_cfg.get('color_filamento_hex', '#F8F5F2'))
    c_ovary = np_hex_to_rgb(g_cfg.get('color_ovario_hex', '#5A8A34'))

    vertices, colors, faces = [], [], []
    base_idx = 0

    # 1. Ovario pedicelado
    n_ped, sides_ped = 16, 6
    t_ped = np.linspace(0.0, 1.0, n_ped)
    ped_pts = np.column_stack([np.zeros(n_ped), -t_ped * 28.0, -t_ped * 45.0 + 5.0 * np.sin(t_ped * np.pi)])
    add_tube_along_curve(ped_pts, np.linspace(2.8, 3.6, n_ped), np.tile(c_ovary, (n_ped, 1)), sides_ped, vertices, colors, faces)
    base_idx = len(vertices)

    # 2. Sepalos lanceolados (dorsal vertical + 2 laterales)
    sepal_angles = [np.pi / 2.0, -np.pi * 0.18, -np.pi * 0.82]
    ru_s, rv_s = 20, 8
    u_vals_s = np.linspace(0.0, 1.0, ru_s + 1)
    v_vals_s = np.linspace(-0.5, 0.5, rv_s + 1)
    for base_ang in sepal_angles:
        ca, sa = np.cos(base_ang), np.sin(base_ang)
        for u in u_vals_s:
            r = 3.0 + l_sepal * u
            w_loc = (w_sepal / 2.0) * np.sin(np.pi * (u ** 0.72)) * (1.0 - 0.2 * u)
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

    # 3. Petalos laterales ondulados (amplios)
    petal_angles = [np.radians(14.0), np.radians(166.0)]
    ru_p, rv_p = 24, 16
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
                ruffle = 4.5 * edge_factor * math.sin(8.0 * np.pi * u + (2.0 if is_left else 0.0))
                px = r * ca - lat * sa
                py = r * sa + lat * ca
                pz = arch_z + ruffle - 2.8 * (v * v)
                center_glow = 1.0 - 0.12 * (abs(v) / 0.5)
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

    # 4. LABELO COMPLETO (Tubo + Limbo frontal fucsia/amarillo rizado)
    ru_l, rv_l = 32, 24
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
                px = tube_radius * math.sin(theta)
                py = y_center - tube_radius * 0.48 * (1.0 - math.cos(theta))
                pz = z_center + tube_radius * math.cos(theta)
                col = c_yellow if abs(v) < 0.3 else c_lilac
            else:
                t_flare = (u - 0.42) / 0.58
                lat = v * 2.0 * lip_width
                edge_factor = (abs(v) / 0.5) ** 1.6
                ruffle = 5.5 * edge_factor * math.sin(11.0 * math.pi * t_flare + v * 14.0)
                notch = -6.0 * (u - 0.82) / 0.18 * (1.0 - abs(v) / 0.16) if (abs(v) < 0.16 and u > 0.82) else 0.0
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

    # 5. Ginostemio (Columna arqueada protegida por el labelo)
    l_col = float(a_cfg.get('filamento_longitud_mm', 32.0))
    n_col = 16
    t_col = np.linspace(0.0, 1.0, n_col)
    col_pts = np.column_stack([np.zeros(n_col), -t_col * l_col * 0.72, 3.5 + t_col * 15.0 - 5.0 * (t_col ** 2)])
    add_tube_along_curve(col_pts, np.linspace(3.6, 2.6, n_col), np.tile(c_column, (n_col, 1)), 10, vertices, colors, faces)
    ant_pt = col_pts[-1]
    ant_pts = np.array([ant_pt, [ant_pt[0], ant_pt[1] - 2.8, ant_pt[2] + 0.8]])
    c_anther = np_hex_to_rgb(a_cfg.get('color_antera_hex', '#F4D03F'))
    add_tube_along_curve(ant_pts, np.array([2.4, 1.2]), np.tile(c_anther, (2, 1)), 8, vertices, colors, faces)

    lines = []
    for v, c in zip(vertices, colors):
        lines.append(f"v {v[0]:.4f} {v[1]:.4f} {v[2]:.4f} {c[0]:.4f} {c[1]:.4f} {c[2]:.4f}" + NL)
    for f_idx in faces:
        lines.append(f"f {f_idx[0]} {f_idx[1]} {f_idx[2]}" + NL)
    return "".join(lines)

