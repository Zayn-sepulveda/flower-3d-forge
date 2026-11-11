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
    <title>Visor Botánico 3D - {sp_name}</title>
    <style>
        html, body {{ width: 100vw; height: 100vh; margin: 0; padding: 0; overflow: hidden; background-color: #0f1218; background-image: radial-gradient(circle at center, #1e2430 0%, #0f1218 100%); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; user-select: none; }}
        .hud-panel {{ position: absolute; top: 18px; left: 18px; background: rgba(15, 20, 28, 0.90); color: #e2e8f0; padding: 16px 20px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.12); z-index: 10; font-size: 0.86rem; line-height: 1.55; backdrop-filter: blur(8px); max-width: 310px; }}
        .hud-panel h2 {{ margin: 0 0 6px 0; font-style: italic; color: #58a6ff; font-size: 1.3rem; }}
        .hud-hint {{ color: #79c0ff; font-size: 0.76rem; margin-top: 8px; }}

        .dissect-panel {{ position: absolute; top: 18px; right: 18px; background: rgba(15, 20, 28, 0.92); color: #e2e8f0; padding: 16px 18px; border-radius: 10px; border: 1px solid rgba(88, 166, 255, 0.28); z-index: 10; width: 280px; backdrop-filter: blur(8px); box-shadow: 0 8px 24px rgba(0,0,0,0.5); }}
        .dissect-panel h3 {{ margin: 0 0 10px 0; font-size: 0.92rem; text-transform: uppercase; letter-spacing: 0.8px; color: #58a6ff; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 6px; }}
        .control-group {{ margin-bottom: 12px; }}
        .control-group label {{ display: flex; justify-content: space-between; font-size: 0.8rem; color: #cbd5e0; margin-bottom: 4px; }}
        .slider {{ width: 100%; accent-color: #58a6ff; cursor: pointer; }}
        .btn-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 6px; margin-bottom: 10px; }}
        .action-btn {{ background: #1f2937; color: #e2e8f0; border: 1px solid rgba(255,255,255,0.15); border-radius: 6px; padding: 7px 8px; font-size: 0.76rem; font-weight: 600; cursor: pointer; transition: all 0.2s; }}
        .action-btn:hover {{ background: #374151; border-color: #58a6ff; }}
        .action-btn.active {{ background: #1d4ed8; border-color: #79c0ff; color: #ffffff; }}
        .whorl-toggles {{ display: flex; flex-direction: column; gap: 4px; font-size: 0.78rem; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 8px; }}
        .whorl-toggles label {{ display: flex; align-items: center; gap: 6px; cursor: pointer; color: #cbd5e0; }}

        #organ-tooltip {{ position: fixed; pointer-events: none; display: none; background: rgba(10, 14, 20, 0.95); color: #f8fafc; border: 1px solid #58a6ff; border-radius: 8px; padding: 10px 14px; font-size: 0.8rem; max-width: 260px; z-index: 30; box-shadow: 0 8px 20px rgba(0,0,0,0.75); line-height: 1.4; }}
        #organ-tooltip .tt-title {{ color: #79c0ff; font-weight: 700; font-size: 0.9rem; margin-bottom: 3px; }}
        #organ-tooltip .tt-whorl {{ color: #fbbf24; font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.6px; margin-bottom: 5px; }}
        #organ-tooltip .tt-desc {{ color: #cbd5e1; font-size: 0.77rem; }}

        .photo-panel {{ position: absolute; bottom: 20px; right: 20px; width: 200px; background: rgba(15, 20, 28, 0.92); border: 2px solid #58a6ff; border-radius: 10px; overflow: hidden; z-index: 10; box-shadow: 0 8px 24px rgba(0,0,0,0.6); transform-origin: bottom right; transition: transform 0.3s cubic-bezier(0.25, 0.8, 0.25, 1), box-shadow 0.3s ease; cursor: pointer; }}
        .photo-panel:hover {{ transform: scale(1.4); box-shadow: 0 16px 36px rgba(0,0,0,0.85), 0 0 16px rgba(88, 166, 255, 0.35); }}
        .photo-panel img {{ width: 100%; height: 155px; object-fit: cover; display: block; }}
        .photo-label {{ background: #161b22; color: #cbd5e0; text-align: center; font-size: 0.7rem; font-weight: 700; letter-spacing: 1px; padding: 6px 0; text-transform: uppercase; }}
        .back-btn {{ position: absolute; bottom: 20px; left: 20px; background: #238636; color: #ffffff; text-decoration: none; padding: 10px 18px; border-radius: 6px; font-size: 0.85rem; font-weight: 600; z-index: 10; display: inline-flex; align-items: center; gap: 6px; box-shadow: 0 4px 12px rgba(0,0,0,0.4); }}
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
        <div class="hud-hint">• Pasa el cursor sobre la flor para identificar cada órgano.<br>• Rotar: Clic izq | Zoom: Rueda | Mover: Clic der</div>
    </div>

    <div class="dissect-panel">
        <h3>🔬 Disección Botánica</h3>
        <div class="control-group">
            <label><span>Separar Verticilos (Explosión)</span><span id="exp-val">0%</span></label>
            <input type="range" id="explode-slider" class="slider" min="0" max="100" value="0">
        </div>
        <div class="btn-grid">
            <button id="btn-plate" class="action-btn">📐 Modo Plantilla</button>
            <button id="btn-xray" class="action-btn">🔍 Rayos X Ovario</button>
            <button id="btn-cut" class="action-btn">🔪 Corte Sagital</button>
            <button id="btn-reset" class="action-btn">🔄 Ensamblar</button>
        </div>
        <div class="whorl-toggles">
            <label><input type="checkbox" class="whorl-cb" data-whorl="caliz" checked> Cáliz (Sépalos / Filarias)</label>
            <label><input type="checkbox" class="whorl-cb" data-whorl="corola" checked> Corola (Pétalos / Labelo)</label>
            <label><input type="checkbox" class="whorl-cb" data-whorl="reproductivo" checked> Androceo y Gineceo (Columna)</label>
            <label><input type="checkbox" class="whorl-cb" data-whorl="ovario" checked> Ovario y Óvulos Internos</label>
        </div>
    </div>

    <div id="organ-tooltip">
        <div class="tt-title" id="tt-title">Órgano</div>
        <div class="tt-whorl" id="tt-whorl">Verticilo</div>
        <div class="tt-desc" id="tt-desc">Descripción</div>
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

       const ANATOMY_DB = {{
            // --- ORCHIDACEAE (Cattleya) ---
            "Sepalo_Dorsal": {{ title: "Sépalo Dorsal", whorl: "Cáliz (Verticilo Externo)", cat: "caliz", desc: "Tépalo externo erecto (83 × 20 mm). Protege la yema floral antes de la antesis.", exp: [0, 42, -28], plate: [0, 58, 0] }},
            "Sepalo_Lateral_Izq": {{ title: "Sépalo Lateral Izquierdo", whorl: "Cáliz (Verticilo Externo)", cat: "caliz", desc: "Sépalo lanceolado subfalcado descendente.", exp: [-35, -30, -28], plate: [-55, -48, 0] }},
            "Sepalo_Lateral_Der": {{ title: "Sépalo Lateral Derecho", whorl: "Cáliz (Verticilo Externo)", cat: "caliz", desc: "Sépalo lanceolado subfalcado descendente.", exp: [35, -30, -28], plate: [55, -48, 0] }},
            "Petalo_Lateral_Izq": {{ title: "Pétalo Lateral Izquierdo", whorl: "Corola (Perianto Interno)", cat: "corola", desc: "Pétalo romboidal ancho con margen ondulado-fimbriado (85 × 60 mm).", exp: [-48, 15, -8], plate: [-78, 18, 0] }},
            "Petalo_Lateral_Der": {{ title: "Pétalo Lateral Derecho", whorl: "Corola (Perianto Interno)", cat: "corola", desc: "Pétalo romboidal ancho con margen ondulado-fimbriado (85 × 60 mm).", exp: [48, 15, -8], plate: [78, 18, 0] }},
            "Labelo_Trilobulado": {{ title: "Labelo Trilobulado Convoluto", whorl: "Corola Modificada", cat: "corola", desc: "Pétalo medio especializado: tubo basal que envuelve la columna y limbo tricolor como plataforma de polinización.", exp: [0, -38, 42], plate: [0, -32, 10] }},
            "Ginostemio_Columna": {{ title: "Ginostemio (Columna)", whorl: "Androceo + Gineceo Fusionados", cat: "reproductivo", desc: "Órgano reproductivo semicilíndrico arqueado (28 mm) característico de Orchidaceae.", exp: [0, 14, 26], plate: [-28, -52, 10] }},
            "Antera_Polinios": {{ title: "Antera Apical y Polinios", whorl: "Androceo", cat: "reproductivo", desc: "Cápsula operculada terminal que aloja las masas de polen ceroso (polinios).", exp: [0, 22, 46], plate: [28, -52, 10] }},
            "Ovario_Infero": {{ title: "Ovario Pedicelado Ínfero", whorl: "Gineceo (Receptáculo/Pedicelo)", cat: "ovario", desc: "Ovario ínfero 6-acanalado situado por debajo de la inserción del perianto y resupinado 180°.", exp: [0, -25, -45], plate: [-55, -85, 0] }},
            "Ovulos_Placentacion": {{ title: "Placentas Parietales y Óvulos", whorl: "Gineceo Interno (Cavidad Ovárica)", cat: "ovario", desc: "Tres cordones placentarios parietales con miles de primordios seminales microscópicos dentro del ovario ínfero.", exp: [0, -10, -25], plate: [55, -85, 0] }},

            // --- ARACEAE (Anthurium) ---
            "Espata_Cuculada": {{ title: "Espata Cuculada", whorl: "Bráctea Modificada", cat: "caliz", desc: "Bráctea protectora lanceolada con gradiente vino a verde y acumen distal.", exp: [0, 45, -20], plate: [0, 65, 0] }},
            "Estipite_Basal": {{ title: "Estípite Cilíndrico", whorl: "Eje Inflorescente", cat: "reproductivo", desc: "Segmento corto de articulación entre el espádice y el pedúnculo.", exp: [0, 5, 25], plate: [-25, 0, 0] }},
            "Espadice_Florifero": {{ title: "Espádice Péndulo", whorl: "Inflorescencia Carnosa", cat: "corola", desc: "Espiga cilíndrica con flores hermafroditas sésiles dispuestas en espiral.", exp: [0, -35, 35], plate: [35, 0, 0] }},
            "Gineceo_Ovarios": {{ title: "Matriz Ovárica Bilocular", whorl: "Anatomía Interna (Gineceo)", cat: "ovario", desc: "Red de ovarios súperos que conforman la estructura carnosa bajo la superficie del espádice.", exp: [0, -25, 45], plate: [50, 0, 0] }},
            "Ovulos_Internos": {{ title: "Óvulos Primordiales", whorl: "Anatomía Interna (Semillas)", cat: "ovario", desc: "Centenares de primordios seminales anclados en los lóculos alrededor del eje vascular.", exp: [0, -15, 50], plate: [65, 0, 0] }},
            "Eje_Vascular_Interno": {{ title: "Eje Vascular Central", whorl: "Anatomía Interna", cat: "ovario", desc: "Médula vascular interna visible en rayos X que irriga cada flor del espádice.", exp: [0, -15, 55], plate: [65, 0, 0] }},
            "Pedunculo_Tallo": {{ title: "Pedúnculo", whorl: "Tallo Principal", cat: "ovario", desc: "Eje de soporte principal de la inflorescencia.", exp: [0, -55, -25], plate: [-55, -60, 0] }},

            // --- MATERIALES GENÉRICOS DE RESPALDO ---
            "Mat_Caliz": {{ title: "Cáliz / Brácteas", whorl: "Cáliz", cat: "caliz", desc: "Verticilo externo de protección floral.", exp: [0, -25, 0], plate: [-50, 30, 0] }},
            "Mat_CorolaLimbo": {{ title: "Limbo de la Corola", whorl: "Corola", cat: "corola", desc: "Verticilo de atracción óptica.", exp: [0, 15, 0], plate: [0, 30, 0] }},
            "Mat_CorolaGarganta": {{ title: "Garganta / Serie Basal", whorl: "Corola", cat: "corola", desc: "Zona basal del perianto o corona.", exp: [0, 8, 0], plate: [50, 30, 0] }},
            "Mat_Filamento": {{ title: "Filamentos Estaminales", whorl: "Androceo", cat: "reproductivo", desc: "Soporte de las anteras.", exp: [0, 25, 0], plate: [-40, -30, 0] }},
            "Mat_Antera": {{ title: "Anteras Polínicas", whorl: "Androceo", cat: "reproductivo", desc: "Sacos productores de polen.", exp: [0, 35, 0], plate: [0, -30, 0] }},
            "Mat_Ovario": {{ title: "Ovario", whorl: "Gineceo", cat: "ovario", desc: "Órgano ovulífero femenino.", exp: [0, 42, 0], plate: [40, -30, 0] }},
            "Mat_Estilo": {{ title: "Estilo y Estigma", whorl: "Gineceo", cat: "reproductivo", desc: "Conducto receptor de polen.", exp: [0, 52, 0], plate: [65, -30, 0] }}
        }};

        const scene = new THREE.Scene();
        const camera = new THREE.PerspectiveCamera(42, window.innerWidth / window.innerHeight, 0.1, 3000);
        const renderer = new THREE.WebGLRenderer({{ antialias: true, alpha: true }});
        renderer.setSize(window.innerWidth, window.innerHeight);
        renderer.setPixelRatio(window.devicePixelRatio);
        renderer.localClippingEnabled = false;
        document.body.appendChild(renderer.domElement);

        const controls = new THREE.OrbitControls(camera, renderer.domElement);
        controls.enableDamping = true;
        controls.dampingFactor = 0.06;

        scene.add(new THREE.AmbientLight(0xffffff, 0.78));
        const dirLight1 = new THREE.DirectionalLight(0xfff8e7, 0.82);
        dirLight1.position.set(60, 80, 90);
        scene.add(dirLight1);
        const dirLight2 = new THREE.DirectionalLight(0x88bbff, 0.42);
        dirLight2.position.set(-60, -40, -60);
        scene.add(dirLight2);

        const sagittalPlane = new THREE.Plane(new THREE.Vector3(-1, 0, 0), 0);

        const vertices = [];
        const vColors = [];
        const organMap = {{}};
        let currentGroup = "";
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
            }} else if (parts[0] === 'g') {{
                currentGroup = parts[1] || "Organo_Floral";
            }} else if (parts[0] === 'usemtl') {{
                currentMat = parts[1];
            }} else if (parts[0] === 'f') {{
                const key = currentGroup || currentMat || "Estructura_Base";
                if (!organMap[key]) organMap[key] = {{ pos: [], col: [], mat: currentMat }};
                const idx = parts.slice(1).map(p => parseInt(p.split('/')[0], 10) - 1);
                if (idx.length >= 3 && vertices[idx[0]] && vertices[idx[1]] && vertices[idx[2]]) {{
                    organMap[key].pos.push(...vertices[idx[0]], ...vertices[idx[1]], ...vertices[idx[2]]);
                    if (vColors[idx[0]]) {{
                        organMap[key].col.push(...vColors[idx[0]], ...vColors[idx[1]], ...vColors[idx[2]]);
                    }}
                }}
            }}
        }});

        const flowerGroup = new THREE.Group();
        const interactMeshes = [];

        Object.keys(organMap).forEach(key => {{
            const data = organMap[key];
            if (data.pos.length === 0) return;
            const geom = new THREE.BufferGeometry();
            geom.setAttribute('position', new THREE.Float32BufferAttribute(data.pos, 3));
            const hasVC = data.col.length === data.pos.length;
            if (hasVC) {{
                geom.setAttribute('color', new THREE.Float32BufferAttribute(data.col, 3));
            }}
            geom.computeVertexNormals();
            geom.computeBoundingBox();
            const natCenter = new THREE.Vector3();
            geom.boundingBox.getCenter(natCenter);

            const matOpts = {{
                roughness: 0.42,
                metalness: 0.05,
                side: THREE.DoubleSide,
                clippingPlanes: [sagittalPlane]
            }};
            if (hasVC) {{
                matOpts.vertexColors = true;
            }} else {{
                matOpts.color = palette[data.mat] || '#ffffff';
            }}

            const mat = new THREE.MeshStandardMaterial(matOpts);
            const mesh = new THREE.Mesh(geom, mat);
            const info = ANATOMY_DB[key] || {{
                title: key.replace(/_/g, ' '),
                whorl: "Estructura Floral",
                cat: "corola",
                desc: "Órgano generado paramétricamente a partir de la ficha YAML.",
                exp: [natCenter.x * 0.4, natCenter.y * 0.4, natCenter.z * 0.4],
                plate: [natCenter.x * 1.2, natCenter.y * 1.2, 0]
            }};

            mesh.userData = {{
                key: key,
                info: info,
                natCenter: natCenter,
                targetPos: new THREE.Vector3(0, 0, 0)
            }};

            flowerGroup.add(mesh);
            interactMeshes.push(mesh);
        }});

        scene.add(flowerGroup);

        const box = new THREE.Box3().setFromObject(flowerGroup);
        const center = box.getCenter(new THREE.Vector3());
        const size = box.getSize(new THREE.Vector3());
        flowerGroup.position.sub(center);
        sagittalPlane.constant = 0;

        const maxDim = Math.max(size.x, size.y, size.z) || 120;
        camera.position.set(0, maxDim * 0.15, maxDim * 1.35);
        controls.target.set(0, 0, 0);
        controls.update();

        let explodeFactor = 0.0;
        let plateMode = false;
        let xrayMode = false;
        let cutMode = false;

        function updateTargets() {{
            interactMeshes.forEach(m => {{
                const info = m.userData.info;
                const nc = m.userData.natCenter;
                if (plateMode) {{
                    m.userData.targetPos.set(
                        info.plate[0] - nc.x,
                        info.plate[1] - nc.y + center.y,
                        info.plate[2] - nc.z + center.z
                    );
                }} else {{
                    m.userData.targetPos.set(
                        info.exp[0] * explodeFactor,
                        info.exp[1] * explodeFactor,
                        info.exp[2] * explodeFactor
                    );
                }}
            }});
        }}

        const slider = document.getElementById('explode-slider');
        const expVal = document.getElementById('exp-val');
        slider.addEventListener('input', e => {{
            plateMode = false;
            document.getElementById('btn-plate').classList.remove('active');
            explodeFactor = parseFloat(e.target.value) / 100.0;
            expVal.textContent = e.target.value + '%';
            updateTargets();
        }});

        document.getElementById('btn-plate').addEventListener('click', function() {{
            plateMode = !plateMode;
            this.classList.toggle('active', plateMode);
            if (plateMode) {{
                camera.position.set(0, 0, maxDim * 1.75);
                controls.target.set(0, 0, 0);
            }}
            updateTargets();
        }});

        document.getElementById('btn-xray').addEventListener('click', function() {{
            xrayMode = !xrayMode;
            this.classList.toggle('active', xrayMode);
            interactMeshes.forEach(m => {{
                const k = m.userData.key;
                const isInternal = (k === 'Ovulos_Placentacion' || k === 'Ginostemio_Columna' || k === 'Antera_Polinios');
                if (xrayMode && !isInternal) {{
                    m.material.transparent = true;
                    m.material.opacity = 0.18;
                    m.material.depthWrite = false;
                }} else {{
                    m.material.transparent = false;
                    m.material.opacity = 1.0;
                    m.material.depthWrite = true;
                }}
                m.material.needsUpdate = true;
            }});
        }});

        document.getElementById('btn-cut').addEventListener('click', function() {{
            cutMode = !cutMode;
            this.classList.toggle('active', cutMode);
            renderer.localClippingEnabled = cutMode;
            if (cutMode) {{
                camera.position.set(maxDim * 1.15, -maxDim * 0.1, maxDim * 0.55);
                controls.target.set(0, -10, 0);
            }}
        }});

        document.getElementById('btn-reset').addEventListener('click', () => {{
            explodeFactor = 0;
            plateMode = false;
            xrayMode = false;
            cutMode = false;
            slider.value = 0;
            expVal.textContent = '0%';
            renderer.localClippingEnabled = false;
            document.querySelectorAll('.action-btn').forEach(b => b.classList.remove('active'));
            interactMeshes.forEach(m => {{
                m.material.transparent = false;
                m.material.opacity = 1.0;
                m.material.depthWrite = true;
                m.visible = true;
            }});
            document.querySelectorAll('.whorl-cb').forEach(cb => cb.checked = true);
            camera.position.set(0, maxDim * 0.15, maxDim * 1.35);
            controls.target.set(0, 0, 0);
            updateTargets();
        }});

        document.querySelectorAll('.whorl-cb').forEach(cb => {{
            cb.addEventListener('change', e => {{
                const cat = e.target.getAttribute('data-whorl');
                interactMeshes.forEach(m => {{
                    if (m.userData.info.cat === cat) {{
                        m.visible = e.target.checked;
                    }}
                }});
            }});
        }});

        const raycaster = new THREE.Raycaster();
        const mouse = new THREE.Vector2();
        const tooltip = document.getElementById('organ-tooltip');
        const ttTitle = document.getElementById('tt-title');
        const ttWhorl = document.getElementById('tt-whorl');
        const ttDesc = document.getElementById('tt-desc');
        let hoveredMesh = null;

        window.addEventListener('mousemove', e => {{
            if (e.target !== renderer.domElement) {{
                tooltip.style.display = 'none';
                return;
            }}
            mouse.x = (e.clientX / window.innerWidth) * 2 - 1;
            mouse.y = -(e.clientY / window.innerHeight) * 2 + 1;
            raycaster.setFromCamera(mouse, camera);

            const visibleMeshes = interactMeshes.filter(m => m.visible && (!xrayMode || m.material.opacity > 0.5));
            const intersects = raycaster.intersectObjects(visibleMeshes);

            if (hoveredMesh) {{
                hoveredMesh.material.emissive.setHex(0x000000);
                hoveredMesh = null;
            }}

            if (intersects.length > 0) {{
                hoveredMesh = intersects[0].object;
                hoveredMesh.material.emissive.setHex(0x283b5c);
                const info = hoveredMesh.userData.info;
                ttTitle.textContent = info.title;
                ttWhorl.textContent = info.whorl;
                ttDesc.textContent = info.desc;
                tooltip.style.display = 'block';
                tooltip.style.left = (e.clientX + 16) + 'px';
                tooltip.style.top = (e.clientY + 16) + 'px';
            }} else {{
                tooltip.style.display = 'none';
            }}
        }});

        window.addEventListener('resize', () => {{
            camera.aspect = window.innerWidth / window.innerHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(window.innerWidth, window.innerHeight);
        }});

        function animate() {{
            requestAnimationFrame(animate);
            interactMeshes.forEach(m => {{
                m.position.lerp(m.userData.targetPos, 0.12);
            }});
            controls.update();
            renderer.render(scene, camera);
        }}
        animate();
    </script>
</body>
</html>"""
    with open(html_filepath, 'w', encoding='utf-8') as f:
        f.write(html_content)