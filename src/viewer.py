import json

NL = chr(10)

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
        html, body {{ width: 100vw; height: 100vh; margin: 0; padding: 0; overflow: hidden; background-color: #0f1218; background-image: radial-gradient(circle at center, #1e2430 0%, #0f1218 100%); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
        .hud-panel {{ position: absolute; top: 18px; left: 18px; background: rgba(15, 20, 28, 0.88); color: #e2e8f0; padding: 16px 20px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.1); z-index: 10; font-size: 0.88rem; line-height: 1.6; backdrop-filter: blur(8px); max-width: 320px; }}
        .hud-panel h2 {{ margin: 0 0 8px 0; font-style: italic; color: #58a6ff; font-size: 1.35rem; }}
        .hud-hint {{ color: #58a6ff; font-size: 0.78rem; margin-top: 8px; }}
        .photo-panel {{
            position: absolute; bottom: 20px; right: 20px;
            width: 210px; background: rgba(15, 20, 28, 0.92);
            border: 2px solid #58a6ff; border-radius: 10px;
            overflow: hidden; z-index: 10; box-shadow: 0 8px 24px rgba(0,0,0,0.6);
            transform-origin: bottom right;
            transition: transform 0.3s cubic-bezier(0.25, 0.8, 0.25, 1), box-shadow 0.3s ease, border-color 0.3s ease;
            cursor: pointer;
        }}
        .photo-panel:hover {{
            transform: scale(1.4);
            border-color: #79c0ff;
            box-shadow: 0 16px 36px rgba(0,0,0,0.85), 0 0 16px rgba(88, 166, 255, 0.35);
        }}
        .photo-panel img {{ width: 100%; height: 165px; object-fit: cover; display: block; }}
        .photo-label {{ background: #161b22; color: #cbd5e0; text-align: center; font-size: 0.72rem; font-weight: 700; letter-spacing: 1px; padding: 7px 0; text-transform: uppercase; }}
        .back-btn {{ position: absolute; bottom: 20px; left: 20px; background: #238636; color: #ffffff; text-decoration: none; padding: 10px 18px; border-radius: 6px; font-size: 0.85rem; font-weight: 600; z-index: 10; display: inline-flex; align-items: center; gap: 6px; box-shadow: 0 4px 12px rgba(0,0,0,0.4); transition: background 0.2s; }}
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
        const camera = new THREE.PerspectiveCamera(42, window.innerWidth / window.innerHeight, 0.1, 3000);
        const renderer = new THREE.WebGLRenderer({{ antialias: true, alpha: true }});
        renderer.setSize(window.innerWidth, window.innerHeight);
        renderer.setPixelRatio(window.devicePixelRatio);
        document.body.appendChild(renderer.domElement);
        const controls = new THREE.OrbitControls(camera, renderer.domElement);
        controls.enableDamping = true;
        controls.dampingFactor = 0.06;
        scene.add(new THREE.AmbientLight(0xffffff, 0.75));
        const dirLight1 = new THREE.DirectionalLight(0xfff8e7, 0.78);
        dirLight1.position.set(60, 80, 90);
        scene.add(dirLight1);
        const dirLight2 = new THREE.DirectionalLight(0x88bbff, 0.38);
        dirLight2.position.set(-60, -40, -60);
        scene.add(dirLight2);

        const vertices = [];
        const vColors = [];
        const vcPositions = [];
        const vcColors = [];
        const groups = {{}};
        let currentMat = "Mat_CorolaLimbo";
        const NL_CHAR = String.fromCharCode(10);

        objRaw.split(NL_CHAR).forEach(line => {{
            const parts = line.trim().split(' ').filter(Boolean);
            if (!parts.length) return;
            if (parts[0] === 'v') {{
                vertices.push([parseFloat(parts[1]), parseFloat(parts[2]), parseFloat(parts[3])]);
                if (parts.length >= 7) {{
                    vColors.push([parseFloat(parts[4]), parseFloat(parts[5]), parseFloat(parts[6])]);
                }} else {{
                    vColors.push(null);
                }}
            }} else if (parts[0] === 'usemtl') {{
                currentMat = parts[1];
                if (!groups[currentMat]) groups[currentMat] = [];
            }} else if (parts[0] === 'f') {{
                const idx = parts.slice(1).map(p => parseInt(p.split('/')[0], 10) - 1);
                if (idx.length >= 3 && vertices[idx[0]] && vertices[idx[1]] && vertices[idx[2]]) {{
                    if (vColors[idx[0]]) {{
                        vcPositions.push(...vertices[idx[0]], ...vertices[idx[1]], ...vertices[idx[2]]);
                        vcColors.push(...vColors[idx[0]], ...vColors[idx[1]], ...vColors[idx[2]]);
                    }} else {{
                        if (!groups[currentMat]) groups[currentMat] = [];
                        groups[currentMat].push(...vertices[idx[0]], ...vertices[idx[1]], ...vertices[idx[2]]);
                    }}
                }}
            }}
        }});

        const flowerGroup = new THREE.Group();
        if (vcPositions.length > 0) {{
            const geom = new THREE.BufferGeometry();
            geom.setAttribute('position', new THREE.Float32BufferAttribute(vcPositions, 3));
            geom.setAttribute('color', new THREE.Float32BufferAttribute(vcColors, 3));
            geom.computeVertexNormals();
            const mat = new THREE.MeshStandardMaterial({{ vertexColors: true, roughness: 0.42, metalness: 0.05, side: THREE.DoubleSide }});
            flowerGroup.add(new THREE.Mesh(geom, mat));
        }}

        Object.keys(groups).forEach(matName => {{
            const pos = groups[matName];
            if (pos.length === 0) return;
            const geom = new THREE.BufferGeometry();
            geom.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
            geom.computeVertexNormals();
            const mat = new THREE.MeshStandardMaterial({{ color: palette[matName] || '#ffffff', roughness: 0.44, metalness: 0.05, side: THREE.DoubleSide }});
            flowerGroup.add(new THREE.Mesh(geom, mat));
        }});

        scene.add(flowerGroup);

        if (vcPositions.length > 0) {{
            const box = new THREE.Box3().setFromObject(flowerGroup);
            const center = box.getCenter(new THREE.Vector3());
            const size = box.getSize(new THREE.Vector3());
            flowerGroup.position.sub(center);
            const maxDim = Math.max(size.x, size.y, size.z) || 100;
            camera.position.set(maxDim * 0.85, maxDim * 0.25, maxDim * 1.15);
            controls.target.set(0, 0, 0);
            controls.update();
        }} else {{
            camera.position.set(0, 75, 145);
            controls.target.set(0, 0, 0);
            controls.update();
        }}

        window.addEventListener('resize', () => {{
            camera.aspect = window.innerWidth / window.innerHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(window.innerWidth, window.innerHeight);
        }});
        function animate() {{ requestAnimationFrame(animate); controls.update(); renderer.render(scene, camera); }}
        animate();
    </script>
</body>
</html>"""
    with open(html_filepath, 'w', encoding='utf-8') as f:
        f.write(html_content)

