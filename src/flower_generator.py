import yaml
import sys
import os
import math

def load_config(filepath):
    with open(filepath, 'r') as f:
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
    
    with open(mtl_filepath, 'w') as f:
        f.write("# Materiales generados automaticamente\n")
        colors = {
            "Mat_Caliz": hex_to_rgb(perianto['caliz']['color_hex']),
            "Mat_CorolaGarganta": hex_to_rgb(perianto.get('corola', {}).get('color_garganta_hex', '#FFFFFF')),
            "Mat_CorolaLimbo": hex_to_rgb(perianto.get('corola', {}).get('color_limbo_hex', '#FFFFFF')),
            "Mat_Filamento": hex_to_rgb(androceo['color_filamento_hex']),
            "Mat_Antera": hex_to_rgb(androceo['color_antera_hex']),
            "Mat_Ovario": hex_to_rgb(gineceo['color_ovario_hex']),
            "Mat_Estilo": hex_to_rgb(gineceo['color_estilo_hex'])
        }
        for mat_name, rgb in colors.items():
            f.write(f"\nnewmtl {mat_name}\n")
            f.write(f"Kd {rgb[0]:.4f} {rgb[1]:.4f} {rgb[2]:.4f}\n")
            f.write("Ka 0.2 0.2 0.2\nKs 0.1 0.1 0.1\nNs 10\n")

def build_araceae_inflorescence(cfg):
    obj_data = ""
    v_offset = 1
    
    # 1. Espata (Hoja modificada asimetrica)
    perianto = cfg['perianto']['corola']
    l_limbo = perianto['longitud_limbo_mm']
    w_petalo = perianto['ancho_petalo_mm']
    fd = perianto['diferenciacion_dorsoventral']['factor_tamano_dorsal']
    fv = perianto['diferenciacion_dorsoventral']['factor_tamano_ventral']
    
    obj_data += "usemtl Mat_CorolaLimbo\n"
    res_u = 20
    res_v = 20
    
    # Superficie de la espata cordada bullada
    for i in range(res_u + 1):
        u = i / res_u
        for j in range(res_v + 1):
            v = j / res_v
            
            theta = (v - 0.5) * math.pi * 1.5
            radius = (w_petalo / 2) * math.sin(math.pi * u) * (fd if theta > 0 else fv)
            
            x = radius * math.cos(theta)
            y_base = l_limbo * u
            
            z = radius * math.sin(theta) * 0.4
            z -= (u * u) * 40
            
            bullado = math.sin(u * math.pi * 12) * math.cos(v * math.pi * 12) * 1.5
            z += bullado
            
            # Reflexión hacia atrás (~55 grados)
            angle = math.radians(-55)
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

    # 2. Espádice
    gineceo = cfg['gineceo']
    l_espadice = gineceo['estilo_longitud_mm']
    w_espadice = gineceo['estilo_grosor_mm'] / 2.0
    
    # Estípite (pedúnculo basal del espádice)
    estipite_l = cfg['androceo']['filamento_longitud_mm']
    
    # Evaluar si la disposición es erecta o péndula
    disposicion = cfg['arquitectura_floral'].get('disposicion', 'erecta').lower()
    
    res_h = 30
    res_rad = 15
    obj_data += "usemtl Mat_Estilo\n"
    
    for i in range(res_h + 1):
        h_norm = i / res_h
        
        y_val = estipite_l + (l_espadice * h_norm)
        if disposicion == "pendula":
            y_val = -y_val
            
        z_offset = (h_norm * 15.0) if disposicion == "erecta" else 0
        
        r = w_espadice * (1.0 - 0.3 * (h_norm ** 2))
        
        for j in range(res_rad):
            theta = (j / res_rad) * 2 * math.pi
            x = r * math.cos(theta)
            z = r * math.sin(theta) + z_offset
            obj_data += build_vertex(x, y_val, z)

    for i in range(res_h):
        for j in range(res_rad):
            p1 = v_offset + i * res_rad + j
            p2 = v_offset + i * res_rad + (j + 1) % res_rad
            p3 = v_offset + (i + 1) * res_rad + j
            p4 = v_offset + (i + 1) * res_rad + (j + 1) % res_rad
            obj_data += build_face(p1, p2, p3)
            obj_data += build_face(p2, p4, p3)

    return obj_data

