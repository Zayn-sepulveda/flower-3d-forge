import yaml
import sys
import os
import math
import json

def load_config(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def build_vertex(x, y, z):
    return f"v {x:.4f} {y:.4f} {z:.4f}\n"

def build_face(v1, v2, v3):
    return f"f {v1} {v2} {v3}\n"

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16)/255.0 for i in (0, 2, 4))

def create_material_mtl(cfg, mtl_filepath):
    perianto = cfg['perianto']
    androceo = cfg['androceo']
    gineceo = cfg['gineceo']
   
    colors = {
        "Mat_Caliz": hex_to_rgb(perianto['caliz']['color_hex']),
        "Mat_CorolaGarganta": hex_to_rgb(perianto.get('corola', {}).get('color_garganta_hex', '#FFFFFF')),
        "Mat_CorolaLimbo": hex_to_rgb(perianto.get('corola', {}).get('color_limbo_hex', '#FFFFFF')),
        "Mat_Filamento": hex_to_rgb(androceo['color_filamento_hex']),
        "Mat_Antera": hex_to_rgb(androceo['color_antera_hex']),
        "Mat_Ovario": hex_to_rgb(gineceo['color_ovario_hex']),
        "Mat_Estilo": hex_to_rgb(gineceo['color_estilo_hex']),
        "Mat_Blanco": (0.98, 0.98, 1.0)
    }
    with open(mtl_filepath, 'w', encoding='utf-8') as f:
        f.write("# Materiales generados automaticamente\n")
        for mat_name, rgb in colors.items():
            f.write(f"\nnewmtl {mat_name}\n")
            f.write(f"Kd {rgb[0]:.4f} {rgb[1]:.4f} {rgb[2]:.4f}\n")
            f.write("Ka 0.2 0.2 0.2\nKs 0.15 0.15 0.15\nNs 12\n")
    return {k: '#' + ''.join(f'{int(c*255):02x}' for c in v) for k, v in colors.items()}

def add_tube(pts, r0, r1, sides, v_offset):
    out = ""
    n = len(pts)
    for i, (x, y, z) in enumerate(pts):
        t = i / max(1, n - 1)
        r = r0 * (1 - t) + r1 * t
        if i < n - 1:
            dx, dy, dz = pts[i+1][0] - x, pts[i+1][1] - y, pts[i+1][2] - z
        else:
            dx, dy, dz = x - pts[i-1][0], y - pts[i-1][1], z - pts[i-1][2]
        length = math.sqrt(dx*dx + dy*dy + dz*dz) or 1.0
        tx, ty, tz = dx/length, dy/length, dz/length
        if abs(ty) < 0.9:
            ux, uy, uz = 0, 1, 0
        else:
            ux, uy, uz = 1, 0, 0
        nx = ty*uz - tz*uy
        ny = tz*ux - tx*uz
        nz = tx*uy - ty*ux
        nl = math.sqrt(nx*nx + ny*ny + nz*nz) or 1.0
        nx, ny, nz = nx/nl, ny/nl, nz/nl
        bx = ty*nz - tz*ny
        by = tz*nx - tx*nz
        bz = tx*ny - ty*nx
        for s in range(sides):
            ang = 2 * math.pi * s / sides
            ca, sa = math.cos(ang), math.sin(ang)
            vx = x + r * (ca*nx + sa*bx)
            vy = y + r * (ca*ny + sa*by)
            vz = z + r * (ca*nz + sa*bz)
            out += build_vertex(vx, vy, vz)
    for i in range(n - 1):
        for s in range(sides):
            p1 = v_offset + i*sides + s
            p2 = v_offset + i*sides + (s + 1) % sides
            p3 = v_offset + (i + 1)*sides + s
            p4 = v_offset + (i + 1)*sides + (s + 1) % sides
            out += build_face(p1, p2, p3)
            out += build_face(p2, p4, p3)
    return out, v_offset + n * sides

