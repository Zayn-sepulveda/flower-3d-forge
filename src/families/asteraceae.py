import math
import numpy as np
from geometry import *

def build_asteraceae_capitulum(cfg):
    obj_data = ""
    v_offset = 1
    caliz_cfg = cfg.get('perianto', {}).get('caliz') or {}
    corola_cfg = cfg.get('perianto', {}).get('corola') or {}
    scale = 0.62
    r_disco = 47.5 * scale
    n_filarias = int(caliz_cfg.get('sepalos_numero', 48))
    l_filaria = float(caliz_cfg.get('longitud_tubo_mm', 28.0)) * scale
    n_ligulas = int(corola_cfg.get('petalos_numero', 42))
    l_tubo_lig = float(corola_cfg.get('longitud_tubo_mm', 5.5)) * scale
    l_ligula = float(corola_cfg.get('longitud_limbo_mm', 72.0)) * scale
    w_ligula = float(corola_cfg.get('ancho_petalo_mm', 21.0)) * scale

    tilt_rad = math.radians(34.0)
    ct, st = math.cos(tilt_rad), math.sin(tilt_rad)
    def orient_pt(x, y, z):
        return (x, y * ct - z * st, y * st + z * ct)

    obj_data += "usemtl Mat_Caliz" + NL
    n_ped_rings, sides_ped = 16, 18
    for i in range(n_ped_rings):
        t = i / (n_ped_rings - 1)
        py = -85.0 * (1.0 - t) - 4.5 * t
        pz = -22.0 * ((1.0 - t) ** 1.8)
        r_ring = 4.8 + 18.5 * (t ** 3.0)
        for s in range(sides_ped):
            ang = s * (2.0 * math.pi / sides_ped)
            rib_mod = 1.0 + 0.06 * math.cos(ang * 9.0) + 0.02 * math.sin(ang * 18.0)
            tx, ty, tz = orient_pt(r_ring * rib_mod * math.cos(ang), py, r_ring * rib_mod * math.sin(ang) + pz)
            obj_data += build_vertex(tx, ty, tz)
    for i in range(n_ped_rings - 1):
        for s in range(sides_ped):
            p1 = v_offset + i * sides_ped + s
            p2 = v_offset + i * sides_ped + (s + 1) % sides_ped
            p3 = v_offset + (i + 1) * sides_ped + s
            p4 = v_offset + (i + 1) * sides_ped + (s + 1) % sides_ped
            obj_data += build_face(p1, p2, p3)
            obj_data += build_face(p2, p4, p3)
    v_offset += n_ped_rings * sides_ped

    ru_f, rv_f = 9, 5
    for k in range(n_filarias):
        whorl = k % 3
        ang = k * (2.0 * math.pi / n_filarias) + (whorl * 0.18) + (math.sin(k * 2.1) * 0.04)
        ca, sa = math.cos(ang), math.sin(ang)
        if whorl == 0:
            r_ins, y_ins, l_bract, w_bract, recurve = r_disco * 0.72, -6.0, l_filaria * 1.15, 5.2, 9.0
        elif whorl == 1:
            r_ins, y_ins, l_bract, w_bract, recurve = r_disco * 0.86, -3.8, l_filaria * 0.95, 4.8, 3.2
        else:
            r_ins, y_ins, l_bract, w_bract, recurve = r_disco * 0.98, -1.6, l_filaria * 0.78, 4.2, -1.5
        for i in range(ru_f + 1):
            u = i / ru_f
            r_curr = r_ins + l_bract * u
            w_loc = w_bract * math.sin(math.pi * (u ** 0.58)) * (1.0 - 0.75 * u)
            y_curr = y_ins + 2.5 * math.sin(u * math.pi * 0.6) - recurve * (u ** 2.2)
            for j in range(rv_f + 1):
                v = (j / rv_f) - 0.5
                lat = v * 2.0 * w_loc
                cup = -1.1 * (v * v) * (1.0 - u * 0.5)
                tx, ty, tz = orient_pt(r_curr * ca - lat * sa, y_curr + cup, r_curr * sa + lat * ca)
                obj_data += build_vertex(tx, ty, tz)
        for i in range(ru_f):
            for j in range(rv_f):
                p1 = v_offset + i * (rv_f + 1) + j
                p2 = p1 + 1
                p3 = p1 + (rv_f + 1)
                p4 = p3 + 1
                obj_data += build_face(p1, p2, p3)
                obj_data += build_face(p2, p4, p3)
        v_offset += (ru_f + 1) * (rv_f + 1)

    obj_data += "usemtl Mat_Ovario" + NL
    ru_d, rv_d = 12, 32
    for i in range(ru_d + 1):
        u = i / ru_d
        r_curr = r_disco * u
        y_curr = 4.8 * (1.0 - (u ** 2.2))
        for j in range(rv_d + 1):
            ang = j * (2.0 * math.pi / rv_d)
            tx, ty, tz = orient_pt(r_curr * math.cos(ang), y_curr, r_curr * math.sin(ang))
            obj_data += build_vertex(tx, ty, tz)
    for i in range(ru_d):
        for j in range(rv_d):
            p1 = v_offset + i * (rv_d + 1) + j
            p2 = p1 + 1
            p3 = p1 + (rv_d + 1)
            p4 = p3 + 1
            obj_data += build_face(p1, p2, p3)
            obj_data += build_face(p2, p4, p3)
    v_offset += (ru_d + 1) * (rv_d + 1)

    ru_l, rv_l = 14, 6
    for k in range(n_ligulas):
        layer = k % 3
        base_ang = k * (2.0 * math.pi / n_ligulas) + math.sin(k * 3.7) * 0.038 + math.cos(k * 1.9) * 0.02
        ca, sa = math.cos(base_ang), math.sin(base_ang)
        if layer == 0:
            y_base, r_base, l_len, w_local_scale, tilt_pitch, curl_amp = -1.2 + math.sin(k * 1.3) * 0.4, r_disco * 0.96, l_ligula * 1.05, w_ligula * 0.98, -0.16 + math.sin(k * 2.3) * 0.06, -5.8
        elif layer == 1:
            y_base, r_base, l_len, w_local_scale, tilt_pitch, curl_amp = 0.6 + math.cos(k * 2.1) * 0.4, r_disco * 0.98, l_ligula * 1.0, w_ligula * 1.04, 0.02 + math.sin(k * 3.1) * 0.05, -2.2
        else:
            y_base, r_base, l_len, w_local_scale, tilt_pitch, curl_amp = 2.4 + math.sin(k * 2.7) * 0.5, r_disco * 0.92, l_ligula * 0.88, w_ligula * 0.92, 0.22 + math.cos(k * 1.7) * 0.08, 3.6

        obj_data += "usemtl Mat_CorolaGarganta" + NL
        tub_pts = [orient_pt((r_base - 1.2) * ca, y_base, (r_base - 1.2) * sa), orient_pt((r_base + l_tubo_lig) * ca, y_base + 1.2, (r_base + l_tubo_lig) * sa)]
        seg_t, v_offset = add_tube(tub_pts, 1.1, 1.45, 5, v_offset)
        obj_data += seg_t

        obj_data += "usemtl Mat_CorolaLimbo" + NL
        twist_k = math.sin(k * 2.7 + layer) * 0.18
        for i in range(ru_l + 1):
            u = i / ru_l
            r_curr = r_base + l_tubo_lig * 0.8 + l_len * u
            w_curr = (w_local_scale / 2.0) * math.sin(math.pi * (u ** 0.62)) * (1.0 - 0.22 * (u ** 2.2))
            arch_long = y_base + 1.2 + (tilt_pitch * l_len * u) + 3.8 * math.sin(math.pi * u) + curl_amp * (u ** 2.4)
            for j in range(rv_l + 1):
                v = (j / rv_l) - 0.5
                lat = v * 2.0 * w_curr
                vein_ruffle = 0.55 * math.cos(v * math.pi * 3.0) * math.sin(math.pi * (u ** 0.7)) - 0.95 * (v * v) + (v * twist_k * 4.2 * u)
                tx, ty, tz = orient_pt(r_curr * ca - lat * sa, arch_long + vein_ruffle, r_curr * sa + lat * ca)
                obj_data += build_vertex(tx, ty, tz)
        for i in range(ru_l):
            for j in range(rv_l):
                p1 = v_offset + i * (rv_l + 1) + j
                p2 = p1 + 1
                p3 = p1 + (rv_l + 1)
                p4 = p3 + 1
                obj_data += build_face(p1, p2, p3)
                obj_data += build_face(p2, p4, p3)
        v_offset += (ru_l + 1) * (rv_l + 1)

    n_total_flosculos = 520
    golden_angle = math.radians(137.50776)
    c_vogel = (r_disco * 0.93) / math.sqrt(n_total_flosculos)
    flosculos_centro, flosculos_periferia_tubo, flosculos_periferia_antera, flosculos_periferia_estilo = [], [], [], []

    for n in range(1, n_total_flosculos + 1):
        theta_n = n * golden_angle
        r_n = c_vogel * math.sqrt(n)
        frac = r_n / r_disco
        px, pz = r_n * math.cos(theta_n), r_n * math.sin(theta_n)
        py_base = 4.8 * (1.0 - (frac ** 2.2))
        if frac < 0.46:
            flosculos_centro.append([orient_pt(px, py_base, pz), orient_pt(px, py_base + 3.2, pz)])
        else:
            twist_stg = 1.025 if (n % 2 == 0) else 0.975
            flosculos_periferia_tubo.append([orient_pt(px, py_base, pz), orient_pt(px, py_base + 3.1, pz)])
            flosculos_periferia_antera.append([orient_pt(px, py_base + 3.0, pz), orient_pt(px, py_base + 5.3, pz)])
            flosculos_periferia_estilo.append([orient_pt(px, py_base + 5.0, pz), orient_pt(px * twist_stg, py_base + 6.6, pz * twist_stg)])

    obj_data += "usemtl Mat_Antera" + NL
    for pts_f in flosculos_centro:
        seg_f, v_offset = add_tube(pts_f, 0.78, 0.42, 5, v_offset)
        obj_data += seg_f
    obj_data += "usemtl Mat_CorolaGarganta" + NL
    for pts_cor in flosculos_periferia_tubo:
        seg_c, v_offset = add_tube(pts_cor, 0.72, 0.94, 5, v_offset)
        obj_data += seg_c
    obj_data += "usemtl Mat_Filamento" + NL
    for pts_ant in flosculos_periferia_antera:
        seg_a, v_offset = add_tube(pts_ant, 0.52, 0.46, 5, v_offset)
        obj_data += seg_a
    obj_data += "usemtl Mat_Estilo" + NL
    for pts_est in flosculos_periferia_estilo:
        seg_e, v_offset = add_tube(pts_est, 0.42, 0.78, 4, v_offset)
        obj_data += seg_e
    return obj_data

