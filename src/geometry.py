import yaml
import math
import numpy as np

NL = chr(10)

def load_config(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def build_vertex(x, y, z):
    return f"v {x:.4f} {y:.4f} {z:.4f}" + NL


def build_face(v1, v2, v3):
    return f"f {v1} {v2} {v3}" + NL


def hex_to_rgb(hex_color):
    hex_color = str(hex_color).strip().lstrip('#')
    if len(hex_color) != 6:
        return (0.5, 0.5, 0.5)
    try:
        return tuple(int(hex_color[i:i+2], 16) / 255.0 for i in (0, 2, 4))
    except ValueError:
        return (0.5, 0.5, 0.5)


def np_hex_to_rgb(hex_str):
    hex_str = str(hex_str).strip().lstrip('#')
    return np.array([int(hex_str[i:i+2], 16) / 255.0 for i in (0, 2, 4)])


def create_material_mtl(cfg, mtl_filepath):
    perianto = cfg.get('perianto') or {}
    androceo = cfg.get('androceo') or {}
    gineceo = cfg.get('gineceo') or {}
    caliz = perianto.get('caliz') or {}
    corola = perianto.get('corola') or {}

    colors = {
        "Mat_Caliz": hex_to_rgb(caliz.get('color_hex', '#5A8F32')),
        "Mat_CorolaGarganta": hex_to_rgb(corola.get('color_garganta_hex', '#4A1238')),
        "Mat_CorolaLimbo": hex_to_rgb(corola.get('color_limbo_hex', '#9F7CBF')),
        "Mat_Filamento": hex_to_rgb(androceo.get('color_filamento_hex', '#D4DCB8')),
        "Mat_Antera": hex_to_rgb(androceo.get('color_antera_hex', '#D2CA4E')),
        "Mat_Ovario": hex_to_rgb(gineceo.get('color_ovario_hex', '#8DB84A')),
        "Mat_Estilo": hex_to_rgb(gineceo.get('color_estilo_hex', '#D4DCB8')),
        "Mat_CoronaVioleta": hex_to_rgb("#7A4FA0"),
        "Mat_Blanco": (0.95, 0.95, 0.98),
        # Colores para Orchidaceae (Cattleya)
        "Mat_PetaloLila": hex_to_rgb("#D8B8E8"),
        "Mat_LabeloPurpura": hex_to_rgb("#9E1256"),
        "Mat_LabeloAmarillo": hex_to_rgb("#FFB703"),
        "Mat_Columna": hex_to_rgb("#F8F5F2")
    }
    with open(mtl_filepath, 'w', encoding='utf-8') as f:
        f.write("# Materiales generados automaticamente" + NL)
        for mat_name, rgb in colors.items():
            f.write(NL + f"newmtl {mat_name}" + NL)
            f.write(f"Kd {rgb[0]:.4f} {rgb[1]:.4f} {rgb[2]:.4f}" + NL)
            f.write("Ka 0.2 0.2 0.2" + NL + "Ks 0.15 0.15 0.15" + NL + "Ns 12" + NL)
    return {k: '#' + ''.join(f'{int(c*255):02x}' for c in v) for k, v in colors.items()}


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


def add_tube(pts, r0, r1, sides, v_offset):
    out = []
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
        ux, uy, uz = (0, 1, 0) if abs(ty) < 0.9 else (1, 0, 0)
        nx, ny, nz = ty*uz - tz*uy, tz*ux - tx*uz, tx*uy - ty*ux
        nl = math.sqrt(nx*nx + ny*ny + nz*nz) or 1.0
        nx, ny, nz = nx/nl, ny/nl, nz/nl
        bx, by, bz = ty*nz - tz*ny, tz*nx - tx*nz, tx*ny - ty*nx
        for s in range(sides):
            ang = 2 * math.pi * s / sides
            ca, sa = math.cos(ang), math.sin(ang)
            out.append(build_vertex(x + r*(ca*nx + sa*bx), y + r*(ca*ny + sa*by), z + r*(ca*nz + sa*bz)))
    for i in range(n - 1):
        for s in range(sides):
            p1 = v_offset + i*sides + s
            p2 = v_offset + i*sides + (s + 1) % sides
            p3 = v_offset + (i + 1)*sides + s
            p4 = v_offset + (i + 1)*sides + (s + 1) % sides
            out.append(build_face(p1, p2, p3))
            out.append(build_face(p2, p4, p3))
    return "".join(out), v_offset + n * sides