def build_araceae_inflorescence(cfg):
    obj_data = ""
    v_offset = 1
    perianto = cfg['perianto']['corola']
    l_limbo = perianto['longitud_limbo_mm']
    w_petalo = perianto['ancho_petalo_mm']
    fd = perianto['diferenciacion_dorsoventral']['factor_tamano_dorsal']
    fv = perianto['diferenciacion_dorsoventral']['factor_tamano_ventral']
    disposicion = cfg['arquitectura_floral'].get('disposicion', 'erecta').lower()

    obj_data += "usemtl Mat_Caliz\n"
    ped_pts = [(0, -90 + i*9, -8 + math.sin(i*0.15)*3) for i in range(11)]
    seg_obj, v_offset = add_tube(ped_pts, 4.2, 3.8, 12, v_offset)
    obj_data += seg_obj

    obj_data += "usemtl Mat_CorolaLimbo\n"
    res_u, res_v = 24, 24
    for i in range(res_u + 1):
        u = i / res_u
        for j in range(res_v + 1):
            v = j / res_v
            theta = (v - 0.5) * math.pi * 1.5
            lobe_boost = 1.0 + 0.35 * math.sin(abs(theta)) * (1.0 - u) if disposicion == "erecta" else 1.0
            radius = (w_petalo / 2) * math.sin(math.pi * (u ** 0.75)) * (fd if theta > 0 else fv) * lobe_boost
            x = radius * math.cos(theta)
            y_base = l_limbo * (u - 0.12)
            depth = 0.18 if disposicion == "erecta" else 0.55
            z = radius * math.sin(theta) * depth - (u * u) * (18 if disposicion == "erecta" else 42)
            bullado = math.sin(u * math.pi * 10) * math.cos(v * math.pi * 10) * 1.4
            z += bullado
            tilt = -50 if disposicion == "erecta" else 25
            angle = math.radians(tilt)
            y_rot = y_base * math.cos(angle) - z * math.sin(angle)
            z_rot = y_base * math.sin(angle) + z * math.cos(angle)
            obj_data += build_vertex(x, y_rot, z_rot)

    for i in range(res_u):
        for j in range(res_v):
            p1 = v_offset + i * (res_v + 1) + j
            p2 = p1 + 1
            p3 = p1 + (res_v + 1)
            p4 = p3 + 1
            obj_data += build_face(p1, p2, p3)
            obj_data += build_face(p2, p4, p3)
    v_offset += (res_u + 1) * (res_v + 1)

    gineceo = cfg['gineceo']
    l_espadice = gineceo['estilo_longitud_mm']
    w_espadice = gineceo['estilo_grosor_mm'] / 2.0
    estipite_l = cfg['androceo']['filamento_longitud_mm']
    obj_data += "usemtl Mat_Estilo\n"
    sp_pts = []
    for i in range(25):
        h = i / 24.0
        y_val = estipite_l + l_espadice * h
        if disposicion == "pendula":
            y_val = -y_val
        z_val = (h * 18.0) if disposicion == "erecta" else (h * 5.0)
        sp_pts.append((0, y_val, z_val))
    seg_obj, v_offset = add_tube(sp_pts, w_espadice, w_espadice * 0.55, 16, v_offset)
    obj_data += seg_obj
    return obj_data

