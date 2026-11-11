import math
import numpy as np
from geometry import *

def build_orchidaceae_flower(cfg):
    """
    Generador paramétrico organográfico para Cattleya trianae.
    Ajustes aplicados según directrices de campo:
    1. Color sólido RGB saturado (sin gradientes a blanco).
    2. Pétalos lisos abombados con ondas (sin(k*v)) atenuadas en el centro vía u^n.
    3. Labelo basal tubular (330°) cerrándose sobre una columna acortada.
    4. Expansión abrupta frontal del labelo con rizado festoneado estricto en el margen.
    """
    vertices, colors, faces = [], [], []

    # 1. CORRECCIÓN CROMÁTICA RADICAL (RGB directo, saturado, sin lavado)
    c_lilac   = np.array([0.86, 0.62, 0.88])  # Lila/Lavanda sólido y vibrante (Pétalos y Sépalos)
    c_magenta = np.array([0.75, 0.08, 0.55])  # Magenta profundo ininterrumpido (Frente del labelo)
    c_throat  = np.array([0.95, 0.85, 0.25])  # Amarillo/Crema cálido (Interior del tubo)
    
    c_column  = np.array([0.92, 0.90, 0.88])  # Columna blanca/marfil
    c_stem    = np.array([0.34, 0.52, 0.22])  # Tallo verde

    # =========================================================================
    # SÉPALOS (3): Perfiles lanceolados, lisos, color sólido
    # =========================================================================
    sepal_specs = [
        (90.0,  64.0, 11.0, -4.0, 0.0),
        (216.0, 58.0, 10.5, -7.0, 4.0),
        (324.0, 58.0, 10.5, -7.0, 4.0)
    ]
    for ang_deg, length, width, z_off, droop in sepal_specs:
        n_v, n_u = 35, 15
        v_vals = np.linspace(0.0, 1.0, n_v)
        u_vals = np.linspace(-1.0, 1.0, n_u)
        base_idx = len(vertices)
        rad = math.radians(ang_deg)
        ca, sa = math.cos(rad), math.sin(rad)

        for v in v_vals:
            w_prof = math.sin(math.pi * (v ** 0.75)) * (1.0 - 0.15 * (v ** 2))
            r_d = v * length
            for u in u_vals:
                w_loc = u * width * w_prof
                arch = 3.5 * math.sin(math.pi * v) - 1.5 * (u ** 2)
                px = r_d * ca - w_loc * sa
                py = r_d * sa + w_loc * ca - droop * (v ** 1.5)
                pz = z_off + arch
                
                # Color sólido sin gradientes a blanco
                vertices.append([px, py, pz])
                colors.append(c_lilac.tolist())

        for i in range(n_v - 1):
            for j in range(n_u - 1):
                p1 = base_idx + i * n_u + j + 1
                p2 = base_idx + i * n_u + (j + 1) + 1
                p3 = base_idx + (i + 1) * n_u + (j + 1) + 1
                p4 = base_idx + (i + 1) * n_u + j + 1
                faces.append((p1, p2, p3))
                faces.append((p1, p3, p4))

    # =========================================================================
    # PÉTALOS LATERALES (2): Cuerpo liso, ondas atenuadas u^n en márgenes
    # =========================================================================
    for side in [1.0, -1.0]:
        n_v, n_u = 55, 35
        v_vals = np.linspace(0.0, 1.0, n_v)
        u_vals = np.linspace(-1.0, 1.0, n_u)
        base_idx = len(vertices)
        rad = math.radians(16.0 if side > 0 else 164.0)
        ca, sa = math.cos(rad), math.sin(rad)
        p_len, p_w = 64.0, 31.0

        for v in v_vals:
            w_prof = math.sin(math.pi * (v ** 0.65))
            r_d = v * p_len
            for u in u_vals:
                abs_u = abs(u)
                
                # TOPOLOGÍA: Atenuador polinómico (u^3) para aislar la onda en el borde
                # El centro (u=0) queda multiplicado por 0 (liso).
                edge_mask = (abs_u ** 3.0) * np.clip((v - 0.1) / 0.9, 0.0, 1.0)
                wave_w = 3.0 * edge_mask * math.sin(10.0 * math.pi * v)
                wave_z = 4.5 * edge_mask * math.cos(12.0 * math.pi * v + 2.0 * side * u)
                
                # Cuerpo suavemente abombado
                dome = 5.5 * math.sin(math.pi * v) * (1.0 - (u ** 2))

                w_loc = u * p_w * w_prof + wave_w
                px = r_d * ca - w_loc * sa
                py = r_d * sa + w_loc * ca - 4.5 * (v ** 1.8)
                pz = 1.5 + dome + wave_z

                vertices.append([px, py, pz])
                colors.append(c_lilac.tolist())

        for i in range(n_v - 1):
            for j in range(n_u - 1):
                p1 = base_idx + i * n_u + j + 1
                p2 = base_idx + i * n_u + (j + 1) + 1
                p3 = base_idx + (i + 1) * n_u + (j + 1) + 1
                p4 = base_idx + (i + 1) * n_u + j + 1
                faces.append((p1, p2, p3))
                faces.append((p1, p3, p4))

    # =========================================================================
    # LABELO: Tubo cerrado 330° -> Expansión abrupta frontal
    # =========================================================================
    n_lv, n_lu = 65, 55
    v_lab = np.linspace(0.0, 1.0, n_lv)
    u_lab = np.linspace(-1.0, 1.0, n_lu)
    base_idx_lab = len(vertices)

    for v in v_lab:
        # Mezclador: 0.0 (Tubo), 1.0 (Expansión)
        flare = np.clip((v - 0.45) / 0.25, 0.0, 1.0)
        
        # Ángulo de cierre transversal: 165° por lado (330° total) en la base
        # Se abre hacia adelante a medida que 'flare' aumenta
        max_ang = math.radians(165.0 - 75.0 * flare)
        
        # Radios y caídas
        r_tube = 4.0 + 8.5 * v
        w_flare = 14.0 + 38.0 * (v - 0.45)**1.5 if v > 0.45 else 0.0
        
        cy = -v * 20.0 - flare * 32.0 * (v - 0.45)
        cz = 4.0 + v * 24.0 - flare * 18.0 * (v - 0.45)

        for u in u_lab:
            abs_u = abs(u)
            theta = u * max_ang

            # Modo Tubo (Cilíndrico paramétrico)
            tx = r_tube * math.sin(theta)
            ty = cy - r_tube * math.cos(theta)
            tz = cz + r_tube * 0.25 * math.cos(theta)

            # Modo Expansión (Lámina deflexa)
            fx = u * w_flare
            fy = cy - 6.0 * (1.0 - (u ** 2))
            fz = cz + 6.0 * (1.0 - (u ** 2))

            # Fusión interpolada
            px = (1.0 - flare) * tx + flare * fx
            py = (1.0 - flare) * ty + flare * fy
            pz = (1.0 - flare) * tz + flare * fz

            # Rizado Festoneado: Exclusivo del borde (abs_u^3) y zona frontal (flare)
            ruffle_mask = flare * (abs_u ** 3.0)
            ruffle_z = 4.5 * ruffle_mask * math.sin(18.0 * math.pi * u + 6.0 * math.pi * v)
            pz += ruffle_z
            py += ruffle_z * 0.4

            # --- COLOR CROMÁTICO CONFINADO ---
            # Garganta amarilla/crema confinada al tubo
            throat_mask = math.exp(-((v - 0.35) / 0.25)**2 - (abs_u / 0.6)**2)
            # Magenta frontal hasta el borde (sin franja blanca)
            magenta_mask = np.clip((v - 0.45) / 0.20, 0.0, 1.0) * (1.0 - 0.7 * throat_mask)

            col = np.copy(c_lilac)
            col = (1.0 - throat_mask) * col + throat_mask * c_throat
            col = (1.0 - magenta_mask) * col + magenta_mask * c_magenta

            vertices.append([px, py, pz])
            colors.append(np.clip(col, 0.0, 1.0).tolist())

    for i in range(n_lv - 1):
        for j in range(n_lu - 1):
            p1 = base_idx_lab + i * n_lu + j + 1
            p2 = base_idx_lab + i * n_lu + (j + 1) + 1
            p3 = base_idx_lab + (i + 1) * n_lu + (j + 1) + 1
            p4 = base_idx_lab + (i + 1) * n_lu + j + 1
            faces.append((p1, p2, p3))
            faces.append((p1, p3, p4))

    # =========================================================================
    # COLUMNA (Ginostemio): Acortada 20% para quedar resguardada en el tubo
    # =========================================================================
    n_col = 15
    t_col = np.linspace(0.0, 1.0, n_col)
    col_pts = np.column_stack([
        np.zeros(n_col),
        -t_col * 12.0,  # Longitud reducida de 15 a 12
        4.0 + t_col * 6.5 + 1.0 * np.sin(t_col * np.pi)
    ])
    col_radii = 2.4 * (1.0 - 0.15 * t_col)
    col_cols = np.tile(c_column, (n_col, 1))
    add_tube_along_curve(col_pts, col_radii, col_cols, 14, vertices, colors, faces)

    # =========================================================================
    # OVARIO / PEDICELO VERDE
    # =========================================================================
    n_st = 20
    t_st = np.linspace(0.0, 1.0, n_st)
    stem_pts = np.column_stack([
        5.0 * np.sin(t_st * math.pi * 0.6),
        -4.0 - t_st * 40.0,
        1.0 - 8.0 * t_st
    ])
    stem_radii = np.linspace(2.8, 2.2, n_st)
    stem_cols = np.tile(c_stem, (n_st, 1))
    add_tube_along_curve(stem_pts, stem_radii, stem_cols, 14, vertices, colors, faces)

    lines = []
    for v, c in zip(vertices, colors):
        lines.append(f"v {v[0]:.4f} {v[1]:.4f} {v[2]:.4f} {c[0]:.4f} {c[1]:.4f} {c[2]:.4f}" + NL)
    for f_idx in faces:
        lines.append(f"f {f_idx[0]} {f_idx[1]} {f_idx[2]}" + NL)
    return "".join(lines)