def build_passiflora_flower(cfg):
    obj_data = ""
    v_offset = 1
    
    # 1. Base / Receptaculo
    obj_data += "usemtl Mat_Caliz\n"
    r_base = 5.0
    for i in range(12):
        theta = (i/12) * 2 * math.pi
        obj_data += build_vertex(r_base * math.cos(theta), -2.0, r_base * math.sin(theta))
    obj_data += build_vertex(0, -5.0, 0)
    for i in range(12):
        p1 = v_offset + i
        p2 = v_offset + (i+1)%12
        p3 = v_offset + 12
        obj_data += build_face(p2, p1, p3)
    v_offset += 13

    # 2. Sépalos (Cáliz) y Pétalos (Corola) alternados
    l_sepal = cfg['perianto']['caliz'].get('longitud_tubo_mm', 35.0)
    l_petal = cfg['perianto']['corola']['longitud_limbo_mm']
    w_petal = cfg['perianto']['corola']['ancho_petalo_mm']
    
    for whorl in ['sepal', 'petal']:
        num_parts = 5
        length = l_sepal if whorl == 'sepal' else l_petal
        offset_angle = 0 if whorl == 'sepal' else (math.pi * 2 / 10) # Alternados 36 grados
        
        obj_data += f"usemtl {'Mat_Caliz' if whorl == 'sepal' else 'Mat_CorolaLimbo'}\n"
        for i in range(num_parts):
            angle = i * (2 * math.pi / num_parts) + offset_angle
            
            x_tip = length * math.cos(angle)
            z_tip = length * math.sin(angle)
            
            x_L = (w_petal/2) * math.cos(angle + math.pi/2) + (length*0.3) * math.cos(angle)
            z_L = (w_petal/2) * math.sin(angle + math.pi/2) + (length*0.3) * math.sin(angle)
            
            x_R = (w_petal/2) * math.cos(angle - math.pi/2) + (length*0.3) * math.cos(angle)
            z_R = (w_petal/2) * math.sin(angle - math.pi/2) + (length*0.3) * math.sin(angle)
            
            y_base = 0
            y_tip = -5.0 # Ligeramente reflexos
            
            obj_data += build_vertex(0, y_base, 0)
            obj_data += build_vertex(x_L, y_base+2, z_L)
            obj_data += build_vertex(x_R, y_base+2, z_R)
            obj_data += build_vertex(x_tip, y_tip, z_tip)
            
            obj_data += build_face(v_offset, v_offset+1, v_offset+2)
            obj_data += build_face(v_offset+1, v_offset+3, v_offset+2)
            
            v_offset += 4

    # 3. Corona de filamentos (Paracorola)
    obj_data += "usemtl Mat_CorolaGarganta\n"
    num_filaments = 60
    l_filam = cfg['perianto']['corola']['longitud_tubo_mm']
    is_incarnata = "incarnata" in cfg['colecta']['especie'].lower()
    
    for i in range(num_filaments):
        angle = i * (2 * math.pi / num_filaments)
        res_f = 10
        prev_idx = -1
        
        for j in range(res_f):
            u = j / (res_f - 1)
            
            # Filamentos rizados distales para P. incarnata, rectos para P. vitifolia
            delta_theta = 0
            delta_y = 0
            if is_incarnata and u > 0.45:
                delta_theta = 0.5 * ((u - 0.45)**2) * math.sin(5 * math.pi * u + i)
                delta_y = 4.0 * (u**3) * math.cos(4 * math.pi * u)
            
            final_angle = angle + delta_theta
            r = l_filam * u
            x = r * math.cos(final_angle)
            z = r * math.sin(final_angle)
            y = 1.0 + delta_y + (2.0 * math.sin(u * math.pi))
            
            obj_data += build_vertex(x, y, z)
            
            if prev_idx != -1:
                # Simular grosor de linea con triangulos degenerados 
                obj_data += build_face(prev_idx, prev_idx, v_offset)
                
            prev_idx = v_offset
            v_offset += 1

    # 4. Androginóforo y Estambres
    obj_data += "usemtl Mat_Filamento\n"
    l_androg = cfg['androceo']['filamento_longitud_mm']
    w_androg = cfg['androceo']['filamento_grosor_mm'] / 2.0
    
    # Tubo central
    for i in range(12):
        a = i * (2 * math.pi / 12)
        obj_data += build_vertex(w_androg * math.cos(a), 0, w_androg * math.sin(a))
        obj_data += build_vertex(w_androg * math.cos(a), l_androg, w_androg * math.sin(a))
        
        v_base = v_offset + (i*2)
        v_top = v_base + 1
        v_next_base = v_offset + (((i+1)%12)*2)
        v_next_top = v_next_base + 1
        
        obj_data += build_face(v_base, v_next_base, v_top)
        obj_data += build_face(v_next_base, v_next_top, v_top)
    v_offset += 24
    
    # 5 Brazos estaminales
    obj_data += "usemtl Mat_Antera\n"
    l_antera = cfg['androceo']['antera_longitud_mm']
    for i in range(5):
        a = i * (2 * math.pi / 5)
        x_arm = 8.0 * math.cos(a)
        z_arm = 8.0 * math.sin(a)
        
        # Brazo
        obj_data += build_vertex(0, l_androg, 0)
        obj_data += build_vertex(x_arm, l_androg, z_arm)
        obj_data += build_vertex(x_arm, l_androg-1, z_arm)
        obj_data += build_face(v_offset, v_offset+1, v_offset+2)
        
        # Antera versatil transversal
        ax_L = x_arm + (l_antera/2) * math.cos(a + math.pi/2)
        az_L = z_arm + (l_antera/2) * math.sin(a + math.pi/2)
        ax_R = x_arm + (l_antera/2) * math.cos(a - math.pi/2)
        az_R = z_arm + (l_antera/2) * math.sin(a - math.pi/2)
        
        obj_data += build_vertex(ax_L, l_androg-1, az_L)
        obj_data += build_vertex(ax_R, l_androg-1, az_R)
        obj_data += build_vertex(x_arm, l_androg-2, z_arm)
        obj_data += build_face(v_offset+3, v_offset+4, v_offset+5)
        
        v_offset += 6

    # 5. Ovario y Estilos (Gineceo)
    obj_data += "usemtl Mat_Ovario\n"
    r_ovario = 3.5
    for i in range(12):
        a = i * (2 * math.pi / 12)
        obj_data += build_vertex(r_ovario * math.cos(a), l_androg, r_ovario * math.sin(a))
    obj_data += build_vertex(0, l_androg + 5.0, 0)
    for i in range(12):
        obj_data += build_face(v_offset + i, v_offset + (i+1)%12, v_offset + 12)
    v_offset += 13
    
    obj_data += "usemtl Mat_Estilo\n"
    l_estilo = cfg['gineceo']['estilo_longitud_mm']
    for i in range(3): # 3 Estilos clavados
        a = i * (2 * math.pi / 3) + math.pi/3
        x_st = l_estilo * math.cos(a)
        z_st = l_estilo * math.sin(a)
        
        obj_data += build_vertex(0, l_androg + 5.0, 0)
        obj_data += build_vertex(x_st, l_androg + 6.0, z_st)
        obj_data += build_vertex(x_st, l_androg + 4.0, z_st) # Estigma abultado
        obj_data += build_face(v_offset, v_offset+1, v_offset+2)
        v_offset += 3

    return obj_data