def build_passiflora_flower(cfg):
    obj_data = ""
    v_offset = 1
    is_incarnata = "incarnata" in cfg['colecta']['especie'].lower()
    l_petal = cfg['perianto']['corola']['longitud_limbo_mm']
    w_petal = cfg['perianto']['corola']['ancho_petalo_mm']
    l_sepal = l_petal * 1.02

    obj_data += "usemtl Mat_Caliz\n"
    ped_pts = [(0, -35 + i*5, 0) for i in range(8)]
    seg_obj, v_offset = add_tube(ped_pts, 2.2, 6.5, 12, v_offset)
    obj_data += seg_obj

    for whorl in ['sepal', 'petal']:
        length = l_sepal if whorl == 'sepal' else l_petal
        width = w_petal * (1.05 if whorl == 'sepal' else 0.95)
        offset_angle = 0.0 if whorl == 'sepal' else (math.pi / 5.0)
        y_layer = -1.2 if whorl == 'sepal' else 0.0
        obj_data += f"usemtl {'Mat_Caliz' if whorl == 'sepal' else 'Mat_CorolaLimbo'}\n"
        ru, rv = 12, 6
        for k in range(5):
            base_ang = k * (2 * math.pi / 5.0) + offset_angle
            ca, sa = math.cos(base_ang), math.sin(base_ang)
            for i in range(ru + 1):
                u = i / ru
                r = 5.0 + length * u
                w_local = (width / 2.0) * math.sin(math.pi * (u ** 0.7)) * (1.0 - 0.15 * u)
                arch_y = y_layer + 3.5 * math.sin(math.pi * u) - 6.0 * (u ** 1.6)
                for j in range(rv + 1):
                    v = (j / rv) - 0.5
                    lat = v * 2.0 * w_local
                    cup = -1.2 * (v * v)
                    px = r * ca - lat * sa
                    pz = r * sa + lat * ca
                    py = arch_y + cup
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

    l_filam = cfg['perianto']['corola']['longitud_tubo_mm']
    num_outer = 64 if is_incarnata else 48
    for i in range(num_outer):
        angle = i * (2 * math.pi / num_outer)
        pts_base, pts_tip = [], []
        steps = 16
        for j in range(steps):
            u = j / (steps - 1)
            d_theta, d_y = 0.0, 0.0
            if is_incarnata and u > 0.42:
                d_theta = 0.18 * ((u - 0.42) ** 1.3) * math.sin(6.5 * math.pi * u + (i % 5) * 0.7)
                d_y = 2.6 * ((u - 0.42) ** 1.4) * math.cos(5.5 * math.pi * u + (i % 3) * 0.9)
            ang = angle + d_theta
            r = 5.5 + l_filam * (1.35 if is_incarnata else 1.0) * u
            elev = (2.5 * math.sin(u * math.pi) + d_y) if is_incarnata else (8.0 * u - 2.0 * (u ** 2))
            pt = (r * math.cos(ang), 1.2 + elev, r * math.sin(ang))
            if u <= 0.42:
                pts_base.append(pt)
            if u >= 0.35:
                pts_tip.append(pt)
        obj_data += "usemtl Mat_Blanco\n" if is_incarnata else "usemtl Mat_CorolaGarganta\n"
        seg1, v_offset = add_tube(pts_base, 0.55, 0.42, 4, v_offset)
        obj_data += seg1
        obj_data += "usemtl Mat_CorolaLimbo\n" if is_incarnata else "usemtl Mat_CorolaGarganta\n"
        seg2, v_offset = add_tube(pts_tip, 0.42, 0.15, 4, v_offset)
        obj_data += seg2

    obj_data += "usemtl Mat_CorolaGarganta\n" if is_incarnata else "usemtl Mat_Blanco\n"
    for i in range(36):
        ang = i * (2 * math.pi / 36.0)
        pts_in = [
            (4.2 * math.cos(ang), 1.0, 4.2 * math.sin(ang)),
            (6.5 * math.cos(ang), 4.5, 6.5 * math.sin(ang)),
            (5.5 * math.cos(ang), 7.5, 5.5 * math.sin(ang))
        ]
        seg_in, v_offset = add_tube(pts_in, 0.45, 0.18, 4, v_offset)
        obj_data += seg_in

    l_androg = cfg['androceo']['filamento_longitud_mm']
    w_androg = cfg['androceo']['filamento_grosor_mm'] / 2.0
    obj_data += "usemtl Mat_Filamento\n"
    col_pts = [(0, i * (l_androg / 8.0), 0) for i in range(9)]
    seg_col, v_offset = add_tube(col_pts, w_androg * 1.15, w_androg * 0.9, 12, v_offset)
    obj_data += seg_col

    l_antera = cfg['androceo']['antera_longitud_mm']
    for i in range(5):
        a = i * (2 * math.pi / 5.0)
        ca, sa = math.cos(a), math.sin(a)
        arm_pts = [
            (0, l_androg, 0),
            (5.0 * ca, l_androg + 1.2, 5.0 * sa),
            (9.5 * ca, l_androg - 0.8, 9.5 * sa)
        ]
        obj_data += "usemtl Mat_Filamento\n"
        seg_arm, v_offset = add_tube(arm_pts, 0.85, 0.65, 6, v_offset)
        obj_data += seg_arm

        tx, tz = -sa, ca
        ant_pts = [
            (9.5 * ca - (l_antera / 2.0) * tx, l_androg - 1.3, 9.5 * sa - (l_antera / 2.0) * tz),
            (9.5 * ca, l_androg - 1.5, 9.5 * sa),
            (9.5 * ca + (l_antera / 2.0) * tx, l_androg - 1.3, 9.5 * sa + (l_antera / 2.0) * tz)
        ]
        obj_data += "usemtl Mat_Antera\n"
        seg_ant, v_offset = add_tube(ant_pts, 1.35, 1.35, 8, v_offset)
        obj_data += seg_ant

    obj_data += "usemtl Mat_Ovario\n"
    ov_pts = [
        (0, l_androg - 0.5, 0),
        (0, l_androg + 1.5, 0),
        (0, l_androg + 4.2, 0),
        (0, l_androg + 6.5, 0),
        (0, l_androg + 7.5, 0)
    ]
    seg_ov, v_offset = add_tube(ov_pts, 1.2, 0.8, 12, v_offset)
    obj_data += seg_ov

    l_estilo = cfg['gineceo']['estilo_longitud_mm']
    for i in range(3):
        a = i * (2 * math.pi / 3.0) + math.pi / 6.0
        ca, sa = math.cos(a), math.sin(a)
        st_pts = [
            (0, l_androg + 6.8, 0),
            (l_estilo * 0.45 * ca, l_androg + 9.5, l_estilo * 0.45 * sa),
            (l_estilo * 0.85 * ca, l_androg + 8.0, l_estilo * 0.85 * sa),
            (l_estilo * ca, l_androg + 6.5, l_estilo * sa)
        ]
        obj_data += "usemtl Mat_Estilo\n"
        seg_st, v_offset = add_tube(st_pts, 0.75, 1.25, 8, v_offset)
        obj_data += seg_st

        stig_pts = [
            (l_estilo * ca - 1.2 * sa, l_androg + 6.3, l_estilo * sa + 1.2 * ca),
            (l_estilo * ca + 1.2 * sa, l_androg + 6.3, l_estilo * sa - 1.2 * ca)
        ]
        obj_data += "usemtl Mat_Antera\n" if is_incarnata else "usemtl Mat_Ovario\n"
        seg_sg, v_offset = add_tube(stig_pts, 1.6, 1.6, 8, v_offset)
        obj_data += seg_sg

    return obj_data

