import math
import numpy as np
from geometry import *

def build_orchidaceae_flower(cfg):
    """
    Generador paramétrico organográfico para Cattleya trianae.
    - Topología: Geometría estable de main (ondas u^3, labelo convoluto estricto).
    - Color: Gradientes radiales fotográficos (amarillo -> fucsia -> lila).
    - Formato: Disección interactiva (grupos 'g' anatómicos y ovario interno).
    """
    vertices, colors = [], []
    groups = {}

    # Paleta de color base (con gradientes)
    c_lilac   = np.array([0.88, 0.72, 0.92])  # Lila suave (bordes y tépalos)
    c_purple  = np.array([0.68, 0.08, 0.48])  # Fucsia/Púrpura vibrante (centro labelo)
    c_yellow  = np.array([0.98, 0.88, 0.15])  # Amarillo cálido (garganta)
    c_column  = np.array([0.92, 0.90, 0.88])
    c_ovary   = np.array([0.34, 0.52, 0.22])
    c_ovules  = np.array([0.98, 0.95, 0.75])

    # =========================================================================
    # 1. OVARIO ÍNFERO Y PLACENTACIÓN (Módulo de Rayos X)
    # =========================================================================
    f_ovary, f_ovules = [], []
    
    # Ovario externo (acanalado)
    n_ped, sides_ped = 20, 18
    t_ped = np.linspace(0.0, 1.0, n_ped)
    ped_pts = np.column_stack([
        5.0 * np.sin(t_ped * math.pi * 0.6),
        -4.0 - t_ped * 36.0,
        1.0 - 8.0 * t_ped
    ])
    radii_ped = np.zeros((n_ped, sides_ped))
    cols_ped = np.zeros((n_ped, sides_ped, 3))
    theta_ped = np.linspace(0, 2 * np.pi, sides_ped, endpoint=False)
    for i, t in enumerate(t_ped):
        r_base = 3.2 * (1.0 - 0.2 * t)
        for j, th in enumerate(theta_ped):
            rib = 0.3 * math.cos(6.0 * th)
            radii_ped[i, j] = r_base + rib
            cols_ped[i, j] = np.clip(c_ovary * (0.9 + 0.15 * math.cos(6.0 * th)), 0.0, 1.0)
    add_tube_along_curve(ped_pts, radii_ped, cols_ped, sides_ped, vertices, colors, f_ovary)
    groups["Ovario_Infero"] = f_ovary

    # Óvulos internos (Placentación)
    n_ov = 16
    t_ov = np.linspace(0.1, 0.8, n_ov)
    for plac_idx in range(3):
        ang_p = plac_idx * (2.0 * np.pi / 3.0)
        ov_pts = np.column_stack([
            ped_pts[2:18, 0] + 1.2 * math.cos(ang_p),
            ped_pts[2:18, 1] + 1.2 * math.sin(ang_p),
            ped_pts[2:18, 2]
        ])
        add_tube_along_curve(ov_pts, np.full(16, 0.8), np.tile(c_ovules, (16, 1)), 8, vertices, colors, f_ovules)
    groups["Ovulos_Placentacion"] = f_ovules

    # =========================================================================
    # 2. SÉPALOS (Topología estable, Color suave)
    # =========================================================================
    sepal_specs = [
        ("Sepalo_Dorsal", 90.0, 64.0, 11.0, -4.0, 0.0),
        ("Sepalo_Lateral_Izq", 216.0, 58.0, 10.5, -7.0, 4.0),
        ("Sepalo_Lateral_Der", 324.0, 58.0, 10.5, -7.0, 4.0)
    ]
    for grp_name, ang_deg, length, width, z_off, droop in sepal_specs:
        f_sep = []
        n_v, n_u = 30, 12
        v_vals = np.linspace(0.0, 1.0, n_v)
        u_vals = np.linspace(-1.0, 1.0, n_u)
        base_idx = len(vertices)
        ca, sa = math.cos(math.radians(ang_deg)), math.sin(math.radians(ang_deg))

        for v in v_vals:
            w_prof = math.sin(math.pi * (v ** 0.75)) * (1.0 - 0.15 * (v ** 2))
            r_d = v * length
            for u in u_vals:
                w_loc = u * width * w_prof
                px = r_d * ca - w_loc * sa
                py = r_d * sa + w_loc * ca - droop * (v ** 1.5)
                pz = z_off + 3.5 * math.sin(math.pi * v) - 1.5 * (u ** 2)
                
                glow = 1.0 - 0.08 * abs(u) # Ligero gradiente hacia el centro
                vertices.append([px, py, pz])
                colors.append(np.clip(c_lilac * glow, 0.0, 1.0).tolist())

        for i in range(n_v - 1):
            for j in range(n_u - 1):
                p1 = base_idx + i * n_u + j + 1
                p2 = base_idx + i * n_u + (j + 1) + 1
                p3 = base_idx + (i + 1) * n_u + (j + 1) + 1
                p4 = base_idx + (i + 1) * n_u + j + 1
                f_sep.append((p1, p2, p3))
                f_sep.append((p1, p3, p4))
        groups[grp_name] = f_sep

    # =========================================================================
    # 3. PÉTALOS LATERALES (Ondas u^3, Color suave)
    # =========================================================================
    petal_specs = [
        ("Petalo_Lateral_Der", 16.0, 1.0),
        ("Petalo_Lateral_Izq", 164.0, -1.0)
    ]
    for grp_name, ang_deg, side in petal_specs:
        f_pet = []
        n_v, n_u = 45, 25
        v_vals = np.linspace(0.0, 1.0, n_v)
        u_vals = np.linspace(-1.0, 1.0, n_u)
        base_idx = len(vertices)
        ca, sa = math.cos(math.radians(ang_deg)), math.sin(math.radians(ang_deg))

        for v in v_vals:
            w_prof = math.sin(math.pi * (v ** 0.65))
            r_d = v * 64.0
            for u in u_vals:
                abs_u = abs(u)
                edge_mask = (abs_u ** 3.0) * np.clip((v - 0.1) / 0.9, 0.0, 1.0)
                wave_w = 3.0 * edge_mask * math.sin(10.0 * math.pi * v)
                wave_z = 4.5 * edge_mask * math.cos(12.0 * math.pi * v + 2.0 * side * u)
                
                w_loc = u * 31.0 * w_prof + wave_w
                px = r_d * ca - w_loc * sa
                py = r_d * sa + w_loc * ca - 4.5 * (v ** 1.8)
                pz = 1.5 + 5.5 * math.sin(math.pi * v) * (1.0 - (u ** 2)) + wave_z

                glow = 1.0 - 0.12 * abs_u
                vertices.append([px, py, pz])
                colors.append(np.clip(c_lilac * glow, 0.0, 1.0).tolist())

        for i in range(n_v - 1):
            for j in range(n_u - 1):
                p1 = base_idx + i * n_u + j + 1
                p2 = base_idx + i * n_u + (j + 1) + 1
                p3 = base_idx + (i + 1) * n_u + (j + 1) + 1
                p4 = base_idx + (i + 1) * n_u + j + 1
                f_pet.append((p1, p2, p3))
                f_pet.append((p1, p3, p4))
        groups[grp_name] = f_pet

    # =========================================================================
    # 4. LABELO (Topología estricta u^3 + Gradiente Radial Fucsia/Amarillo)
    # =========================================================================
    f_lip = []
    n_lv, n_lu = 60, 50
    v_lab = np.linspace(0.0, 1.0, n_lv)
    u_lab = np.linspace(-1.0, 1.0, n_lu)
    base_idx_lab = len(vertices)

    for v in v_lab:
        flare = np.clip((v - 0.45) / 0.25, 0.0, 1.0)
        max_ang = math.radians(165.0 - 75.0 * flare)
        r_tube = 4.0 + 8.5 * v
        w_flare = 14.0 + 38.0 * (v - 0.45)**1.5 if v > 0.45 else 0.0
        
        cy = -v * 20.0 - flare * 32.0 * (v - 0.45)
        cz = 4.0 + v * 24.0 - flare * 18.0 * (v - 0.45)

        for u in u_lab:
            abs_u = abs(u)
            theta = u * max_ang

            tx = r_tube * math.sin(theta)
            ty = cy - r_tube * math.cos(theta)
            tz = cz + r_tube * 0.25 * math.cos(theta)

            fx = u * w_flare
            fy = cy - 6.0 * (1.0 - (u ** 2))
            fz = cz + 6.0 * (1.0 - (u ** 2))

            px = (1.0 - flare) * tx + flare * fx
            py = (1.0 - flare) * ty + flare * fy
            pz = (1.0 - flare) * tz + flare * fz

            ruffle_mask = flare * (abs_u ** 3.0)
            ruffle_z = 4.5 * ruffle_mask * math.sin(18.0 * math.pi * u + 6.0 * math.pi * v)
            pz += ruffle_z
            py += ruffle_z * 0.4

            # --- COLOR RADIAL HEREDADO DE LA FOTO FAVORITA ---
            # Distancia desde el centro/garganta hacia los bordes
            radial = math.sqrt((u * 0.9)**2 + (max(0.0, (v - 0.35) / 0.65))**2)
            
            if radial < 0.40:
                col = c_yellow
            elif radial < 0.75:
                mix = (radial - 0.40) / 0.35
                col = (1.0 - mix) * c_yellow + mix * c_purple
            else:
                mix = min(1.0, (radial - 0.75) / 0.25)
                col = (1.0 - mix) * c_purple + mix * c_lilac

            vertices.append([px, py, pz])
            colors.append(col.tolist())

    for i in range(n_lv - 1):
        for j in range(n_lu - 1):
            p1 = base_idx_lab + i * n_lu + j + 1
            p2 = base_idx_lab + i * n_lu + (j + 1) + 1
            p3 = base_idx_lab + (i + 1) * n_lu + (j + 1) + 1
            p4 = base_idx_lab + (i + 1) * n_lu + j + 1
            f_lip.append((p1, p2, p3))
            f_lip.append((p1, p3, p4))
    groups["Labelo_Trilobulado"] = f_lip

    # =========================================================================
    # 5. GINOSTEMIO (Columna corta protegida) y ANTERA
    # =========================================================================
    f_col, f_ant = [], []
    n_col = 15
    t_col = np.linspace(0.0, 1.0, n_col)
    col_pts = np.column_stack([
        np.zeros(n_col),
        -t_col * 12.0,
        4.0 + t_col * 6.5 + 1.0 * np.sin(t_col * np.pi)
    ])
    add_tube_along_curve(col_pts, 2.4 * (1.0 - 0.15 * t_col), np.tile(c_column, (n_col, 1)), 12, vertices, colors, f_col)
    groups["Ginostemio_Columna"] = f_col

    ant_pt = col_pts[-1]
    ant_pts = np.array([ant_pt, [ant_pt[0], ant_pt[1] - 1.8, ant_pt[2] + 0.8]])
    add_tube_along_curve(ant_pts, np.array([1.8, 1.0]), np.tile(np.array([0.9, 0.7, 0.1]), (2, 1)), 8, vertices, colors, f_ant)
    groups["Antera_Polinios"] = f_ant

    # =========================================================================
    # CONSTRUCCIÓN DEL OBJ MODULAR
    # =========================================================================
    lines = []
    for v, c in zip(vertices, colors):
        lines.append(f"v {v[0]:.4f} {v[1]:.4f} {v[2]:.4f} {c[0]:.4f} {c[1]:.4f} {c[2]:.4f}" + NL)
    
    for grp_name, grp_faces in groups.items():
        lines.append(f"g {grp_name}" + NL)
        for f_idx in grp_faces:
            lines.append(f"f {f_idx[0]} {f_idx[1]} {f_idx[2]}" + NL)

    return "".join(lines)