def build_actinomorfa_basica(cfg):
    # Logica original simplificada (como Crotalaria)
    obj_data = ""
    # Aqui va el codigo de tu crotalaria que tenias antes
    return obj_data

def export_interactive_viewer_html(cfg, obj_filename, mtl_filename, html_filepath):
    sp_name = cfg['colecta']['especie']
    foto_campo = cfg['colecta'].get('foto_campo', '')
    if foto_campo and not foto_campo.startswith('../'):
        foto_campo = '../' + foto_campo
        
    html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Visor 3D - {sp_name}</title>
    <script type="module" src="https://ajax.googleapis.com/ajax/libs/model-viewer/3.1.1/model-viewer.min.js"></script>
    <style>
        body {{ margin: 0; padding: 0; background-color: #1a1a24; font-family: sans-serif; }}
        model-viewer {{ width: 100vw; height: 100vh; --poster-color: transparent; }}
        .hud-panel {{
            position: absolute; top: 20px; left: 20px;
            background: rgba(15, 15, 25, 0.85); color: #fff;
            padding: 15px; border-radius: 8px; border: 1px solid #333;
            pointer-events: none; z-index: 10; font-size: 0.9em;
        }}
        .hud-panel h2 {{ margin: 0 0 10px 0; font-style: italic; color: #7f9cf5; }}
        .photo-panel {{
            position: absolute; bottom: 20px; right: 20px;
            width: 150px; height: 150px;
            background: #000; border: 2px solid #555;
            border-radius: 8px; overflow: hidden; z-index: 10;
        }}
        .photo-panel img {{ width: 100%; height: 100%; object-fit: cover; }}
        .photo-label {{
            position: absolute; bottom: 0; width: 100%;
            background: rgba(0,0,0,0.7); color: white;
            text-align: center; font-size: 0.7em; padding: 4px 0;
        }}
    </style>
</head>
<body>
    <div class="hud-panel">
        <h2>{sp_name}</h2>
        <p><strong>Familia:</strong> {cfg['colecta']['familia']}</p>
        <p><strong>Muestra:</strong> {cfg['colecta']['id_muestra']}</p>
        <p><strong>Localidad:</strong> {cfg['colecta']['localidad']}</p>
    </div>
    
    <div class="photo-panel">
        <img src="{foto_campo}" alt="Registro de campo">
        <div class="photo-label">REGISTRO DE CAMPO</div>
    </div>

    <model-viewer 
        src="{obj_filename}" 
        camera-controls 
        auto-rotate
        shadow-intensity="1"
        exposure="1.2">
    </model-viewer>
</body>
</html>
"""
    with open(html_filepath, 'w', encoding='utf-8') as f:
        f.write(html_content)

def generate_flower_3d(cfg):
    specie_filename = cfg['colecta']['especie'].lower().replace(" ", "_")
    os.makedirs('models', exist_ok=True)
    
    obj_filepath = os.path.join('models', f"{specie_filename}.obj")
    mtl_filepath = os.path.join('models', f"{specie_filename}.mtl")
    html_filepath = os.path.join('models', f"{specie_filename}.html")
    
    create_material_mtl(cfg, mtl_filepath)
    
    with open(obj_filepath, 'w') as f:
        f.write(f"mtllib {specie_filename}.mtl\n")
        
        # Enrutador taxonómico
        if cfg['colecta']['familia'] == "Araceae":
            f.write(build_araceae_inflorescence(cfg))
        elif cfg['colecta']['familia'] == "Passifloraceae":
            f.write(build_passiflora_flower(cfg))
        else:
            f.write(build_actinomorfa_basica(cfg))
            
    export_interactive_viewer_html(cfg, f"{specie_filename}.obj", f"{specie_filename}.mtl", html_filepath)
    print(f"✅ Modelo 3D generado en: {html_filepath}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python src/flower_generator.py configs/archivo.yaml")
        sys.exit(1)
    
    cfg = load_config(sys.argv[1])
    generate_flower_3d(cfg)