def build_asteraceae_capitulum(cfg):
    """
    Capítulo de Helianthus annuus con morfometría orgánica natural:
    - Pedúnculo clavado acostillado (pubescencia/rugosidad) con curvatura gravitacional.
    - 3 series de filarias involucrales cóncavas y reflexas que envuelven el receptáculo.
    - Lígulas periféricas en 3 capas escalonadas, desalineadas, onduladas y con torsión individual.
    - Flósculos del disco según espiral filotáctica de Vogel sobre domo convexo.
    """
    obj_data = ""
    v_offset = 1

    caliz_cfg = cfg['perianto']['caliz']
    corola_cfg = cfg['perianto']['corola']

    scale = 0.62
    r_disco = 47.5 * scale
    n_filarias = int(caliz_cfg.get('sepalos_numero', 48))
    l_filaria = float(caliz_cfg.get('longitud_tubo_mm', 28.0)) * scale
    n_ligulas = int(corola_cfg.get('petalos_numero', 42))
    l_tubo_lig = float(corola_cfg.get('longitud_tubo_mm', 5.5)) * scale
    l_ligula = float(corola_cfg.get('longitud_limbo_mm', 72.0)) * scale
    w_ligula = float(corola_cfg.get('ancho_petalo_mm', 21.0)) * scale

    # Inclinación heliotrópica natural hacia el visor (34 grados)
    tilt_rad = math.radians(34.0)
    ct, st = math.cos(tilt_rad), math.sin(tilt_rad)

    def orient_pt(x, y, z):
        return (x, y * ct - z * st, y * st + z * ct)

    # 1. PEDÚNCULO CLAVADO (ENSANCHAMIENTO OBCÓNICO SUB-CAPÍTULO Y COSTILLAS HÍSPIDAS)
    obj_data += "usemtl Mat_Caliz\n"
    n_ped_rings, sides_ped = 16, 18
    # Perfil del pedúnculo: desde el tallo basal largo curvado hasta la copa ancha clavada
    for i in range(n_ped_rings):
        t = i / (n_ped_rings - 1)
        # Curvatura sigmoidea natural por peso del capítulo
        py = -85.0 * (1.0 - t) - 4.5 * t
        pz = -22.0 * ((1.0 - t) ** 1.8)
        # Ensanchamiento gradual clavado: de 4.8 mm a 22 mm en la inserción
        r_ring = 4.8 + 18.5 * (t ** 3.0)
        
        for s in range(sides_ped):
            ang = s * (2.0 * math.pi / sides_ped)
            # Modulación acanalada (costillas y asperezas del tallo híspido)
            rib_mod = 1.0 + 0.06 * math.cos(ang * 9.0) + 0.02 * math.sin(ang * 18.0)
            rx = r_ring * rib_mod * math.cos(ang)
            rz = r_ring * rib_mod * math.sin(ang)
            tx, ty, tz = orient_pt(rx, py, rz + pz)
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

    # 2. FILARIAS INVOLUCRALES EN 3 SERIES IMBRICADAS (CÓNCAVAS, FOLIÁCEAS Y ACUMINADAS)
    obj_data += "usemtl Mat_Caliz\n"
    ru_f, rv_f = 9, 5
    for k in range(n_filarias):
        whorl = k % 3  # 0: basal exterior reflexa, 1: media envolvente, 2: interior adpresa
        ang = k * (2.0 * math.pi / n_filarias) + (whorl * 0.18) + (math.sin(k * 2.1) * 0.04)
        ca, sa = math.cos(ang), math.sin(ang)
        
        # Parámetros diferenciados por verticilo
        if whorl == 0:
            r_ins = r_disco * 0.72
            y_ins = -6.0
            l_bract = l_filaria * 1.15
            w_bract = 5.2
            recurve = 9.0   # Puntas reflexas curvadas hacia abajo
        elif whorl == 1:
            r_ins = r_disco * 0.86
            y_ins = -3.8
            l_bract = l_filaria * 0.95
            w_bract = 4.8
            recurve = 3.2
        else:
            r_ins = r_disco * 0.98
            y_ins = -1.6
            l_bract = l_filaria * 0.78
            w_bract = 4.2
            recurve = -1.5  # Adpresas hacia arriba sujetando las lígulas

        for i in range(ru_f + 1):
            u = i / ru_f
            r_curr = r_ins + l_bract * u
            # Perfil ovado-acuminado con quilla dorsal y punta afilada
            w_loc = w_bract * math.sin(math.pi * (u ** 0.58)) * (1.0 - 0.75 * u)
            y_curr = y_ins + 2.5 * math.sin(u * math.pi * 0.6) - recurve * (u ** 2.2)
            
            for j in range(rv_f + 1):
                v = (j / rv_f) - 0.5
                lat = v * 2.0 * w_loc
                # Acabado cóncavo (en teja)
                cup = -1.1 * (v * v) * (1.0 - u * 0.5)
                px = r_curr * ca - lat * sa
                pz = r_curr * sa + lat * ca
                py = y_curr + cup
                tx, ty, tz = orient_pt(px, py, pz)
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

    # 3. DOMO DEL RECEPTÁCULO DISCOIDE PLANO-CONVEXO
    obj_data += "usemtl Mat_Ovario\n"
    ru_d, rv_d = 12, 32
    for i in range(ru_d + 1):
        u = i / ru_d
        r_curr = r_disco * u
        # Cúpula convexa suave que eleva el centro del disco
        y_curr = 4.8 * (1.0 - (u ** 2.2))
        for j in range(rv_d + 1):
            ang = j * (2.0 * math.pi / rv_d)
            px = r_curr * math.cos(ang)
            pz = r_curr * math.sin(ang)
            tx, ty, tz = orient_pt(px, y_curr, pz)
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

    # 4. LÍGULAS PERIFÉRICAS EN 3 CAPAS RADIALES ESCALONADAS Y ONDULADAS
    ru_l, rv_l = 14, 6
    for k in range(n_ligulas):
        # 3 Capas o verticilos concéntricos (capa 0: inferior, capa 1: media, capa 2: superior interna)
        layer = k % 3
        
        # Desfase angular orgánico (sin alineación rígida)
        jitter_ang = math.sin(k * 3.7) * 0.038 + math.cos(k * 1.9) * 0.02
        base_ang = k * (2.0 * math.pi / n_ligulas) + jitter_ang
        ca, sa = math.cos(base_ang), math.sin(base_ang)

        # Variación paramétrica por capa (alturas, radios basales y longitud)
        if layer == 0:  # Capa inferior: más larga, ligeramente caída
            y_base = -1.2 + math.sin(k * 1.3) * 0.4
            r_base = r_disco * 0.96
            l_len = l_ligula * 1.05
            w_local_scale = w_ligula * 0.98
            tilt_pitch = -0.16 + math.sin(k * 2.3) * 0.06
            curl_amp = -5.8
        elif layer == 1:  # Capa media: horizontal extendida
            y_base = 0.6 + math.cos(k * 2.1) * 0.4
            r_base = r_disco * 0.98
            l_len = l_ligula * 1.0
            w_local_scale = w_ligula * 1.04
            tilt_pitch = 0.02 + math.sin(k * 3.1) * 0.05
            curl_amp = -2.2
        else:  # Capa superior interna: más erguida hacia adelante y corta
            y_base = 2.4 + math.sin(k * 2.7) * 0.5
            r_base = r_disco * 0.92
            l_len = l_ligula * 0.88
            w_local_scale = w_ligula * 0.92
            tilt_pitch = 0.22 + math.cos(k * 1.7) * 0.08
            curl_amp = 3.6

        # 4a. Tubo basal estrecho (naranja cálido)
        obj_data += "usemtl Mat_CorolaGarganta\n"
        tub_pts = [
            orient_pt((r_base - 1.2) * ca, y_base, (r_base - 1.2) * sa),
            orient_pt((r_base + l_tubo_lig) * ca, y_base + 1.2, (r_base + l_tubo_lig) * sa)
        ]
        seg_t, v_offset = add_tube(tub_pts, 1.1, 1.45, 5, v_offset)
        obj_data += seg_t

        # 4b. Lámina radiante ondulada y torsionada (amarillo oro)
        obj_data += "usemtl Mat_CorolaLimbo\n"
        twist_k = math.sin(k * 2.7 + layer) * 0.18  # Torsión individual del limbo

        for i in range(ru_l + 1):
            u = i / ru_l
            r_curr = r_base + l_tubo_lig * 0.8 + l_len * u
            
            # Ancho con ápice trilobulado/acuminado característico
            w_curr = (w_local_scale / 2.0) * math.sin(math.pi * (u ** 0.62)) * (1.0 - 0.22 * (u ** 2.2))
            
            # Arqueamiento longitudinal orgánico (combinación de elevación, caída y dobleces)
            arch_long = (
                y_base + 1.2 
                + (tilt_pitch * l_len * u)
                + 3.8 * math.sin(math.pi * u) 
                + curl_amp * (u ** 2.4)
            )

            for j in range(rv_l + 1):
                v = (j / rv_l) - 0.5
                lat = v * 2.0 * w_curr
                
                # Nervaduras y pliegues longitudinales marcados
                vein_ruffle = (
                    0.55 * math.cos(v * math.pi * 3.0) * math.sin(math.pi * (u ** 0.7))
                    - 0.95 * (v * v)
                    + (v * twist_k * 4.2 * u)  # Torsión de bordes
                )
                
                px = r_curr * ca - lat * sa
                pz = r_curr * sa + lat * ca
                py = arch_long + vein_ruffle
                tx, ty, tz = orient_pt(px, py, pz)
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

    # 5. FLÓSCULOS DEL DISCO (FILOTAXIA DE VOGEL CON MADURACIÓN CENTRÍPETA)
    n_total_flosculos = 520
    golden_angle = math.radians(137.50776)
    c_vogel = (r_disco * 0.93) / math.sqrt(n_total_flosculos)

    flosculos_centro = []
    flosculos_periferia_tubo = []
    flosculos_periferia_antera = []
    flosculos_periferia_estilo = []

    for n in range(1, n_total_flosculos + 1):
        theta_n = n * golden_angle
        r_n = c_vogel * math.sqrt(n)
        frac = r_n / r_disco
        px = r_n * math.cos(theta_n)
        pz = r_n * math.sin(theta_n)
        py_base = 4.8 * (1.0 - (frac ** 2.2))

        if frac < 0.46:
            # Centro: botones tubulares cerrados parduzcos-verdosos
            pts_f = [
                orient_pt(px, py_base, pz),
                orient_pt(px, py_base + 3.2, pz)
            ]
            flosculos_centro.append(pts_f)
        else:
            # Periferia: flores hermafroditas abiertas con tubo, antera negra y estigma bífido amarillo
            pts_cor = [
                orient_pt(px, py_base, pz),
                orient_pt(px, py_base + 3.1, pz)
            ]
            pts_ant = [
                orient_pt(px, py_base + 3.0, pz),
                orient_pt(px, py_base + 5.3, pz)
            ]
            # Bifurcación recurvada del estigma
            twist_stg = 1.025 if (n % 2 == 0) else 0.975
            pts_est = [
                orient_pt(px, py_base + 5.0, pz),
                orient_pt(px * twist_stg, py_base + 6.6, pz * twist_stg)
            ]
            flosculos_periferia_tubo.append(pts_cor)
            flosculos_periferia_antera.append(pts_ant)
            flosculos_periferia_estilo.append(pts_est)

    obj_data += "usemtl Mat_Antera\n"
    for pts_f in flosculos_centro:
        seg_f, v_offset = add_tube(pts_f, 0.78, 0.42, 5, v_offset)
        obj_data += seg_f

    obj_data += "usemtl Mat_CorolaGarganta\n"
    for pts_cor in flosculos_periferia_tubo:
        seg_c, v_offset = add_tube(pts_cor, 0.72, 0.94, 5, v_offset)
        obj_data += seg_c

    obj_data += "usemtl Mat_Filamento\n"
    for pts_ant in flosculos_periferia_antera:
        seg_a, v_offset = add_tube(pts_ant, 0.52, 0.46, 5, v_offset)
        obj_data += seg_a

    obj_data += "usemtl Mat_Estilo\n"
    for pts_est in flosculos_periferia_estilo:
        seg_e, v_offset = add_tube(pts_est, 0.42, 0.78, 4, v_offset)
        obj_data += seg_e

    return obj_data

