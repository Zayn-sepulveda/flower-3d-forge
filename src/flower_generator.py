import sys
import os
import yaml
import numpy as np


def hex_to_rgb(hex_str):
    hex_str = hex_str.lstrip('#')
    return np.array([int(hex_str[i:i+2], 16) / 255.0 for i in (0, 2, 4)])


def load_specimen_config(yaml_path):
    with open(yaml_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def add_tube_along_curve(curve_pts, radii, colors_ring, n_slices, vertices, colors, faces):
    n_rings = len(curve_pts)
    base_idx = len(vertices)
    theta_vals = np.linspace(0, 2 * np.pi, n_slices, endpoint=False)

    for i in range(n_rings):
        p = curve_pts[i]
        if i < n_rings - 1:
            tang = curve_pts[i + 1] - p
        else:
            tang = p - curve_pts[i - 1]
        norm_t = np.linalg.norm(tang)
        tang = tang / (norm_t if norm_t > 1e-6 else 1.0)

        ref = np.array([0.0, 0.0, 1.0]) if abs(tang[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
        n1 = np.cross(tang, ref)
        n1 /= np.linalg.norm(n1)
        n2 = np.cross(tang, n1)

        for j, th in enumerate(theta_vals):
            r = radii[i, j] if radii.ndim == 2 else radii[i]
            pt = p + r * (np.cos(th) * n1 + np.sin(th) * n2)
            vertices.append(pt.tolist())
            c = colors_ring[i, j] if colors_ring.ndim == 3 else colors_ring[i]
            colors.append(c.tolist())

    for i in range(n_rings - 1):
        for j in range(n_slices):
            j_next = (j + 1) % n_slices
            p1 = base_idx + i * n_slices + j + 1
            p2 = base_idx + i * n_slices + j_next + 1
            p3 = base_idx + (i + 1) * n_slices + j_next + 1
            p4 = base_idx + (i + 1) * n_slices + j + 1
            faces.append((p1, p2, p3))
            faces.append((p1, p3, p4))


def build_araceae_inflorescence(cfg):
    c_cfg = cfg['perianto']['corola']
    a_cfg = cfg.get('androceo', {})
    g_cfg = cfg.get('gineceo', {})

    spathe_len = float(c_cfg.get('longitud_limbo_mm', 65.0))
    acumen_len = float(c_cfg.get('longitud_tubo_mm', 15.0))
    total_spathe = spathe_len + acumen_len
    spathe_w = float(c_cfg.get('ancho_petalo_mm', 38.0)) * 0.55

    c_wine = hex_to_rgb(c_cfg.get('color_garganta_hex', '#8A1822'))
    c_dark_wine = c_wine * 0.65
    c_green = hex_to_rgb(c_cfg.get('color_limbo_hex', '#7A9F2E'))
    c_stipe = hex_to_rgb(a_cfg.get('color_filamento_hex', '#C85242'))
    c_spadix = hex_to_rgb(g_cfg.get('color_estilo_hex', '#B8D844'))
    c_spadix_tip = hex_to_rgb(g_cfg.get('color_apice_hex', '#D49442'))
    c_peduncle = hex_to_rgb(cfg['perianto']['caliz'].get('color_hex', '#8C7D38'))

    vertices, colors, faces = [], [], []

    # Leer disposición del archivo YAML desde el principio
    disposicion = cfg.get('arquitectura_floral', {}).get('disposicion', 'pendula').lower()

    # 1. ESPATA (Cordada plana para 'erecta' o Cuculada para 'pendula')
    n_v, n_u = 95, 55
    v_vals = np.linspace(0.0, 1.0, n_v)
    u_vals = np.linspace(-1.0, 1.0, n_u)
    body_frac = spathe_len / total_spathe
    base_idx = len(vertices)

    for v in v_vals:
        if v <= body_frac:
            tv = v / body_frac
            w_profile = np.sin(np.pi * (tv ** 0.68))
            depth_profile = np.sin(np.pi * (tv ** 0.8)) * (spathe_w * 0.72)
        else:
            ta = (v - body_frac) / (1.0 - body_frac)
            w_profile = (1.0 - ta) ** 2.2 * 0.18
            depth_profile = (1.0 - ta) * 2.5

        y_spine = v * total_spathe * 0.78
        
        # Aplanar la espata si es erecta (A. andraeanum)
        if disposicion == 'erecta':
            z_arch = np.sin(v * np.pi) * 3.0 - (v ** 2) * 4.0  # Mucho más plana
            depth_multiplier = 0.15  # Quita la forma de cuenco/capucha
            w_profile = w_profile * 1.3 # Ensancha la forma de corazón
        else:
            z_arch = np.sin(v * np.pi * 0.72) * 22.0 - (v ** 3) * 8.0 # Capucha original
            depth_multiplier = 1.0

        for u in u_vals:
            x = u * spathe_w * w_profile
            hood_curve = (1.0 - (u ** 2)) * depth_profile * depth_multiplier
            y = y_spine + (u ** 2) * 2.5
            z = z_arch - hood_curve

            # Moteado orgánico
            mottle = (
                0.09 * np.sin(38.0 * v + 17.0 * u) * np.cos(27.0 * v - 21.0 * u)
                + 0.05 * np.sin(75.0 * v + 43.0 * u)
            )
            trans_center = 0.44 + 0.08 * (1.0 - u ** 2)
            mix = np.clip((v - trans_center + mottle) / 0.16, 0.0, 1.0)

            base_col = (1.0 - min(v * 2.5, 1.0)) * c_dark_wine + min(v * 2.5, 1.0) * c_wine
            edge_green = np.clip((abs(u) - 0.78) / 0.22, 0.0, 1.0) * 0.55
            mix_final = np.clip(mix + edge_green, 0.0, 1.0)
            col = (1.0 - mix_final) * base_col + mix_final * c_green

            vertices.append([x, y, z])
            colors.append(col.tolist())

    for i in range(n_v - 1):
        for j in range(n_u - 1):
            p1 = base_idx + i * n_u + j + 1
            p2 = base_idx + i * n_u + (j + 1) + 1
            p3 = base_idx + (i + 1) * n_u + (j + 1) + 1
            p4 = base_idx + (i + 1) * n_u + j + 1
            faces.append((p1, p2, p3))
            faces.append((p1, p3, p4))

    # 2. ESTÍPITE ROJIZO ARQUEADO
    stipe_len = float(a_cfg.get('filamento_longitud_mm', 14.0))
    stipe_r = float(a_cfg.get('filamento_grosor_mm', 2.2))
    n_st = 20
    t_st = np.linspace(0, 1, n_st)
    
    if disposicion == 'erecta':
        # Para A. andraeanum el estípite sale hacia adelante y arriba
        stipe_pts = np.column_stack([
            np.zeros(n_st),
            3.0 + t_st * 4.0,
            -2.0 + t_st * 8.0 
        ])
    else:
        stipe_pts = np.column_stack([
            np.zeros(n_st),
            3.0 - t_st * 6.5,
            -2.0 + np.sin(t_st * np.pi * 0.5) * stipe_len
        ])
        
    stipe_radii = np.linspace(stipe_r * 1.1, stipe_r * 0.95, n_st)
    stipe_cols = np.tile(c_stipe, (n_st, 1))
    add_tube_along_curve(stipe_pts, stipe_radii, stipe_cols, 24, vertices, colors, faces)

    # 3. ESPÁDICE (DISPOSICIÓN ERECTA O PÉNDULA SEGÚN TAXÓN)
    spadix_len = float(g_cfg.get('estilo_longitud_mm', 70.0))
    spadix_r_base = float(g_cfg.get('estilo_grosor_mm', g_cfg.get('diametro_espadice_mm', 9.5))) / 2.0
    n_sp = 90
    n_sl = 44
    s_vals = np.linspace(0, 1, n_sp)
    start_sp = stipe_pts[-1]

    if disposicion == 'erecta':
        # ERECTO: Ángulo diagonal fuerte hacia afuera y arriba
        spadix_pts = np.column_stack([
            np.zeros(n_sp),
            start_sp[1] + s_vals * spadix_len * 0.7,
            start_sp[2] + s_vals * spadix_len * 0.7 + np.sin(s_vals * np.pi) * 1.5
        ])
    else:
        # PÉNDULO
        spadix_pts = np.column_stack([
            np.zeros(n_sp),
            start_sp[1] - s_vals * spadix_len,
            start_sp[2] + np.sin(s_vals * np.pi) * 2.2
        ])

    # 4. PEDÚNCULO (TALLO BASAL)
    n_ped = 30
    t_ped = np.linspace(0, 1, n_ped)
    ped_pts = np.column_stack([
        np.zeros(n_ped),
        3.0 - t_ped * 85.0,
        -2.0 - np.sin(t_ped * np.pi * 0.5) * 14.0
    ])
    ped_radii = np.linspace(2.6, 3.1, n_ped)
    ped_cols = np.tile(c_peduncle, (n_ped, 1))
    add_tube_along_curve(ped_pts, ped_radii, ped_cols, 20, vertices, colors, faces)

    return vertices, colors, faces


def build_standard_flower(cfg, n_rings=70, n_slices=120):
    arch = cfg.get('arquitectura_floral', {})
    simetria = arch.get('simetria', 'actinomorfa').lower()
    c_cfg = cfg['perianto']['corola']
    n_petals = max(int(c_cfg['petalos_numero']), 1)
    tube_len = float(c_cfg['longitud_tubo_mm'])
    limb_len = float(c_cfg['longitud_limbo_mm'])
    total_len = tube_len + limb_len
    r_base = 3.0
    r_throat = max(r_base, float(c_cfg.get('ancho_petalo_mm', 10.0)) * 0.4)

    is_zygo = (simetria == 'zigomorfa')
    zygo_cfg = c_cfg.get('diferenciacion_dorsoventral', {})
    f_dorsal = float(zygo_cfg.get('factor_tamano_dorsal', 1.5)) if is_zygo else 1.0
    f_ventral = float(zygo_cfg.get('factor_tamano_ventral', 0.8)) if is_zygo else 1.0

    c_base = hex_to_rgb(c_cfg['color_garganta_hex'])
    c_limbo = hex_to_rgb(c_cfg['color_limbo_hex'])

    z_vals = np.linspace(0, total_len, n_rings)
    theta_vals = np.linspace(0, 2 * np.pi, n_slices, endpoint=False)
    vertices, colors, faces = [], [], []

    for z in z_vals:
        if z <= tube_len and tube_len > 0:
            t = z / tube_len
            r_mean = r_base + (r_throat - r_base) * (t ** 1.2)
            amp = 0.05 * (t ** 2) * r_mean
            c_curr = c_base
        else:
            t = (z - tube_len) / max(limb_len, 1e-5)
            r_flare = r_throat + t * (float(c_cfg['ancho_petalo_mm']) * n_petals / (2 * np.pi))
            amp = t * float(c_cfg['ancho_petalo_mm']) * 0.6
            r_mean = r_flare
            c_curr = (1.0 - t) * c_base + t * c_limbo

        for th in theta_vals:
            mod = 1.0 + (np.cos(th) * (f_dorsal - 1.0) if np.cos(th) > 0 else np.cos(th) * (1.0 - f_ventral)) if is_zygo else 1.0
            r = (r_mean + amp * np.cos(n_petals * th)) * max(mod, 0.2)
            vertices.append([r * np.sin(th), z, r * np.cos(th)])
            colors.append(c_curr.tolist())

    for i in range(n_rings - 1):
        for j in range(n_slices):
            j_next = (j + 1) % n_slices
            p1 = i * n_slices + j + 1
            p2 = i * n_slices + j_next + 1
            p3 = (i + 1) * n_slices + j_next + 1
            p4 = (i + 1) * n_slices + j + 1
            faces.append((p1, p2, p3))
            faces.append((p1, p3, p4))

    return vertices, colors, faces


def export_obj(vertices, colors, faces, output_path):
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("# Digital Herbarium 3D - Morphometric Floral Model\n")
        for v, c in zip(vertices, colors):
            f.write(f"v {v[0]:.4f} {v[1]:.4f} {v[2]:.4f} {c[0]:.4f} {c[1]:.4f} {c[2]:.4f}\n")
        for face in faces:
            f.write(f"f {face[0]} {face[1]} {face[2]}\n")


def export_interactive_viewer_html(cfg, obj_filename, html_path):
    sp = cfg['colecta'].get('especie', 'Flor Desconocida')
    fam = cfg['colecta'].get('familia', 'Indeterminada')
    loc = cfg['colecta'].get('localidad', 'Colombia')
    fecha = cfg['colecta'].get('fecha', 'N/A')
    id_m = cfg['colecta'].get('id_muestra', 'COL-000')
    img_path = cfg['colecta'].get('foto_campo', '')
    if img_path and not img_path.startswith(('http://', 'https://')):
        img_path = "../" + img_path.lstrip('/')

    html_code = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Herbario 3D - {sp}</title>
    <style>
        body {{ margin: 0; overflow: hidden; background: radial-gradient(circle at center, #1b2028 0%, #0d1014 100%); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
        #canvas-container {{ width: 100vw; height: 100vh; }}
        .info-card {{
            position: absolute; top: 20px; left: 20px;
            background: rgba(22, 27, 34, 0.88); backdrop-filter: blur(8px);
            color: #f0f6fc; padding: 16px 20px; border-radius: 10px;
            border: 1px solid rgba(255, 255, 255, 0.12); max-width: 330px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.5); pointer-events: none;
        }}
        .info-card h2 {{ margin: 0 0 6px 0; font-size: 1.25rem; font-style: italic; color: #58a6ff; }}
        .info-card p {{ margin: 4px 0; font-size: 0.85rem; color: #8b949e; }}
        .info-card strong {{ color: #c9d1d9; }}
        .specimen-photo-box {{
            position: absolute; bottom: 24px; right: 24px; width: 230px;
            background: rgba(22, 27, 34, 0.92); border: 2px solid #58a6ff;
            border-radius: 12px; overflow: hidden;
            box-shadow: 0 10px 30px rgba(0,0,0,0.7);
            transition: transform 0.3s ease, width 0.3s ease; z-index: 10;
        }}
        .specimen-photo-box:hover {{ width: 340px; transform: scale(1.02); }}
        .specimen-photo-box img {{ width: 100%; height: auto; display: block; object-fit: cover; max-height: 280px; }}
        .photo-placeholder {{ padding: 24px 14px; text-align: center; font-size: 0.8rem; color: #8b949e; }}
        .upload-btn {{
            margin-top: 10px; display: inline-block; padding: 6px 12px;
            background: #238636; color: #fff; border-radius: 6px;
            font-size: 0.75rem; cursor: pointer; font-weight: 600;
        }}
        .photo-label {{
            padding: 8px 12px; font-size: 0.75rem; font-weight: 600;
            text-align: center; color: #f0f6fc; background: #161b22;
            letter-spacing: 0.5px; text-transform: uppercase;
        }}
    </style>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/OBJLoader.js"></script>
</head>
<body>
    <div class="info-card">
        <h2>{sp}</h2>
        <p><strong>Familia:</strong> {fam}</p>
        <p><strong>Muestra:</strong> {id_m}</p>
        <p><strong>Localidad:</strong> {loc}</p>
        <p><strong>Fecha:</strong> {fecha}</p>
        <p style="margin-top: 10px; font-size: 0.75rem; color: #58a6ff;">● Rotar: Clic izquierdo | Zoom: Rueda | Mover: Clic derecho</p>
    </div>

    <div class="specimen-photo-box" id="photo-box">
        <img id="field-img" src="{img_path}" alt="Espécimen real"
             onerror="this.style.display='none'; document.getElementById('fallback-box').style.display='block';" />
        <div id="fallback-box" class="photo-placeholder" style="display:none;">
            📷 Guarda tu foto en <b>{img_path.replace('../', '')}</b><br>o cárgala aquí directamente:<br>
            <label class="upload-btn">Elegir foto real<input type="file" accept="image/*" style="display:none" onchange="loadLocalPhoto(event)"></label>
        </div>
        <div class="photo-label">Registro de Campo</div>
    </div>

    <div id="canvas-container"></div>

    <script>
        function loadLocalPhoto(event) {{
            const file = event.target.files[0];
            if (file) {{
                const img = document.getElementById('field-img');
                img.src = URL.createObjectURL(file);
                img.style.display = 'block';
                document.getElementById('fallback-box').style.display = 'none';
            }}
        }}

        const scene = new THREE.Scene();
        const camera = new THREE.PerspectiveCamera(42, window.innerWidth / window.innerHeight, 0.1, 2000);
        const renderer = new THREE.WebGLRenderer({{ antialias: true, alpha: true }});
        renderer.setSize(window.innerWidth, window.innerHeight);
        renderer.setPixelRatio(window.devicePixelRatio);
        document.getElementById('canvas-container').appendChild(renderer.domElement);

        const controls = new THREE.OrbitControls(camera, renderer.domElement);
        controls.enableDamping = true;
        controls.dampingFactor = 0.06;

        scene.add(new THREE.AmbientLight(0xffffff, 0.75));
        const dirLight1 = new THREE.DirectionalLight(0xfff8e7, 0.75);
        dirLight1.position.set(60, 80, 90);
        scene.add(dirLight1);

        const dirLight2 = new THREE.DirectionalLight(0x88bbff, 0.35);
        dirLight2.position.set(-60, -40, -60);
        scene.add(dirLight2);

        const loader = new THREE.OBJLoader();
        loader.load('{obj_filename}?t=' + new Date().getTime(), function (object) {{
            object.traverse(function (child) {{
                if (child.isMesh) {{
                    child.geometry.computeVertexNormals();
                    child.material = new THREE.MeshStandardMaterial({{
                        vertexColors: true,
                        roughness: 0.42,
                        metalness: 0.05,
                        side: THREE.DoubleSide
                    }});
                }}
            }});
            const box = new THREE.Box3().setFromObject(object);
            const center = box.getCenter(new THREE.Vector3());
            const size = box.getSize(new THREE.Vector3());
            object.position.sub(center);
            scene.add(object);

            const maxDim = Math.max(size.x, size.y, size.z);
            camera.position.set(maxDim * 0.85, maxDim * 0.25, maxDim * 1.15);
            controls.target.set(0, 0, 0);
            controls.update();
        }});

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
</html>
"""
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_code)


def main():
    config_path = sys.argv[1] if len(sys.argv) > 1 else "configs/plantilla_base.yaml"
    if not os.path.exists(config_path):
        print(f"[ERROR] No se encontro archivo de configuracion: {config_path}")
        sys.exit(1)

    cfg = load_specimen_config(config_path)
    sp_name = cfg['colecta']['especie'].replace(' ', '_').lower().replace('.', '')
    os.makedirs("models", exist_ok=True)
    out_obj = os.path.join("models", f"{sp_name}.obj")
    out_html = os.path.join("models", f"{sp_name}.html")

    tipo_inf = cfg.get('arquitectura_floral', {}).get('tipo_inflorescencia', '').lower()
    if tipo_inf == 'espadice':
        verts, cols, faces = build_araceae_inflorescence(cfg)
    else:
        verts, cols, faces = build_standard_flower(cfg)

    export_obj(verts, cols, faces, out_obj)
    export_interactive_viewer_html(cfg, f"{sp_name}.obj", out_html)

    print(f"[OK] Modelo 3D exportado: {out_obj}")
    print(f"[OK] Visor interactivo generado: {out_html}")
    print(f"     Taxon: {cfg['colecta']['especie']} | Vertices: {len(verts)} | Caras: {len(faces)}")


if __name__ == "__main__":
    main()