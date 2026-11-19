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

    fam_lower = str((cfg.get('colecta') or cfg.get('taxonomia') or {}).get('familia', '')).strip().lower()
    if fam_lower == 'asteraceae':
        lbl_caliz, lbl_corola, lbl_reprod, lbl_ovario = 'Involucro', 'Lígulas', 'Disco/Páleas', 'Recept./Aquenios'
    else:
        lbl_caliz, lbl_corola, lbl_reprod, lbl_ovario = 'Cáliz', 'Corola', 'Reprod.', 'Ovario'

    fam_lower = str((cfg.get('colecta') or cfg.get('taxonomia') or {}).get('familia', '')).strip().lower()
    if fam_lower == 'asteraceae':
        lbl_caliz, lbl_corola, lbl_reprod, lbl_ovario = 'Involucro', 'Lígulas', 'Disco/Páleas', 'Recept./Aquenios'
    else:
        lbl_caliz, lbl_corola, lbl_reprod, lbl_ovario = 'Cáliz', 'Corola', 'Reprod.', 'Ovario'

    html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name=\"author\" content=\"Sain Alexis Sepúlveda Murillo\">
    <meta name=\"copyright\" content=\"Copyright (c) 2026 Sain Alexis Sepúlveda Murillo - GPLv3 / CC BY-NC-SA 4.0\">
    <meta name=\"author\" content=\"Sain Alexis Sepúlveda Murillo\">
    <meta name=\"copyright\" content=\"Copyright (c) 2026 Sain Alexis Sepúlveda Murillo - GPLv3 / CC BY-NC-SA 4.0\">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Visor Botánico 3D - {sp_name}</title>
    <style>
        html, body {{ width: 100vw; height: 100vh; margin: 0; padding: 0; overflow: hidden; background-color: #0f1218; background-image: radial-gradient(circle at center, #1e2430 0%, #0f1218 100%); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; user-select: none; }}
        .hud-panel {{ position: absolute; top: 16px; left: 16px; background: rgba(15, 20, 28, 0.92); color: #e2e8f0; padding: 14px 16px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.14); z-index: 15; font-size: 0.85rem; line-height: 1.5; backdrop-filter: blur(8px); max-width: 315px; box-shadow: 0 8px 24px rgba(0,0,0,0.45); transition: all 0.2s ease; }}
        .hud-panel h2 {{ margin: 0; font-style: italic; color: #58a6ff; font-size: 1.18rem; line-height: 1.2; }}
        .hud-hint {{ color: #79c0ff; font-size: 0.75rem; margin-top: 8px; border-top: 1px solid rgba(255,255,255,0.08); padding-top: 6px; }}

        .dissect-panel {{ position: absolute; top: 14px; right: 14px; background: rgba(15, 20, 28, 0.90); color: #e2e8f0; padding: 11px 12px; border-radius: 12px; border: 1px solid rgba(88, 166, 255, 0.32); z-index: 18; width: 190px; backdrop-filter: blur(10px); box-shadow: 0 8px 24px rgba(0,0,0,0.55); transition: all 0.2s ease; }}
        .dissect-panel h3 {{ margin: 0; font-size: 0.88rem; text-transform: uppercase; letter-spacing: 0.7px; color: #58a6ff; }}

        .panel-header {{ display: flex; align-items: center; justify-content: space-between; gap: 10px; cursor: pointer; }}
        .panel-body {{ margin-top: 10px; }}
        .dissect-panel .panel-header {{ border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 6px; }}
        .minimized .panel-body {{ display: none !important; }}
        .minimized .panel-header {{ border-bottom: none; padding-bottom: 0; }}
        .hud-panel.minimized, .dissect-panel.minimized {{ width: auto; max-width: none; padding: 9px 12px; }}

        .panel-toggle-btn {{ background: rgba(88, 166, 255, 0.14); color: #79c0ff; border: 1px solid rgba(88, 166, 255, 0.35); border-radius: 6px; width: 26px; height: 24px; display: inline-flex; align-items: center; justify-content: center; font-size: 0.85rem; font-weight: 700; cursor: pointer; flex-shrink: 0; }}
        .panel-toggle-btn:hover {{ background: rgba(88, 166, 255, 0.28); }}

        .control-group {{ margin-bottom: 12px; }}
        .control-group label {{ display: flex; justify-content: space-between; font-size: 0.8rem; color: #cbd5e0; margin-bottom: 4px; }}
        .slider {{ width: 100%; accent-color: #58a6ff; cursor: pointer; height: 22px; }}
        .btn-grid {{ display: flex; flex-direction: column; gap: 5px; margin-bottom: 8px; }}
        .action-btn {{ background: #1f2937; color: #e2e8f0; border: 1px solid rgba(255,255,255,0.15); border-radius: 6px; padding: 8px 8px; font-size: 0.76rem; font-weight: 600; cursor: pointer; transition: all 0.2s; }}
        .action-btn:hover {{ background: #374151; border-color: #58a6ff; }}
        .action-btn.active {{ background: #1d4ed8; border-color: #79c0ff; color: #ffffff; }}
        .whorl-toggles {{ display: grid; grid-template-columns: 1fr 1fr; gap: 5px; font-size: 0.73rem; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 7px; }}
        .whorl-toggles label {{ display: flex; align-items: center; gap: 7px; cursor: pointer; color: #cbd5e0; }}

        #organ-tooltip {{ position: fixed; pointer-events: none; display: none; background: rgba(10, 14, 20, 0.96); color: #f8fafc; border: 1px solid #58a6ff; border-radius: 10px; padding: 11px 14px; font-size: 0.82rem; max-width: 280px; z-index: 35; box-shadow: 0 10px 28px rgba(0,0,0,0.8); line-height: 1.42; }}
        #organ-tooltip.pinned {{ pointer-events: auto; left: 50% !important; top: auto !important; bottom: 68px !important; transform: translateX(-50%); width: min(92vw, 350px); max-width: none; border-width: 1.5px; }}
        #organ-tooltip .tt-head {{ display: flex; justify-content: space-between; align-items: flex-start; gap: 8px; }}
        #organ-tooltip .tt-close {{ display: none; background: rgba(255,255,255,0.1); border: none; color: #cbd5e1; border-radius: 5px; padding: 2px 7px; font-size: 0.85rem; cursor: pointer; }}
        #organ-tooltip.pinned .tt-close {{ display: inline-block; }}
        #organ-tooltip .tt-title {{ color: #79c0ff; font-weight: 700; font-size: 0.92rem; margin-bottom: 2px; }}
        #organ-tooltip .tt-whorl {{ color: #fbbf24; font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.6px; margin-bottom: 5px; }}
        #organ-tooltip .tt-desc {{ color: #cbd5e1; font-size: 0.78rem; }}

        .photo-panel {{ position: absolute; bottom: 16px; right: 16px; width: 195px; background: rgba(15, 20, 28, 0.94); border: 1.5px solid #58a6ff; border-radius: 10px; overflow: hidden; z-index: 15; box-shadow: 0 8px 24px rgba(0,0,0,0.6); transform-origin: bottom right; transition: all 0.25s ease; }}
        @media (hover: hover) {{
            .photo-panel:not(.minimized):hover {{ transform: scale(1.38); box-shadow: 0 16px 36px rgba(0,0,0,0.85), 0 0 16px rgba(88, 166, 255, 0.35); }}
        }}
        .photo-panel img {{ width: 100%; height: 145px; object-fit: cover; display: block; }}
        .photo-label {{ background: #161b22; color: #cbd5e0; display: flex; align-items: center; justify-content: space-between; font-size: 0.68rem; font-weight: 700; letter-spacing: 0.7px; padding: 6px 9px; text-transform: uppercase; cursor: pointer; gap: 6px; }}
        .photo-panel.minimized {{ width: auto; border-radius: 999px; }}
        .photo-panel.minimized img {{ display: none; }}
        .photo-panel.minimized .photo-label {{ padding: 8px 13px; background: rgba(15, 20, 28, 0.94); color: #79c0ff; }}

        .back-btn {{ position: absolute; bottom: 16px; left: 16px; background: #238636; color: #ffffff; text-decoration: none; padding: 10px 16px; border-radius: 8px; font-size: 0.84rem; font-weight: 600; z-index: 15; display: inline-flex; align-items: center; gap: 6px; box-shadow: 0 4px 12px rgba(0,0,0,0.45); }}
        .back-btn:hover {{ background: #2ea043; }}

        @media (max-width: 768px) {{
            .hud-panel {{ top: 10px; left: 10px; max-width: calc(50vw - 14px); padding: 9px 11px; font-size: 0.78rem; }}
            .hud-panel:not(.minimized) {{ max-width: calc(100vw - 20px); right: 10px; z-index: 22; }}
            .hud-panel h2 {{ font-size: 0.96rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
            .hud-panel:not(.minimized) h2 {{ white-space: normal; }}

            .dissect-panel {{ top: 10px; right: 10px; width: auto; max-width: calc(50vw - 14px); padding: 9px 11px; }}
            .dissect-panel:not(.minimized) {{ width: 168px; max-width: 46vw; left: auto !important; right: 10px; z-index: 22; padding: 10px; }}
            .dissect-panel h3 {{ font-size: 0.76rem; letter-spacing: 0.3px; }}

            .back-btn {{ bottom: 12px; left: 12px; padding: 9px 13px; font-size: 0.8rem; }}
            .photo-panel {{ bottom: 12px; right: 12px; width: 150px; }}
            .photo-panel img {{ height: 112px; }}
        }}
    </style>
</head>
<body>
    <div class="hud-panel" id="hud-info-panel">
        <div class="panel-header" onclick="toggleViewerPanel('hud-info-panel', 'hud-dissect-panel')">
            <h2>{sp_name}</h2>
            <button type="button" class="panel-toggle-btn" id="btn-toggle-info" aria-label="Minimizar ficha">−</button>
        </div>
        <div class="panel-body">
            <div><strong>Familia:</strong> {fam}</div>
            <div><strong>Catálogo:</strong> {id_m}</div>
            <div><strong>Distribución:</strong> {loc}</div>
            <div><strong>Fuente:</strong> {fecha}</div>
            <div class="hud-hint" id="hud-controls-hint">• Cursor / Toque en órgano: Identificar estructura.<br>• Rotar: Clic izq / 1 dedo | Zoom: Rueda / Pellizco</div>
        </div>
    </div>

    <div class="dissect-panel" id="hud-dissect-panel">
        <div class="panel-header" onclick="toggleViewerPanel('hud-dissect-panel', 'hud-info-panel')">
            <h3>🔬 Disección</h3>
            <button type="button" class="panel-toggle-btn" id="btn-toggle-dissect" aria-label="Minimizar disección">−</button>
        </div>
        <div class="panel-body">
            <div class="control-group">
                <label><span>💥 Explosión</span><span id="exp-val">0%</span></label>
                <input type="range" id="explode-slider" class="slider" min="0" max="100" value="0">
            </div>
            <div class="btn-grid">
                <button id="btn-plate" class="action-btn">📐 Plantilla</button>
                <button id="btn-xray" class="action-btn">🔍 Rayos X</button>
                <button id="btn-cut" class="action-btn">🔪 Corte Sagital</button>
                <button id="btn-reset" class="action-btn">🔄 Ensamblar</button>
            </div>
            <div class="whorl-toggles">
                <label><input type="checkbox" class="whorl-cb" data-whorl="caliz" checked> {lbl_caliz}</label>
                <label><input type="checkbox" class="whorl-cb" data-whorl="corola" checked> {lbl_corola}</label>
                <label><input type="checkbox" class="whorl-cb" data-whorl="reproductivo" checked> {lbl_reprod}</label>
                <label><input type="checkbox" class="whorl-cb" data-whorl="ovario" checked> {lbl_ovario}</label>
            </div>
        </div>
    </div>

    <div id="organ-tooltip">
        <div class="tt-head">
            <div>
                <div class="tt-title" id="tt-title">Órgano</div>
                <div class="tt-whorl" id="tt-whorl">Verticilo</div>
            </div>
            <button type="button" class="tt-close" id="tt-close-btn" aria-label="Cerrar">✕</button>
        </div>
        <div class="tt-desc" id="tt-desc">Descripción</div>
    </div>

    <a href="../index.html" class="back-btn" onclick="if(window.parent && window.parent !== window){{ event.preventDefault(); if(window.disposeAtlasScene) window.disposeAtlasScene(); window.parent.postMessage('close-atlas-modal', '*'); }} else if(document.referrer && document.referrer.indexOf(location.host) !== -1 && history.length > 1){{ event.preventDefault(); history.back(); }}">⬅ Volver al catálogo</a>
    <div class="photo-panel" id="hud-photo-panel">
        <img src="{foto_campo}" alt="{sp_name}" onerror="this.parentElement.style.display='none';">
        <div class="photo-label" onclick="togglePhotoPanel()">
            <span id="photo-label-text">📷 Referencia</span>
            <span id="photo-toggle-icon">−</span>
        </div>
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

            // --- ARACEAE (Anthurium sanjorgense & Anthurium andraeanum) ---
            "Espata_Cuculada": {{ title: "Espata Cuculada", whorl: "Bráctea Modificada", cat: "caliz", desc: "Bráctea protectora lanceolada con gradiente vino a verde y acumen distal.", exp: [0, 45, -20], plate: [0, 65, 0] }},
            "Espata_Cordiforme": {{ title: "Espata Cordiforme Bullada", whorl: "Bráctea Modificada (Espata)", cat: "caliz", desc: "Bráctea abierta plano-convexa en forma de corazón con lóbulos basales (aurículas) extendidos, ápice acuminado y acabado céreo rojo carmín.", exp: [0, -8, -42], plate: [-65, 10, 0] }},
            "Estipite_Basal": {{ title: "Estípite Cilíndrico", whorl: "Eje Inflorescente", cat: "reproductivo", desc: "Segmento corto de articulación entre el espádice y el pedúnculo.", exp: [0, 5, 25], plate: [-25, 0, 0] }},
            "Espadice_Florifero": {{ title: "Espádice Péndulo", whorl: "Inflorescencia Carnosa", cat: "corola", desc: "Espiga cilíndrica con flores hermafroditas sésiles dispuestas en espiral.", exp: [0, -35, 35], plate: [35, 0, 0] }},
            "Espadice_Florifero_Externo": {{ title: "Espádice Florífero Externo", whorl: "Inflorescencia (Tépalos en Parísticas)", cat: "corola", desc: "Cilindro subulado inclinado a 35° con ápice subcónico cerrado y trama espiral densa de flores bisexuales diminutas.", exp: [0, 36, 48], plate: [0, 38, 0] }},
            "Androceo_Micro_Estambres": {{ title: "Capa de Micro-Estambres", whorl: "Androceo (88% del Radio)", cat: "reproductivo", desc: "Estrato estaminal subyacente a los tépalos que agrupa los 4 micro-estambres por cada flor perfecta del espádice.", exp: [0, 26, 34], plate: [55, 38, 0] }},
            "Gineceo_Ovarios": {{ title: "Matriz Ovárica Bilocular", whorl: "Anatomía Interna (Gineceo, 75% Radio)", cat: "ovario", desc: "Tejido reticular en panal compuesto por los ovarios súperos biloculares inmersos en la corteza carnosa del espádice.", exp: [0, 16, 20], plate: [-10, -38, 0] }},
            "Ovulos_Internos": {{ title: "Óvulos Primordiales", whorl: "Anatomía Interna (Semillas)", cat: "ovario", desc: "Centenares de primordios seminales anclados en los lóculos alrededor del eje vascular.", exp: [0, -15, 50], plate: [65, 0, 0] }},
            "Ovulos_Internos_Placentarios": {{ title: "Capa de Óvulos Placentarios", whorl: "Anatomía Interna (Lóculos Ováricos)", cat: "ovario", desc: "Multitud de cuerpos ovoides blanco-crema brillante insertados axialmente en los lóculos ováricos.", exp: [0, 8, 10], plate: [30, -38, 0] }},
            "Eje_Vascular_Interno": {{ title: "Eje Vascular Central", whorl: "Anatomía Interna (Estela Medular)", cat: "ovario", desc: "Cilindro vascular sólido color marfil que actúa como núcleo conductor de toda la inflorescencia.", exp: [0, 0, 0], plate: [68, -38, 0] }},
            "Pedunculo_Tallo": {{ title: "Pedúnculo Sólido", whorl: "Tallo Floral Principal", cat: "caliz", desc: "Eje cilíndrico sólido verde oliva oscuro unido de forma continua al nodo basal de la espata y el espádice.", exp: [0, -38, -18], plate: [-65, -48, 0] }},
           
             // --- PASSIFLORACEAE (Passiflora incarnata / P. vitifolia) ---
            "Pedicelo_Hipanto": {{ title: "Pedicelo y Copa del Hipanto", whorl: "Receptáculo Floral", cat: "caliz", desc: "Tallo floral y receptáculo acopado urceolado donde se insertan el perianto y la corona.", exp: [0, -25, 0], plate: [0, -50, 0] }},
            "Epicaliz_Bracteas_Involucrales": {{ title: "Brácteas Involucrales", whorl: "Epicáliz", cat: "caliz", desc: "3 brácteas foliáceas bajo el hipanto con glándulas nectaríferas extraflorales.", exp: [0, -40, 0], plate: [-35, -50, 0] }},
            "Caliz_Sepalos": {{ title: "Sépalos Carena-Corniculados (5)", whorl: "Cáliz", cat: "caliz", desc: "5 sépalos con envés verde, quilla dorsal (carina) y mucrón subapical (corniculum).", exp: [0, -12, 0], plate: [35, -50, 0] }},
            "Corola_Petalos": {{ title: "Pétalos Laminares (5)", whorl: "Corola", cat: "corola", desc: "5 pétalos membranáceos alternados con los sépalos, de contorno elíptico-obtuso.", exp: [0, 5, 0], plate: [0, 35, 0] }},
            "Corona_Filamentos_Radii": {{ title: "Corona Exterior (Radii)", whorl: "Paracorola Externa", cat: "corola", desc: "Verticilo de filamentos largos con bandeado cromático y ondulación distal.", exp: [0, 18, 0], plate: [-45, 35, 0] }},
            "Corona_Interna_Pali": {{ title: "Corona Interna (Pali)", whorl: "Paracorola Interna", cat: "corola", desc: "Anillos de filamentos cortos y capitados de color púrpura granate.", exp: [0, 26, 0], plate: [45, 35, 0] }},
            "Columna_Androginoforo": {{ title: "Androginóforo Columnar", whorl: "Eje Reproductivo", cat: "reproductivo", desc: "Columna que eleva el androceo y gineceo por encima de la corona.", exp: [0, 40, 0], plate: [-25, 0, 0] }},
            "Androceo_Estambres": {{ title: "Estambres y Anteras (5)", whorl: "Androceo", cat: "reproductivo", desc: "5 filamentos acintados y anteras biloculares en inserción dorsifija en 'T'.", exp: [0, 55, 0], plate: [25, 0, 0] }},
            "Gineceo_Ovario_Supero": {{ title: "Ovario Súpero", whorl: "Gineceo", cat: "ovario", desc: "Ovario globoso elevado sobre el androginóforo, de superficie velutina.", exp: [0, 68, 0], plate: [0, -15, 0] }},
            "Gineceo_Estilos_Estigmas": {{ title: "Estilos y Estigmas (3)", whorl: "Gineceo Apical", cat: "reproductivo", desc: "3 estilos claviformes rematados en estigmas sólidos reniformes.", exp: [0, 85, 0], plate: [45, -15, 0] }},
            "Ovulos_Placentacion_Parietal": {{ title: "Placentas Parietales y Óvulos", whorl: "Anatomía Interna", cat: "ovario", desc: "Cavidad unilocular con 3 cordones parietales y óvulos anátropos.", exp: [0, 68, 0], plate: [0, -15, 0] }},
            "Camara_Nectarifera_Interna": {{ title: "Cámara Nectarífera y Opérculo", whorl: "Anatomía Interna", cat: "ovario", desc: "Cavidad anular cerrada por el opérculo membranoso plicado y el toroide secretor.", exp: [0, -6, 0], plate: [-45, -15, 0] }},
            "Eje_Vascular_Interno": {{ title: "Sistema Vascular Central", whorl: "Anatomía Interna", cat: "ovario", desc: "Cilindro vascular que ramifica hacia los 5 estambres y las 3 placentas.", exp: [0, 15, 0], plate: [25, -15, 0] }},


            // --- ASTERACEAE / ESPELETIINAE (Espeletia grandiflora) ---
            "Pedunculo_Lanoso": {{ title: "Pedúnculo Floral Lanoso", whorl: "Eje de la Sinflorescencia", cat: "caliz", desc: "Pedúnculo cilíndrico grueso revestido por denso tomento lanoso blanco-ocráceo que aísla térmicamente el capítulo frente a las heladas del páramo.", exp: [0, -32, -12], plate: [0, -58, 0] }},
            "Involucro_Filarias_Lanosas": {{ title: "Involucro Pluriseriado (Filarias)", whorl: "Involucro Protector (3–4 Series)", cat: "caliz", desc: "Filarias imbricadas ovado-lanceoladas cubiertas de indumento lanoso-velloso que protegen el capítulo en yema y antesis.", exp: [0, -18, -8], plate: [-56, -28, 0] }},
            "Receptaculo_Parenquima": {{ title: "Receptáculo Carnoso Parenquimatoso", whorl: "Base del Capítulo (Sección Interna)", cat: "ovario", desc: "Receptáculo sólido ligeramente convexo de parénquima crema-verdoso que soporta las flores periféricas fértiles y el disco estaminado.", exp: [0, -6, 0], plate: [0, -18, 0] }},
            "Plexo_Vascular_Capitulo": {{ title: "Plexo Vascular del Capítulo", whorl: "Anatomía Interna (Haces Vasculares)", cat: "ovario", desc: "Cilindro vascular central que asciende por el pedúnculo y se ramifica en haces hacia los aquenios periféricos y flores del disco.", exp: [0, -2, 10], plate: [56, -28, 0] }},
            "Aquenios_Perifericos_Fertiles": {{ title: "Cipselas / Aquenios Periféricos (Epaposos)", whorl: "Frutos Fértiles (3.2–4.0 mm, sin Vilano)", cat: "ovario", desc: "Aquenios obovoides-trígonos glabros de color pardo oscuro a negro, formados exclusivamente en las flores liguladas femeninas y carentes de vilano.", exp: [0, 8, 8], plate: [-56, 24, 0] }},
            "Flores_Liguladas_Femeninas": {{ title: "Flores Liguladas Radiales (Femeninas)", whorl: "Periferia del Capítulo (2–3 Series)", cat: "corola", desc: "Flores pistiladas fértiles con lígulas linear-oblongas amarillo ocre-dorado, ápice tridentado y estilo bífido exserto que atraen a abejorros (Bombus).", exp: [0, 18, 14], plate: [0, 44, 0] }},
            "Paleas_Receptaculares": {{ title: "Páleas Receptaculares Escariosas", whorl: "Brácteas del Receptáculo", cat: "reproductivo", desc: "Escamas cóncavas (naviculares) escariosas de ápice pubescente que abrazan individualmente las flores tubulosas del disco.", exp: [0, 22, 16], plate: [56, 24, 0] }},
            "Flores_Tubulosas_Disco": {{ title: "Flores Tubulosas del Disco (Estaminadas)", whorl: "Disco Central (Espiral de Fibonacci)", cat: "reproductivo", desc: "Flósculos funcionalmente masculinos con corola amarilla 5-lobada, sinantero pardo-negruzco exserto, presentación secundaria de polen y ovario estéril.", exp: [0, 32, 22], plate: [0, 14, 0] }},

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

        scene.add(new THREE.AmbientLight(0xffffff, 0.46));
        scene.add(new THREE.HemisphereLight(0xf6fff2, 0x221b2c, 0.44));
        const dirLight1 = new THREE.DirectionalLight(0xfff8ec, 0.92);
        dirLight1.position.set(55, 85, 95);
        scene.add(dirLight1);
        const dirLight2 = new THREE.DirectionalLight(0x9ac4ff, 0.46);
        dirLight2.position.set(-68, -32, -62);
        scene.add(dirLight2);
        const dirLight3 = new THREE.DirectionalLight(0xfff4e0, 0.26);
        dirLight3.position.set(0, -65, 50);
        scene.add(dirLight3);

        const sagittalPlane = new THREE.Plane(new THREE.Vector3(-1, 0, 0), 0);

        const vx = [], vy = [], vz = [];
        const vr = [], vg = [], vb = [], hasCol = [];
        const organMap = {{}};
        let currentGroup = "";
        let currentMat = "Mat_CorolaLimbo";
        let activeBucket = null;
        const lines = objRaw.split(String.fromCharCode(10));

        for (let i = 0, n = lines.length; i < n; i++) {{
            const line = lines[i].trim();
            if (!line) continue;
            const c0 = line.charCodeAt(0);
            if (c0 === 118 && line.charCodeAt(1) === 32) {{
                const p = line.split(' ');
                vx.push(+p[1]); vy.push(+p[2]); vz.push(+p[3]);
                if (p.length >= 7) {{
                    vr.push(+p[4]); vg.push(+p[5]); vb.push(+p[6]);
                    hasCol.push(1);
                }} else {{
                    vr.push(0); vg.push(0); vb.push(0);
                    hasCol.push(0);
                }}
            }} else if (c0 === 102 && line.charCodeAt(1) === 32) {{
                if (!activeBucket) {{
                    const key = currentGroup || currentMat || "Estructura_Base";
                    if (!organMap[key]) organMap[key] = {{ pos: [], col: [], mat: currentMat }};
                    activeBucket = organMap[key];
                }}
                const p = line.split(' ');
                const i0 = parseInt(p[1], 10) - 1;
                const i1 = parseInt(p[2], 10) - 1;
                const i2 = parseInt(p[3], 10) - 1;
                if (i0 >= 0 && i1 >= 0 && i2 >= 0 && i0 < vx.length) {{
                    activeBucket.pos.push(
                        vx[i0], vy[i0], vz[i0],
                        vx[i1], vy[i1], vz[i1],
                        vx[i2], vy[i2], vz[i2]
                    );
                    if (hasCol[i0]) {{
                        activeBucket.col.push(
                            vr[i0], vg[i0], vb[i0],
                            vr[i1], vg[i1], vb[i1],
                            vr[i2], vg[i2], vb[i2]
                        );
                    }}
                }}
            }} else if (c0 === 103 && line.charCodeAt(1) === 32) {{
                currentGroup = line.slice(2).trim() || "Organo_Floral";
                const key = currentGroup || currentMat || "Estructura_Base";
                if (!organMap[key]) organMap[key] = {{ pos: [], col: [], mat: currentMat }};
                activeBucket = organMap[key];
            }} else if (line.startsWith("usemtl ")) {{
                currentMat = line.slice(7).trim();
                const key = currentGroup || currentMat || "Estructura_Base";
                if (!organMap[key]) organMap[key] = {{ pos: [], col: [], mat: currentMat }};
                activeBucket = organMap[key];
            }}
        }}

        window.disposeAtlasScene = function() {{
            try {{
                interactMeshes.forEach(m => {{
                    if (m.geometry) m.geometry.dispose();
                    if (m.material) m.material.dispose();
                }});
                renderer.dispose();
            }} catch(e) {{}}
        }};

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
                cutMode = false;
                renderer.localClippingEnabled = false;
                const cutBtn = document.getElementById('btn-cut');
                if (cutBtn) cutBtn.classList.remove('active');
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
                const isInternal = (
                    k === 'Ovulos_Placentacion' || 
                    k === 'Ginostemio_Columna' || 
                    k === 'Antera_Polinios' ||
                    k === 'Ovulos_Placentacion_Parietal' || 
                    k === 'Camara_Nectarifera_Interna' || 
                    k === 'Eje_Vascular_Interno' ||
                    k === 'Ovulos_Internos' ||
                    k === 'Ovulos_Internos_Placentarios'
                );
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

        // Gestión de paneles minimizables y adaptación móvil/tablet
        function syncPanelIcons() {{
            const infoP = document.getElementById('hud-info-panel');
            const dissP = document.getElementById('hud-dissect-panel');
            const photoP = document.getElementById('hud-photo-panel');
            if (infoP) document.getElementById('btn-toggle-info').textContent = infoP.classList.contains('minimized') ? '+' : '−';
            if (dissP) document.getElementById('btn-toggle-dissect').textContent = dissP.classList.contains('minimized') ? '+' : '−';
            if (photoP) {{
                const isMin = photoP.classList.contains('minimized');
                document.getElementById('photo-toggle-icon').textContent = isMin ? '+' : '−';
                document.getElementById('photo-label-text').textContent = isMin ? '📷 Referencia' : 'ESPÉCIMEN';
            }}
        }}

        window.toggleViewerPanel = function(targetId, otherId) {{
            const target = document.getElementById(targetId);
            const other = document.getElementById(otherId);
            const willOpen = target.classList.contains('minimized');
            target.classList.toggle('minimized');
            if (willOpen && window.innerWidth <= 768 && other) {{
                other.classList.add('minimized');
            }}
            syncPanelIcons();
        }};

        window.togglePhotoPanel = function() {{
            const photoP = document.getElementById('hud-photo-panel');
            if (!photoP) return;
            photoP.classList.toggle('minimized');
            syncPanelIcons();
        }};

        if (window.innerWidth <= 768) {{
            document.getElementById('hud-info-panel').classList.add('minimized');
            document.getElementById('hud-dissect-panel').classList.add('minimized');
            document.getElementById('hud-photo-panel').classList.add('minimized');
        }}
        syncPanelIcons();

        const raycaster = new THREE.Raycaster();
        const mouse = new THREE.Vector2();
        const tooltip = document.getElementById('organ-tooltip');
        const ttTitle = document.getElementById('tt-title');
        const ttWhorl = document.getElementById('tt-whorl');
        const ttDesc = document.getElementById('tt-desc');
        let hoveredMesh = null;
        let pinnedTouch = false;

        function clearOrganHighlight() {{
            if (hoveredMesh) {{
                hoveredMesh.material.emissive.setHex(0x000000);
                hoveredMesh = null;
            }}
            pinnedTouch = false;
            tooltip.classList.remove('pinned');
            tooltip.style.display = 'none';
        }}

        document.getElementById('tt-close-btn').addEventListener('click', e => {{
            e.stopPropagation();
            clearOrganHighlight();
        }});

        function inspectAtClientXY(clientX, clientY, isTapPin) {{
            mouse.x = (clientX / window.innerWidth) * 2 - 1;
            mouse.y = -(clientY / window.innerHeight) * 2 + 1;
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

                if (isTapPin || window.innerWidth <= 768) {{
                    pinnedTouch = true;
                    tooltip.classList.add('pinned');
                }} else {{
                    pinnedTouch = false;
                    tooltip.classList.remove('pinned');
                    const leftPos = Math.min(window.innerWidth - 295, Math.max(12, clientX + 16));
                    const topPos = Math.min(window.innerHeight - 130, Math.max(12, clientY + 16));
                    tooltip.style.left = leftPos + 'px';
                    tooltip.style.top = topPos + 'px';
                }}
            }} else {{
                clearOrganHighlight();
            }}
        }}

        renderer.domElement.addEventListener('pointermove', e => {{
            if (e.pointerType !== 'mouse' || pinnedTouch) return;
            inspectAtClientXY(e.clientX, e.clientY, false);
        }});

        let downPt = {{ x: 0, y: 0, t: 0 }};
        renderer.domElement.addEventListener('pointerdown', e => {{
            downPt = {{ x: e.clientX, y: e.clientY, t: performance.now() }};
        }});

        renderer.domElement.addEventListener('pointerup', e => {{
            const dist = Math.hypot(e.clientX - downPt.x, e.clientY - downPt.y);
            const dt = performance.now() - downPt.t;
            if (dist < 9 && dt < 380) {{
                inspectAtClientXY(e.clientX, e.clientY, e.pointerType !== 'mouse');
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