def export_interactive_viewer_html(cfg, obj_data, color_map, html_filepath):
    sp_name = cfg['colecta'].get('especie', 'Flor Desconocida')
    fam = cfg['colecta'].get('familia', 'Indeterminada')
    id_m = cfg['colecta'].get('id_muestra', 'COL-000')
    loc = cfg['colecta'].get('localidad', 'Colombia')
    fecha = cfg['colecta'].get('fecha', 'N/A')
    
    foto_campo = cfg['colecta'].get('foto_campo', '')
    if foto_campo and not foto_campo.startswith('../') and not foto_campo.startswith(('http://', 'https://')):
        foto_campo = '../' + foto_campo.lstrip('/')

    html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Visor 3D - {sp_name}</title>
    <style>
        body {{ margin: 0; overflow: hidden; background: radial-gradient(circle at center, #1e2430 0%, #0f1218 100%); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
        .hud-panel {{
            position: absolute; top: 18px; left: 18px;
            background: rgba(15, 20, 28, 0.88); color: #e2e8f0;
            padding: 16px 20px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.1);
            z-index: 10; font-size: 0.88rem; line-height: 1.6;
            backdrop-filter: blur(8px); max-width: 320px;
        }}
        .hud-panel h2 {{ margin: 0 0 8px 0; font-style: italic; color: #58a6ff; font-size: 1.35rem; }}
        .hud-hint {{ color: #58a6ff; font-size: 0.78rem; margin-top: 8px; }}
        .photo-panel {{
            position: absolute; bottom: 20px; right: 20px;
            width: 210px; background: rgba(15, 20, 28, 0.92);
            border: 2px solid #58a6ff; border-radius: 10px;
            overflow: hidden; z-index: 10; box-shadow: 0 8px 24px rgba(0,0,0,0.6);
        }}
        .photo-panel img {{ width: 100%; height: 165px; object-fit: cover; display: block; }}
        .photo-label {{
            background: #161b22; color: #cbd5e0; text-align: center;
            font-size: 0.72rem; font-weight: 700; letter-spacing: 1px; padding: 7px 0;
            text-transform: uppercase;
        }}
        .back-btn {{
            position: absolute; bottom: 20px; left: 20px;
            background: #238636; color: #ffffff; text-decoration: none;
            padding: 10px 18px; border-radius: 6px; font-size: 0.85rem; font-weight: 600;
            z-index: 10; display: inline-flex; align-items: center; gap: 6px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.4); transition: background 0.2s;
        }}
        .back-btn:hover {{ background: #2ea043; }}
    </style>
</head>
<body>
    <div class="hud-panel">
        <h2>{sp_name}</h2>
        <div><strong>Familia:</strong> {fam}</div>
        <div><strong>Muestra:</strong> {id_m}</div>
        <div><strong>Localidad:</strong> {loc}</div>
        <div><strong>Fecha:</strong> {fecha}</div>
        <div class="hud-hint">• Rotar: Clic izquierdo | Zoom: Rueda | Mover: Clic derecho</div>
    </div>

    <a href="../index.html" class="back-btn">⬅ Volver al catálogo</a>

    <div class="photo-panel">
        <img src="{foto_campo}" alt="{sp_name}" onerror="this.parentElement.style.display='none';">
        <div class="photo-label">REGISTRO DE CAMPO</div>
    </div>

    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
    <script>
        const objRaw = {json.dumps(obj_data)};
        const palette = {json.dumps(color_map)};

        const scene = new THREE.Scene();
        const camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 2000);
        camera.position.set(0, 65, 140);

        const renderer = new THREE.WebGLRenderer({{ antialias: true, alpha: true }});
        renderer.setSize(window.innerWidth, window.innerHeight);
        renderer.setPixelRatio(window.devicePixelRatio);
        document.body.appendChild(renderer.domElement);

        const controls = new THREE.OrbitControls(camera, renderer.domElement);
        controls.enableDamping = true;

        scene.add(new THREE.AmbientLight(0xffffff, 0.75));
        const dirLight1 = new THREE.DirectionalLight(0xffffff, 0.85);
        dirLight1.position.set(80, 140, 100);
        scene.add(dirLight1);
        const dirLight2 = new THREE.DirectionalLight(0x90cdf4, 0.4);
        dirLight2.position.set(-80, -60, -80);
        scene.add(dirLight2);

        const vertices = [];
        const groups = {{}};
        let currentMat = "Mat_CorolaLimbo";

        objRaw.split('\n').forEach(line => {{
            const parts = line.trim().split(/\s+/);
            if (parts[0] === 'v') {{
                vertices.push([parseFloat(parts[1]), parseFloat(parts[2]), parseFloat(parts[3])]);
            }} else if (parts[0] === 'usemtl') {{
                currentMat = parts[1];
                if (!groups[currentMat]) groups[currentMat] = [];
            }} else if (parts[0] === 'f') {{
                if (!groups[currentMat]) groups[currentMat] = [];
                const idx = parts.slice(1).map(p => parseInt(p.split('/')[0]) - 1);
                if (idx.length >= 3 && vertices[idx[0]] && vertices[idx[1]] && vertices[idx[2]]) {{
                    groups[currentMat].push(...vertices[idx[0]], ...vertices[idx[1]], ...vertices[idx[2]]);
                }}
            }}
        }});

        const flowerGroup = new THREE.Group();
        Object.keys(groups).forEach(matName => {{
            const pos = groups[matName];
            if (pos.length === 0) return;
            const geom = new THREE.BufferGeometry();
            geom.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
            geom.computeVertexNormals();
            const mat = new THREE.MeshStandardMaterial({{
                color: palette[matName] || '#ffffff',
                roughness: 0.44,
                metalness: 0.05,
                side: THREE.DoubleSide
            }});
            flowerGroup.add(new THREE.Mesh(geom, mat));
        }});
        scene.add(flowerGroup);

        window.addEventListener('resize', () => {{
            camera.aspect = window.innerWidth / window.innerHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(window.innerWidth, window.innerHeight);
        }});

        function animate() {{
            requestAnimationFrame(animate);
            controls.update();
            renderer.render(scene, camera);
        }}
        animate();
    </script>
</body>
</html>"""
    with open(html_filepath, 'w', encoding='utf-8') as f:
        f.write(html_content)


def generate_flower_3d(cfg):
    specie_filename = cfg['colecta']['especie'].lower().replace(" ", "_")
    os.makedirs('models', exist_ok=True)
    obj_filepath = os.path.join('models', f"{specie_filename}.obj")
    mtl_filepath = os.path.join('models', f"{specie_filename}.mtl")
    html_filepath = os.path.join('models', f"{specie_filename}.html")

    color_map = create_material_mtl(cfg, mtl_filepath)
    familia = cfg['colecta']['familia'].strip()

    if familia == "Araceae":
        obj_data = build_araceae_inflorescence(cfg)
    elif familia == "Asteraceae":
        obj_data = build_asteraceae_capitulum(cfg)
    else:
        obj_data = build_passiflora_flower(cfg)

    with open(obj_filepath, 'w', encoding='utf-8') as f:
        f.write(f"mtllib {specie_filename}.mtl\n" + obj_data)

    export_interactive_viewer_html(cfg, obj_data, color_map, html_filepath)
    print(f"✅ Modelo 3D orgánico generado en: {html_filepath}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(1)
    generate_flower_3d(load_config(sys.argv[1]))
