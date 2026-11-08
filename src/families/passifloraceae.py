import math
import numpy as np
from geometry import *

import math
from geometry import add_tube, build_vertex, build_face, NL

def build_passiflora_flower(cfg):
    """
    Modelo morfométrico de alta precisión para Passiflora vitifolia:
    - Perianto reflejo: 10 tépalos (5 sépalos + 5 pétalos) lanceolados con caída natural (~55°).
    - Corona (paracorola): empalizada densa de filamentos tricolores (carmesí basal -> blanco medio -> ápice violeta).
    - Androginóforo columnar axial continuo.
    - 5 estambres libres e independientes con filamentos descendentes y anteras versátiles colgantes.
    - Ovario globoso central superior y 3 estilos recurvados con estigmas capitados (globosos).
    """
    obj_data = ""
    v_offset = 1

    corola = cfg.get('perianto', {}).get('corola', {})
    androceo = cfg.get('androceo', {})
    gineceo = cfg.get('gineceo', {})

    l_petal = float(corola.get('longitud_limbo_mm', 65.0))
    w_petal = float(corola.get('ancho_petalo_mm', 16.0))
    l_sepal = l_petal * 1.06
    w_sepal = w_petal * 1.08

    # 1. Pedicelo e Hipanto basal
    obj_data += "usemtl Mat_Caliz" + NL
    ped_pts = [
        (0.0, -42.0, -6.0),
        (0.0, -32.0, -5.0),
        (0.0, -20.0, -3.0),
        (0.0, -10.0, -1.0),
        (0.0, -4.0, 0.0)
    ]
    seg_ped, v_offset = add_tube(ped_pts, 2.2, 3.0, 14, v_offset)
    obj_data += seg_ped

    # Copa del hipanto (receptáculo ensanchado)
    n_cup, s_cup = 6, 20
    for i in range(n_cup):
        t = i / (n_cup - 1)
        y_c = -4.0 + t * 4.0
        r_c = 3.0 + 5.5 * math.sin(t * math.pi * 0.5)
        for s in range(s_cup):
            ang = s * (2.0 * math.pi / s_cup)
            obj_data += build_vertex(r_c * math.cos(ang), y_c, r_c * math.sin(ang))

    for i in range(n_cup - 1):
        for s in range(s_cup):
            p1 = v_offset + i * s_cup + s
            p2 = v_offset + i * s_cup + (s + 1) % s_cup
            p3 = v_offset + (i + 1) * s_cup + s
            p4 = v_offset + (i + 1) * s_cup + (s + 1) % s_cup
            obj_data += build_face(p1, p2, p3)
            obj_data += build_face(p2, p4, p3)
    v_offset += n_cup * s_cup

    # 2. Perianto reflejo (5 sépalos + 5 pétalos fuertemente caídos hacia abajo)
    obj_data += "usemtl Mat_CorolaLimbo" + NL
    ru, rv = 20, 8

    for whorl in ['sepal', 'petal']:
        length = l_sepal if whorl == 'sepal' else l_petal
        width = w_sepal if whorl == 'sepal' else w_petal
        offset_ang = 0.0 if whorl == 'sepal' else (math.pi / 5.0)
        y_origin = -0.6 if whorl == 'sepal' else 0.4

        for k in range(5):
            base_ang = k * (2.0 * math.pi / 5.0) + offset_ang
            ca, sa = math.cos(base_ang), math.sin(base_ang)

            for i in range(ru + 1):
                u = i / ru
                # Curva paramétrica de caída (drooping): inicia horizontal y se arquea bruscamente hacia abajo
                r_proj = 8.5 + length * (u ** 0.88) * 0.72
                y_drop = y_origin + 2.5 * math.sin(math.pi * u * 0.4) - 38.0 * (u ** 1.6)

                # Perfil de lámina lanceolada-acuminada
                if u < 0.20:
                    w_profile = (u / 0.20) ** 0.65
                elif u < 0.70:
                    w_profile = 1.0 - 0.15 * ((u - 0.20) / 0.50)
                else:
                    t_tip = (u - 0.70) / 0.30
                    w_profile = (1.0 - t_tip) ** 1.2 * 0.85

                w_local = (width / 2.0) * w_profile

                for j in range(rv + 1):
                    v = (j / rv) - 0.5
                    lat = v * 2.0 * w_local
                    # Acanalamiento cóncavo longitudinal
                    gutter = -1.6 * (v * v) * (1.0 - u * 0.4)

                    px = r_proj * ca - lat * sa
                    pz = r_proj * sa + lat * ca
                    py = y_drop + gutter

                    # Apículo dorsal en los sépalos
                    if whorl == 'sepal' and 0.82 < u < 0.95 and abs(v) < 0.15:
                        py -= 1.8 * math.sin((u - 0.82) / 0.13 * math.pi)

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

    # 3. Corona de filamentos (Paracorola densa y tricolor)
    l_corona = float(corola.get('longitud_tubo_mm', 24.0))
    series_radii = [8.2, 7.3, 6.4]
    series_counts = [60, 52, 44]

    for s_idx, (r_start, num_fil) in enumerate(zip(series_radii, series_counts)):
        scale_len = 1.0 - (s_idx * 0.16)
        for i in range(num_fil):
            ang = i * (2.0 * math.pi / num_fil) + (s_idx * 0.06)
            ca_f, sa_f = math.cos(ang), math.sin(ang)

            # Filamento erecto-ascendente con divergencia distal suave
            pts_dark, pts_white, pts_tip = [], [], []
            steps = 14
            for j in range(steps):
                u = j / (steps - 1)
                r_curr = r_start + (l_corona * 0.52 * scale_len) * (u ** 1.2)
                y_curr = 0.5 + (l_corona * scale_len) * u + 0.8 * math.sin(u * math.pi)

                pt = (r_curr * ca_f, y_curr, r_curr * sa_f)
                if u <= 0.32:
                    pts_dark.append(pt)
                if 0.28 <= u <= 0.65:
                    pts_white.append(pt)
                if u >= 0.60:
                    pts_tip.append(pt)

            obj_data += "usemtl Mat_CorolaGarganta" + NL
            seg1, v_offset = add_tube(pts_dark, 0.40, 0.34, 4, v_offset)
            obj_data += seg1

            obj_data += "usemtl Mat_Blanco" + NL
            seg2, v_offset = add_tube(pts_white, 0.34, 0.26, 4, v_offset)
            obj_data += seg2

            obj_data += "usemtl Mat_CoronaVioleta" + NL
            seg3, v_offset = add_tube(pts_tip, 0.26, 0.12, 4, v_offset)
            obj_data += seg3

    # Opérculo interno erecto
    obj_data += "usemtl Mat_CorolaGarganta" + NL
    for i in range(36):
        ang = i * (2.0 * math.pi / 36.0)
        pts_op = [
            (5.2 * math.cos(ang), 0.4, 5.2 * math.sin(ang)),
            (5.8 * math.cos(ang), 2.8, 5.8 * math.sin(ang)),
            (5.0 * math.cos(ang), 5.0, 5.0 * math.sin(ang))
        ]
        seg_op, v_offset = add_tube(pts_op, 0.32, 0.12, 4, v_offset)
        obj_data += seg_op

    # 4. Columna axial central (Androginóforo)
    l_androg = float(androceo.get('filamento_longitud_mm', 26.0))
    w_androg = float(androceo.get('filamento_grosor_mm', 2.8)) / 2.0

    obj_data += "usemtl Mat_Filamento" + NL
    col_pts = [(0.0, i * (l_androg / 10.0), 0.0) for i in range(11)]
    seg_col, v_offset = add_tube(col_pts, w_androg * 1.15, w_androg * 0.95, 14, v_offset)
    obj_data += seg_col

    # 5. Androceo: 5 Estambres libres con anteras versátiles colgantes
    l_antera = float(androceo.get('antera_longitud_mm', 9.5))
    w_antera = 2.4

    for i in range(5):
        a = i * (2.0 * math.pi / 5.0)
        ca_st, sa_st = math.cos(a), math.sin(a)

        # Filamento aplanado arqueado hacia afuera y abajo
        fil_pts = [
            (0.0, l_androg * 0.96, 0.0),
            (3.8 * ca_st, l_androg + 1.2, 3.8 * sa_st),
            (7.5 * ca_st, l_androg - 0.8, 7.5 * sa_st),
            (9.2 * ca_st, l_androg - 4.5, 9.2 * sa_st)
        ]
        obj_data += "usemtl Mat_Filamento" + NL
        seg_fil, v_offset = add_tube(fil_pts, 0.75, 0.52, 6, v_offset)
        obj_data += seg_fil

        # Inserción versátil en "T": Antera oblonga transversal y péndula
        tip_fil = fil_pts[-1]
        tx, tz = -sa_st, ca_st  # Vector tangencial horizontal

        ant_pts = [
            (tip_fil[0] - (l_antera * 0.48) * tx, tip_fil[1] - 0.4, tip_fil[2] - (l_antera * 0.48) * tz),
            (tip_fil[0], tip_fil[1], tip_fil[2]),
            (tip_fil[0] + (l_antera * 0.48) * tx, tip_fil[1] - 0.4, tip_fil[2] + (l_antera * 0.48) * tz)
        ]
        obj_data += "usemtl Mat_Antera" + NL
        seg_ant, v_offset = add_tube(ant_pts, w_antera * 0.65, w_antera * 0.65, 8, v_offset)
        obj_data += seg_ant

    # 6. Gineceo: Ovario globoso + 3 estilos recurvados con estigmas capitados
    ov_r = 3.6
    ov_center_y = l_androg + ov_r * 0.75

    obj_data += "usemtl Mat_Ovario" + NL
    ov_pts = [
        (0.0, l_androg, 0.0),
        (0.0, ov_center_y - ov_r * 0.5, 0.0),
        (0.0, ov_center_y, 0.0),
        (0.0, ov_center_y + ov_r * 0.5, 0.0),
        (0.0, ov_center_y + ov_r * 0.85, 0.0)
    ]
    seg_ov, v_offset = add_tube(ov_pts, ov_r * 0.65, 0.6, 16, v_offset)
    obj_data += seg_ov

    l_estilo = float(gineceo.get('estilo_longitud_mm', 10.5))
    for i in range(3):
        a_sty = i * (2.0 * math.pi / 3.0) + math.pi / 6.0
        ca_sy, sa_sy = math.cos(a_sty), math.sin(a_sty)

        # Estilo carnoso arqueado divergente
        sty_pts = [
            (0.0, ov_center_y + ov_r * 0.80, 0.0),
            (l_estilo * 0.35 * ca_sy, ov_center_y + ov_r + 2.8, l_estilo * 0.35 * sa_sy),
            (l_estilo * 0.75 * ca_sy, ov_center_y + ov_r + 2.2, l_estilo * 0.75 * sa_sy),
            (l_estilo * 1.05 * ca_sy, ov_center_y + ov_r + 0.2, l_estilo * 1.05 * sa_sy)
        ]
        obj_data += "usemtl Mat_Estilo" + NL
        seg_sty, v_offset = add_tube(sty_pts, 0.85, 0.95, 8, v_offset)
        obj_data += seg_sty

        # Estigma capitado (cabezuela globosa apical)
        apex = sty_pts[-1]
        stig_pts = [
            (apex[0] - 0.4 * ca_sy, apex[1] - 0.4, apex[2] - 0.4 * sa_sy),
            (apex[0], apex[1], apex[2]),
            (apex[0] + 0.6 * ca_sy, apex[1] + 0.2, apex[2] + 0.6 * sa_sy)
        ]
        obj_data += "usemtl Mat_Ovario" + NL
        seg_stig, v_offset = add_tube(stig_pts, 1.85, 0.8, 12, v_offset)
        obj_data += seg_stig

    return obj_data

