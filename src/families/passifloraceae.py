import math
import numpy as np
from geometry import *

def build_passiflora_flower(cfg):
    obj_data = ""
    v_offset = 1
    is_incarnata = "incarnata" in cfg['colecta']['especie'].lower()

    corola = cfg.get('perianto', {}).get('corola', {})
    l_petal = float(corola.get('longitud_limbo_mm', 42.0))
    w_petal = float(corola.get('ancho_petalo_mm', 18.0))
    l_sepal = l_petal * 1.04

    obj_data += "usemtl Mat_Caliz" + NL
    ped_pts = [
        (0.0, -38.0, -8.0),
        (0.0, -30.0, -7.0),
        (0.0, -22.0, -5.0),
        (0.0, -15.0, -2.5),
        (0.0, -9.0, 0.0)
    ]
    seg_ped, v_offset = add_tube(ped_pts, 1.8, 2.2, 12, v_offset)
    obj_data += seg_ped

    n_cup_rings, sides_cup = 8, 20
    for i in range(n_cup_rings):
        t = i / (n_cup_rings - 1)
        y_c = -9.0 + t * 9.0
        r_c = 2.2 + 5.8 * math.sin(t * math.pi * 0.5)
        for s in range(sides_cup):
            ang = s * (2.0 * math.pi / sides_cup)
            rib = 1.0 + 0.05 * math.cos(10 * ang)
            px = r_c * rib * math.cos(ang)
            pz = r_c * rib * math.sin(ang)
            obj_data += build_vertex(px, y_c, pz)

    for i in range(n_cup_rings - 1):
        for s in range(sides_cup):
            p1 = v_offset + i * sides_cup + s
            p2 = v_offset + i * sides_cup + (s + 1) % sides_cup
            p3 = v_offset + (i + 1) * sides_cup + s
            p4 = v_offset + (i + 1) * sides_cup + (s + 1) % sides_cup
            obj_data += build_face(p1, p2, p3)
            obj_data += build_face(p2, p4, p3)
    v_offset += n_cup_rings * sides_cup

    obj_data += "usemtl Mat_CorolaLimbo" + NL
    ru, rv = 16, 8

    for whorl in ['sepal', 'petal']:
        length = l_sepal if whorl == 'sepal' else l_petal
        width = w_petal * (1.05 if whorl == 'sepal' else 0.95)
        offset_angle = 0.0 if whorl == 'sepal' else (math.pi / 5.0)
        y_layer = -0.8 if whorl == 'sepal' else 0.0

        for k in range(5):
            base_ang = k * (2.0 * math.pi / 5.0) + offset_angle
            ca, sa = math.cos(base_ang), math.sin(base_ang)

            for i in range(ru + 1):
                u = i / ru
                r = 7.5 + length * u

                if u < 0.18:
                    w_profile = (u / 0.18) ** 0.55
                elif u < 0.82:
                    w_profile = 1.0
                else:
                    t_tip = (u - 0.82) / 0.18
                    w_profile = math.sqrt(max(0.001, 1.0 - t_tip * t_tip))

                w_local = (width / 2.0) * w_profile
                arch_y = y_layer + 3.8 * math.sin(math.pi * u * 0.6) - 16.0 * (u ** 2.2)

                for j in range(rv + 1):
                    v = (j / rv) - 0.5
                    lat = v * 2.0 * w_local
                    cup = -1.4 * (v * v) * (1.0 - u * 0.3)

                    px = r * ca - lat * sa
                    pz = r * sa + lat * ca
                    py = arch_y + cup

                    if whorl == 'sepal' and 0.80 < u < 0.94 and abs(v) < 0.18:
                        py += 2.2 * math.sin((u - 0.80) / 0.14 * math.pi)

                    obj_data += build_vertex(px, py, pz)

            for i in range(ru):
                for j in range(rv):
                    p1 = v_offset + i * (rv + 1) + j
                    p2 = p1 + 1
                    p3 = p1 + (rv + 1)
                    p4 = p3 + 1
                    obj_data += build_face(p1, p2, p3)
                    obj_data += build_face(p2, p4, p3)
            v_offset += (ru + 1) * (rv + 1)

    l_filam = float(corola.get('longitud_tubo_mm', 36.0))
    series_radii = [7.2, 6.4, 5.6]
    series_counts = [72, 72, 48] if is_incarnata else [64, 48, 36]

    for s_idx, (r_start, num_fil) in enumerate(zip(series_radii, series_counts)):
        scale_len = 1.0 - (s_idx * 0.14)
        for i in range(num_fil):
            angle = i * (2.0 * math.pi / num_fil) + (s_idx * 0.05)
            pts_dark, pts_white, pts_tip = [], [], []
            steps = 18

            for j in range(steps):
                u = j / (steps - 1)
                d_theta, d_y = 0.0, 0.0
                if is_incarnata and u > 0.32:
                    d_theta = 0.26 * ((u - 0.32) ** 1.2) * math.sin(12.0 * math.pi * u + (i % 7) * 1.1)
                    d_y = 3.6 * ((u - 0.32) ** 1.5) * math.cos(9.0 * math.pi * u + (i % 5) * 0.8)

                elev = 1.8 * math.sin(u * math.pi) + d_y - 2.5 * (u ** 2)
                r_ext = r_start + l_filam * scale_len * u
                ang = angle + d_theta
                pt = (r_ext * math.cos(ang), 0.6 + elev, r_ext * math.sin(ang))

                if u <= 0.30:
                    pts_dark.append(pt)
                if 0.26 <= u <= 0.58:
                    pts_white.append(pt)
                if u >= 0.54:
                    pts_tip.append(pt)

            obj_data += "usemtl Mat_CorolaGarganta" + NL
            seg1, v_offset = add_tube(pts_dark, 0.46, 0.36, 4, v_offset)
            obj_data += seg1

            obj_data += "usemtl Mat_Blanco" + NL
            seg2, v_offset = add_tube(pts_white, 0.36, 0.28, 4, v_offset)
            obj_data += seg2

            obj_data += "usemtl Mat_CoronaVioleta" + NL
            seg3, v_offset = add_tube(pts_tip, 0.28, 0.10, 4, v_offset)
            obj_data += seg3

    obj_data += "usemtl Mat_CorolaGarganta" + NL
    for i in range(48):
        ang = i * (2.0 * math.pi / 48.0)
        pts_op = [
            (4.8 * math.cos(ang), 0.6, 4.8 * math.sin(ang)),
            (5.6 * math.cos(ang), 3.2, 5.6 * math.sin(ang)),
            (5.0 * math.cos(ang), 5.5, 5.0 * math.sin(ang))
        ]
        seg_op, v_offset = add_tube(pts_op, 0.38, 0.14, 4, v_offset)
        obj_data += seg_op

    androceo = cfg.get('androceo') or {}
    gineceo = cfg.get('gineceo') or {}
    l_androg = float(androceo.get('filamento_longitud_mm', 22.0))
    w_androg = float(androceo.get('filamento_grosor_mm', 2.2)) / 2.0

    obj_data += "usemtl Mat_Estilo" + NL
    col_pts = [(0, i * (l_androg / 10.0), 0) for i in range(11)]
    seg_col, v_offset = add_tube(col_pts, w_androg * 1.1, w_androg * 0.92, 12, v_offset)
    obj_data += seg_col

    l_antera = float(androceo.get('antera_longitud_mm', 8.0))
    for i in range(5):
        a = i * (2.0 * math.pi / 5.0)
        ca, sa = math.cos(a), math.sin(a)
        arm_pts = [
            (0, l_androg, 0),
            (4.0 * ca, l_androg + 1.2, 4.0 * sa),
            (8.5 * ca, l_androg - 1.5, 8.5 * sa)
        ]
        obj_data += "usemtl Mat_Filamento" + NL
        seg_arm, v_offset = add_tube(arm_pts, 0.72, 0.48, 6, v_offset)
        obj_data += seg_arm

        tx, tz = -sa, ca
        ant_pts = [
            (8.5 * ca - (l_antera / 2.0) * tx, l_androg - 2.4, 8.5 * sa - (l_antera / 2.0) * tz),
            (8.5 * ca, l_androg - 2.0, 8.5 * sa),
            (8.5 * ca + (l_antera / 2.0) * tx, l_androg - 2.4, 8.5 * sa + (l_antera / 2.0) * tz)
        ]
        obj_data += "usemtl Mat_Antera" + NL
        seg_ant, v_offset = add_tube(ant_pts, 1.45, 1.45, 8, v_offset)
        obj_data += seg_ant

    obj_data += "usemtl Mat_Ovario" + NL
    ov_r = 3.2 if is_incarnata else 2.5
    ov_pts = [
        (0, l_androg, 0),
        (0, l_androg + ov_r * 0.5, 0),
        (0, l_androg + ov_r, 0),
        (0, l_androg + ov_r * 1.5, 0),
        (0, l_androg + ov_r * 1.8, 0)
    ]
    seg_ov, v_offset = add_tube(ov_pts, ov_r * 0.65, 0.4, 16, v_offset)
    obj_data += seg_ov

    l_estilo = float(gineceo.get('estilo_longitud_mm', 9.5))
    for i in range(3):
        a = i * (2.0 * math.pi / 3.0) + math.pi / 6.0
        ca, sa = math.cos(a), math.sin(a)
        st_pts = [
            (0, l_androg + ov_r * 1.7, 0),
            (l_estilo * 0.4 * ca, l_androg + ov_r * 1.9 + 2.0, l_estilo * 0.4 * sa),
            (l_estilo * 0.8 * ca, l_androg + ov_r * 1.9 + 0.5, l_estilo * 0.8 * sa),
            (l_estilo * 1.1 * ca, l_androg + ov_r * 1.9 - 2.5, l_estilo * 1.1 * sa)
        ]
        obj_data += "usemtl Mat_Estilo" + NL
        seg_st, v_offset = add_tube(st_pts, 0.75, 1.15, 8, v_offset)
        obj_data += seg_st

        stig_pts = [
            (l_estilo * 1.1 * ca - 1.4 * sa, l_androg + ov_r * 1.9 - 2.8, l_estilo * 1.1 * sa + 1.4 * ca),
            (l_estilo * 1.1 * ca + 1.4 * sa, l_androg + ov_r * 1.9 - 2.8, l_estilo * 1.1 * sa - 1.4 * ca)
        ]
        obj_data += "usemtl Mat_Ovario" + NL
        seg_sg, v_offset = add_tube(stig_pts, 1.8, 1.8, 10, v_offset)
        obj_data += seg_sg

    return obj_data

