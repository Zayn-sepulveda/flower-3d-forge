import sys
import os
from datetime import datetime
from geometry import NL, load_config, create_material_mtl
from viewer import export_interactive_viewer_html
from families.araceae import build_araceae_inflorescence
from families.passifloraceae import build_passiflora_flower
from families.asteraceae import build_asteraceae_capitulum
from families.orchidaceae import build_orchidaceae_flower
from families.heliconiaceae import build_heliconiaceae_inflorescence

def generate_flower_3d(cfg):
    specie_filename = cfg["colecta"]["especie"].lower().replace(" ", "_")
    os.makedirs("models", exist_ok=True)
    obj_filepath = os.path.join("models", f"{specie_filename}.obj")
    mtl_filepath = os.path.join("models", f"{specie_filename}.mtl")
    html_filepath = os.path.join("models", f"{specie_filename}.html")

    color_map = create_material_mtl(cfg, mtl_filepath)
    familia = cfg["colecta"]["familia"].strip()

    if familia == "Araceae":
        obj_data = build_araceae_inflorescence(cfg)
    elif familia == "Asteraceae":
        obj_data = build_asteraceae_capitulum(cfg)
    elif familia == "Orchidaceae":
        obj_data = build_orchidaceae_flower(cfg)
    elif familia == "Heliconiaceae":
        obj_data = build_heliconiaceae_inflorescence(cfg)
    else:
        obj_data = build_passiflora_flower(cfg)

    with open(obj_filepath, "w", encoding="utf-8") as f:
        f.write(f"mtllib {specie_filename}.mtl" + NL + obj_data)

    export_interactive_viewer_html(cfg, obj_data, color_map, html_filepath)
    size_kb = os.path.getsize(html_filepath) / 1024.0
    now_str = datetime.now().strftime("%H:%M:%S")
    print(f"✅ [{now_str}] Modelo 3D generado: {html_filepath} ({size_kb:.1f} KB)")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(1)
    generate_flower_3d(load_config(sys.argv[1]))
