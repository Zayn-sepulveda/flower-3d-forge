import math
import random
from geometry import NL


def _clamp(v, lo=0.0, hi=1.0):
    return lo if v < lo else (hi if v > hi else v)


def _ss(e0, e1, x):
    t = _clamp((x - e0) / (e1 - e0 if abs(e1 - e0) > 1e-9 else 1.0))
    return t * t * (3.0 - 2.0 * t)


def _lerp_col(c1, c2, t):
    t = _clamp(t)
    return (
        c1[0] + (c2[0] - c1[0]) * t,
        c1[1] + (c2[1] - c1[1]) * t,
        c1[2] + (c2[2] - c1[2]) * t,
    )


def _shade(c, f):
    return (_clamp(c[0] * f), _clamp(c[1] * f), _clamp(c[2] * f))


def _noise2(x, y, seed=0.0):
    return (
        0.52 * math.sin(x * 1.13 + y * 0.71 + seed)
        + 0.31 * math.cos(x * 2.41 - y * 1.93 + seed * 1.7)
        + 0.17 * math.sin(x * 4.37 + y * 3.89 - seed * 2.3)
    )


class _AsterMesh:
    """Constructor rapido de mallas OBJ con grupos anatomicos (g) y vertex colors."""

    def __init__(self, tilt_deg=32.0):
        self.lines = []
        self.v_count = 0
        rad = math.radians(tilt_deg)
        self.ct = math.cos(rad)
        self.st = math.sin(rad)

    def orient(self, x, y, z):
        # Rotacion en torno al eje X: preserva x=0 intacto para el Corte Sagital
        return (x, y * self.ct - z * self.st, y * self.st + z * self.ct)

    def group(self, name):
        self.lines.append(f"g {name}")

    def material(self, name):
        self.lines.append(f"usemtl {name}")

    def v(self, x, y, z, r, g, b, transform=True):
        if transform:
            x, y, z = self.orient(x, y, z)
        self.v_count += 1
        self.lines.append(f"v {x:.4f} {y:.4f} {z:.4f} {r:.4f} {g:.4f} {b:.4f}")
        return self.v_count

    def f(self, a, b, c):
        self.lines.append(f"f {a} {b} {c}")

    def quad(self, a, b, c, d):
        self.lines.append(f"f {a} {b} {d}")
        self.lines.append(f"f {a} {d} {c}")

    def add_tube(self, pts, radii, colors, radial_segs=8, cap_start=False, cap_end=False):
        n = len(pts)
        if n < 2:
            return
        rings = []
        for i in range(n):
            px, py, pz = pts[i]
            if i < n - 1:
                dx, dy, dz = pts[i + 1][0] - px, pts[i + 1][1] - py, pts[i + 1][2] - pz
            else:
                dx, dy, dz = px - pts[i - 1][0], py - pts[i - 1][1], pz - pts[i - 1][2]
            dl = math.sqrt(dx * dx + dy * dy + dz * dz) or 1.0
            tx, ty, tz = dx / dl, dy / dl, dz / dl

            ux, uy, uz = (0.0, 1.0, 0.0) if abs(ty) < 0.88 else (1.0, 0.0, 0.0)
            nx = ty * uz - tz * uy
            ny = tz * ux - tx * uz
            nz = tx * uy - ty * ux
            nl = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
            nx, ny, nz = nx / nl, ny / nl, nz / nl

            bx = ty * nz - tz * ny
            by = tz * nx - tx * nz
            bz = tx * ny - ty * nx

            rad = radii[i]
            col = colors[i]
            ring = []
            for s in range(radial_segs):
                ang = s * (2.0 * math.pi / radial_segs)
                ca, sa = math.cos(ang), math.sin(ang)
                vx = px + rad * (ca * nx + sa * bx)
                vy = py + rad * (ca * ny + sa * by)
                vz = pz + rad * (ca * nz + sa * bz)
                ring.append(self.v(vx, vy, vz, *col))
            rings.append(ring)

        for i in range(n - 1):
            for s in range(radial_segs):
                sn = (s + 1) % radial_segs
                self.quad(rings[i][s], rings[i][sn], rings[i + 1][s], rings[i + 1][sn])

        if cap_start:
            c0 = self.v(*pts[0], *colors[0])
            for s in range(radial_segs):
                sn = (s + 1) % radial_segs
                self.f(c0, rings[0][sn], rings[0][s])
        if cap_end:
            c1 = self.v(*pts[-1], *colors[-1])
            for s in range(radial_segs):
                sn = (s + 1) % radial_segs
                self.f(c1, rings[-1][s], rings[-1][sn])

    def add_wool_tuft(self, base_pt, dir_vec, side_vec, length, width, col_base, col_tip, bend_vec):
        """Agrega un penacho de tricomas lanosos (cinta curva fina de 2 segmentos)."""
        bx, by, bz = base_pt
        dx, dy, dz = dir_vec
        sx, sy, sz = side_vec
        kx, ky, kz = bend_vec

        hw0 = width * 0.52
        hw1 = width * 0.30
        c_mid = _lerp_col(col_base, col_tip, 0.55)

        p0l = self.v(bx - sx * hw0, by - sy * hw0, bz - sz * hw0, *col_base)
        p0r = self.v(bx + sx * hw0, by + sy * hw0, bz + sz * hw0, *col_base)

        mx = bx + dx * (length * 0.52) + kx * (length * 0.16)
        my = by + dy * (length * 0.52) + ky * (length * 0.16)
        mz = bz + dz * (length * 0.52) + kz * (length * 0.16)
        p1l = self.v(mx - sx * hw1, my - sy * hw1, mz - sz * hw1, *c_mid)
        p1r = self.v(mx + sx * hw1, my + sy * hw1, mz + sz * hw1, *c_mid)

        tx = bx + dx * length + kx * (length * 0.42)
        ty = by + dy * length + ky * (length * 0.42)
        tz = bz + dz * length + kz * (length * 0.42)
        p2 = self.v(tx, ty, tz, *col_tip)

        self.quad(p0l, p0r, p1l, p1r)
        self.f(p1l, p1r, p2)

    def build_obj(self):
        return NL.join(self.lines) + NL


def build_asteraceae_capitulum(cfg):
    """
    Reconstruccion morfometrica y anatomica 3D de alta fidelidad de Espeletia grandiflora
    (Asteraceae: Millerieae: Espeletiinae).

    Genera 8 grupos anatomicos verificados:
      1. Pedunculo_Lanoso
      2. Involucro_Filarias_Lanosas
      3. Receptaculo_Parenquima (con plano parenquimatoso solido interno para Corte Sagital)
      4. Plexo_Vascular_Capitulo (sistema vascular 3D + relieve en plano sagital)
      5. Aquenios_Perifericos_Fertiles (cipselas obovoides oscuras epaposas, 3.8 mm)
      6. Flores_Liguladas_Femeninas (3 series densas, ocre-dorado, apice tridentado, estilo bifido)
      7. Paleas_Receptaculares (bracteas escariosas naviculares)
      8. Flores_Tubulosas_Disco (funcionalmente masculinas, Fibonacci, sinantero pardo, polen dorado)
    """
    corola_cfg = cfg.get("perianto", {}).get("corola") or {}
    caliz_cfg = cfg.get("perianto", {}).get("caliz") or {}

    tilt_deg = float(
        (corola_cfg.get("diferenciacion_dorsoventral") or {}).get("curvatura_dorsal_grados", 32.0)
    )
    mb = _AsterMesh(tilt_deg=tilt_deg)

    # Dimensiones calibradas en mm para Espeletia grandiflora
    r_disco = 12.2  # Diametro del disco ~24.4 mm
    n_filarias_cfg = int(caliz_cfg.get("sepalos_numero", 44))
    l_filaria_base = float(caliz_cfg.get("longitud_tubo_mm", 16.5))
    n_ligulas = max(56, min(88, int(corola_cfg.get("petalos_numero", 74))))
    l_ligula_base = float(corola_cfg.get("longitud_limbo_mm", 14.5))
    w_ligula_base = float(corola_cfg.get("ancho_petalo_mm", 3.1))

    # Curva suave del pedunculo (en plano Y-Z, preservando X=0)
    def ped_center(t):
        # t=0 abajo (-48 mm), t=1 union bajo el involucro (-10.5 mm)
        y = -48.0 * (1.0 - t) - 10.5 * t
        z = -7.5 * ((1.0 - t) ** 1.7)
        return (0.0, y, z)

    def ped_radius(t):
        # Pedunculo grueso (Ø ~7.0-8.6 mm) que ensancha suavemente al entrar al involucro
        return 3.55 + 0.45 * t + 2.8 * (t ** 4.2)

    def dome_y(r):
        frac = min(1.0, r / r_disco)
        return 3.45 * (1.0 - 0.88 * (frac ** 1.85))

    # =========================================================================
    # 1. PEDÚNCULO GRUESO CON INDUMENTO LANOSO (g Pedunculo_Lanoso)
    # =========================================================================
    mb.group("Pedunculo_Lanoso")
    mb.material("Mat_Caliz")

    n_ped_rings, s_ped = 26, 24
    ped_rings = []
    for i in range(n_ped_rings):
        t = i / (n_ped_rings - 1)
        cx, cy, cz = ped_center(t)
        r_base = ped_radius(t)
        ring = []
        for s in range(s_ped):
            ang = s * (2.0 * math.pi / s_ped)
            ca, sa = math.cos(ang), math.sin(ang)
            n_bump = _noise2(ang * 3.5, t * 14.0, seed=1.3)
            r_loc = r_base + 0.38 * n_bump
            # Paleta tomentosa crema-plateada a ocre suave con AO en surcos
            ao = 0.80 + 0.22 * (0.5 + 0.5 * n_bump)
            c_wool = _lerp_col((0.64, 0.59, 0.47), (0.86, 0.83, 0.74), _clamp(0.45 + 0.48 * n_bump))
            c_wool = _lerp_col(c_wool, (0.76, 0.72, 0.60), _ss(0.65, 1.0, t) * 0.35)
            ring.append(mb.v(cx + r_loc * ca, cy, cz + r_loc * sa, *_shade(c_wool, ao)))
        ped_rings.append(ring)

    for i in range(n_ped_rings - 1):
        for s in range(s_ped):
            sn = (s + 1) % s_ped
            mb.quad(ped_rings[i][s], ped_rings[i][sn], ped_rings[i + 1][s], ped_rings[i + 1][sn])

    # Tapa basal cerrada (elimina artefacto de agujero blanco)
    bx0, by0, bz0 = ped_center(0.0)
    bot_c = mb.v(bx0, by0, bz0, 0.55, 0.51, 0.40)
    for s in range(s_ped):
        sn = (s + 1) % s_ped
        mb.f(bot_c, ped_rings[0][sn], ped_rings[0][s])

    # Penachos lanosos procedurales cubriendo el pedunculo
    rng_ped = random.Random(105)
    for _ in range(340):
        t = rng_ped.uniform(0.03, 0.96)
        ang = rng_ped.uniform(0.0, 2.0 * math.pi)
        ca, sa = math.cos(ang), math.sin(ang)
        cx, cy, cz = ped_center(t)
        r_loc = ped_radius(t) + 0.05
        bx = cx + r_loc * ca
        bz = cz + r_loc * sa
        by = cy + rng_ped.uniform(-0.4, 0.4)

        # Direccion lanosa ligeramente ascendente/despeinada
        up_bias = rng_ped.uniform(0.15, 0.78)
        tang_j = rng_ped.uniform(-0.45, 0.45)
        dx = ca + (-sa) * tang_j
        dy = up_bias
        dz = sa + ca * tang_j
        dl = math.sqrt(dx * dx + dy * dy + dz * dz) or 1.0
        dx, dy, dz = dx / dl, dy / dl, dz / dl

        sx, sy, sz = -sa, rng_ped.uniform(-0.3, 0.3), ca
        sl = math.sqrt(sx * sx + sy * sy + sz * sz) or 1.0
        sx, sy, sz = sx / sl, sy / sl, sz / sl

        tuft_len = rng_ped.uniform(1.6, 3.1)
        tuft_w = rng_ped.uniform(0.55, 1.05)
        col_b = _lerp_col((0.68, 0.63, 0.50), (0.80, 0.76, 0.64), rng_ped.random())
        col_t = _lerp_col((0.86, 0.84, 0.77), (0.95, 0.94, 0.90), rng_ped.random())
        bend = (rng_ped.uniform(-0.5, 0.5), rng_ped.uniform(0.2, 0.7), rng_ped.uniform(-0.5, 0.5))
        mb.add_wool_tuft((bx, by, bz), (dx, dy, dz), (sx, sy, sz), tuft_len, tuft_w, col_b, col_t, bend)

    # =========================================================================
    # 2. INVOLUCRO HEMISFÉRICO PLURISERADO DE FILARIAS LANOSAS (g Involucro_Filarias_Lanosas)
    # =========================================================================
    mb.group("Involucro_Filarias_Lanosas")
    mb.material("Mat_Caliz")

    # 4 series imbricadas de filarias anchas ovado-lanceoladas abrazando el receptaculo
    series_cfg = [
        {"cnt": 9,  "r_ins": 5.2,  "y_ins": -10.4, "len": l_filaria_base * 0.84, "w": 8.4, "out_r": 8.2,  "rise": 7.6,  "th": 1.05, "wool": 12},
        {"cnt": 11, "r_ins": 7.4,  "y_ins": -8.8,  "len": l_filaria_base * 0.95, "w": 7.6, "out_r": 7.6,  "rise": 9.8,  "th": 0.92, "wool": 11},
        {"cnt": 12, "r_ins": 9.5,  "y_ins": -6.6,  "len": l_filaria_base * 1.00, "w": 6.4, "out_r": 6.6,  "rise": 10.6, "th": 0.78, "wool": 9},
        {"cnt": 12, "r_ins": 11.1, "y_ins": -4.2,  "len": l_filaria_base * 0.92, "w": 4.9, "out_r": 5.4,  "rise": 9.6,  "th": 0.60, "wool": 5},
    ]

    rng_inv = random.Random(205)
    nu_f, nv_f = 9, 6

    for s_idx, sc in enumerate(series_cfg):
        cnt = sc["cnt"]
        for k in range(cnt):
            ang = k * (2.0 * math.pi / cnt) + s_idx * 0.29 + rng_inv.uniform(-0.07, 0.07)
            ca, sa = math.cos(ang), math.sin(ang)
            tx, tz = -sa, ca

            l_var = sc["len"] * rng_inv.uniform(0.92, 1.08)
            w_var = sc["w"] * rng_inv.uniform(0.92, 1.08)
            r_ins = sc["r_ins"] + rng_inv.uniform(-0.25, 0.25)
            y_ins = sc["y_ins"] + rng_inv.uniform(-0.35, 0.35)
            flare = rng_inv.uniform(-0.6, 0.9)

            in_grid, out_grid = [], []
            for i in range(nu_f + 1):
                u = i / nu_f
                # Contorno anchamente ovado-lanceolado (obtuso en series externas, mas agudo en internas)
                if s_idx <= 1:
                    w_prof = math.sin(math.pi * (u ** 0.56)) * (1.0 - 0.16 * (u ** 1.8))
                else:
                    w_prof = math.sin(math.pi * (u ** 0.62)) * (1.0 - 0.24 * (u ** 1.6))
                w_loc = (w_var * 0.5) * max(0.04, w_prof)

                # Trayectoria hemisferica acopada abrazando el receptaculo
                r_curr = r_ins + sc["out_r"] * math.sin(u * math.pi * 0.62) + (2.0 + flare) * (u ** 1.7)
                y_curr = y_ins + sc["rise"] * (u ** 0.86) - 1.2 * (u ** 2.6)
                th_loc = sc["th"] * (1.0 - 0.68 * (u ** 1.3))

                row_in, row_out = [], []
                for j in range(nv_f + 1):
                    v = (j / nv_f) - 0.5
                    av = abs(v)
                    lat = v * 2.0 * w_loc

                    # Concavidad envolvente hacia el interior del capitulo
                    cup_rad = -1.75 * (v * v) * (1.0 - 0.35 * u)
                    n_tex = _noise2(u * 9.0 + k * 1.3, v * 8.0 + s_idx * 2.1, seed=float(s_idx + k))
                    bump_out = 0.42 * n_tex * (1.0 - 0.35 * u)

                    px_in = (r_curr + cup_rad) * ca + lat * tx
                    pz_in = (r_curr + cup_rad) * sa + lat * tz
                    py_in = y_curr

                    # Cara abaxial externa desplazada radialmente hacia afuera/abajo
                    px_out = (r_curr + cup_rad + th_loc + bump_out) * ca + lat * tx
                    pz_out = (r_curr + cup_rad + th_loc + bump_out) * sa + lat * tz
                    py_out = y_curr - th_loc * 0.48 - abs(bump_out) * 0.2

                    # Coloracion abaxial lanosa plateado-crema con fondo pardo-oliva suave
                    ao_b = 0.72 + 0.28 * _ss(0.0, 0.35, u)
                    edge_light = _ss(0.28, 0.50, av)
                    wool_tone = _lerp_col((0.56, 0.51, 0.39), (0.86, 0.83, 0.74), _clamp(0.42 + 0.45 * n_tex + 0.22 * edge_light))
                    if s_idx == 3:
                        wool_tone = _lerp_col(wool_tone, (0.74, 0.69, 0.48), 0.38)
                    c_out = _shade(wool_tone, ao_b)

                    # Cara adaxial interna pardo-verdosa/escariosa (visible en Corte Sagital)
                    c_in = _lerp_col((0.46, 0.42, 0.30), (0.68, 0.62, 0.45), u)
                    c_in = _shade(c_in, 0.82 + 0.18 * u)

                    row_in.append(mb.v(px_in, py_in, pz_in, *c_in))
                    row_out.append(mb.v(px_out, py_out, pz_out, *c_out))
                in_grid.append(row_in)
                out_grid.append(row_out)

            for i in range(nu_f):
                for j in range(nv_f):
                    mb.quad(out_grid[i][j], out_grid[i][j + 1], out_grid[i + 1][j], out_grid[i + 1][j + 1])
                    mb.quad(in_grid[i][j + 1], in_grid[i][j], in_grid[i + 1][j + 1], in_grid[i + 1][j])
                mb.quad(in_grid[i][0], out_grid[i][0], in_grid[i + 1][0], out_grid[i + 1][0])
                mb.quad(out_grid[i][-1], in_grid[i][-1], out_grid[i + 1][-1], in_grid[i + 1][-1])

            # Penachos lanosos brotando del dorso y margenes de cada filaria
            for _ in range(sc["wool"]):
                u_t = rng_inv.uniform(0.15, 0.94)
                v_t = rng_inv.uniform(-0.48, 0.48)
                w_prof = math.sin(math.pi * (u_t ** 0.58)) * (1.0 - 0.18 * (u_t ** 1.7))
                w_loc = (w_var * 0.5) * max(0.05, w_prof)
                r_curr = r_ins + sc["out_r"] * math.sin(u_t * math.pi * 0.62) + (2.0 + flare) * (u_t ** 1.7)
                y_curr = y_ins + sc["rise"] * (u_t ** 0.86) - 1.2 * (u_t ** 2.6)
                cup_rad = -1.75 * (v_t * v_t) * (1.0 - 0.35 * u_t)

                bx = (r_curr + cup_rad + sc["th"] * 0.75) * ca + (v_t * 2.0 * w_loc) * tx
                bz = (r_curr + cup_rad + sc["th"] * 0.75) * sa + (v_t * 2.0 * w_loc) * tz
                by = y_curr - 0.25

                dx = ca * 0.82 + tx * (v_t * 0.9 + rng_inv.uniform(-0.3, 0.3))
                dy = rng_inv.uniform(0.25, 0.85)
                dz = sa * 0.82 + tz * (v_t * 0.9 + rng_inv.uniform(-0.3, 0.3))
                dl = math.sqrt(dx * dx + dy * dy + dz * dz) or 1.0
                dx, dy, dz = dx / dl, dy / dl, dz / dl

                t_len = rng_inv.uniform(1.6, 3.2) * (1.05 if abs(v_t) > 0.32 else 0.88)
                t_w = rng_inv.uniform(0.55, 1.05)
                c_b = _lerp_col((0.68, 0.63, 0.50), (0.82, 0.78, 0.68), rng_inv.random())
                c_t = _lerp_col((0.88, 0.86, 0.80), (0.96, 0.95, 0.92), rng_inv.random())
                bend = (ca * 0.25 + rng_inv.uniform(-0.3, 0.3), rng_inv.uniform(0.2, 0.6), sa * 0.25 + rng_inv.uniform(-0.3, 0.3))
                mb.add_wool_tuft((bx, by, bz), (dx, dy, dz), (tx, 0.15, tz), t_len, t_w, c_b, c_t, bend)

    # =========================================================================
    # 3. RECEPTÁCULO CARNOSO SÓLIDO Y PLANO PARENQUIMATOSO SAGITAL (g Receptaculo_Parenquima)
    # =========================================================================
    mb.group("Receptaculo_Parenquima")
    mb.material("Mat_Ovario")

    # Cascaron externo cerrado del receptaculo (domo superior convexo + cuenco inferior)
    s_rec = 32
    rec_prof = [
        # Domo superior donde se asientan las flores (de centro a borde)
        (0.25, dome_y(0.25), (0.76, 0.74, 0.58)),
        (3.5,  dome_y(3.5),  (0.78, 0.76, 0.60)),
        (7.2,  dome_y(7.2),  (0.80, 0.78, 0.62)),
        (10.5, dome_y(10.5), (0.81, 0.78, 0.62)),
        (12.2, dome_y(12.2), (0.78, 0.76, 0.58)),
        # Pared inferior carnosa del receptaculo bajando al pedunculo
        (11.6, -1.8, (0.72, 0.71, 0.54)),
        (10.4, -4.6, (0.68, 0.68, 0.52)),
        (8.4,  -7.2, (0.64, 0.65, 0.49)),
        (5.4,  -9.4, (0.60, 0.62, 0.46)),
        (3.6,  -11.2, (0.58, 0.60, 0.44)),
    ]
    rec_rings = []
    for r_c, y_c, col_c in rec_prof:
        ring = []
        for s in range(s_rec):
            ang = s * (2.0 * math.pi / s_rec)
            ring.append(mb.v(r_c * math.cos(ang), y_c, r_c * math.sin(ang), *col_c))
        rec_rings.append(ring)

    top_center_rec = mb.v(0.0, dome_y(0.0), 0.0, 0.76, 0.74, 0.58)
    for s in range(s_rec):
        sn = (s + 1) % s_rec
        mb.f(top_center_rec, rec_rings[0][s], rec_rings[0][sn])
    for i in range(len(rec_rings) - 1):
        for s in range(s_rec):
            sn = (s + 1) % s_rec
            mb.quad(rec_rings[i][s], rec_rings[i][sn], rec_rings[i + 1][s], rec_rings[i + 1][sn])

    # Seccion sagital solida del parenquima interno en x = -0.08 mm
    # (100% oculta dentro del volumen cuando la flor esta intacta; visible al activar Corte Sagital)
    x_cap = -0.08
    cap_center = (0.0, -3.6)  # (z, y) centro del parenquima del receptaculo
    cap_poly = []
    # Borde superior (z de -11.4 a +11.4) siguiendo la convexidad del receptaculo
    for i in range(17):
        frac = -1.0 + 2.0 * (i / 16.0)
        z_p = 11.4 * frac
        y_p = dome_y(abs(z_p)) - 0.32
        cap_poly.append((z_p, y_p))
    # Contorno derecho del cuenco receptacular bajando al pedunculo (+Z)
    cap_poly.extend([
        (10.8, -2.0),
        (9.6, -4.8),
        (7.5, -7.3),
        (4.6, -9.4),
        (3.1, -11.5),
    ])
    # Borde derecho de la medula del pedunculo hasta abajo (+Z)
    for i in range(1, 13):
        t = 1.0 - (i / 12.0) * 0.96
        _, cy, cz = ped_center(t)
        r_m = ped_radius(t) - 0.55
        cap_poly.append((cz + r_m, cy))
    # Borde izquierdo de la medula del pedunculo subiendo (-Z)
    for i in range(12, 0, -1):
        t = 1.0 - (i / 12.0) * 0.96
        _, cy, cz = ped_center(t)
        r_m = ped_radius(t) - 0.55
        cap_poly.append((cz - r_m, cy))
    # Contorno izquierdo del cuenco receptacular (-Z)
    cap_poly.extend([
        (-3.1, -11.5),
        (-4.6, -9.4),
        (-7.5, -7.3),
        (-9.6, -4.8),
        (-10.8, -2.0),
    ])

    # Triangular el parenquima en 3 anillos concentricos suaves (centro marfil -> borde verdoso)
    c_pith_core = (0.93, 0.91, 0.83)
    c_pith_mid  = (0.89, 0.86, 0.76)
    c_pith_rim  = (0.76, 0.75, 0.62)

    n_poly = len(cap_poly)
    v_cap_center = mb.v(x_cap, cap_center[1], cap_center[0], *c_pith_core)
    ring_mid_cap = []
    ring_out_cap = []
    for z_p, y_p in cap_poly:
        # Interpolar hacia el eje central del pedunculo para puntos bajos
        if y_p < -11.0:
            t_est = _clamp((y_p + 48.0) / 37.5)
            _, _, cz_loc = ped_center(t_est)
            zm = cz_loc + (z_p - cz_loc) * 0.52
            ym = y_p
        else:
            zm = cap_center[0] + (z_p - cap_center[0]) * 0.58
            ym = cap_center[1] + (y_p - cap_center[1]) * 0.58
        n_cell = 0.96 + 0.04 * _noise2(z_p * 0.6, y_p * 0.6, seed=4.2)
        ring_mid_cap.append(mb.v(x_cap, ym, zm, *_shade(c_pith_mid, n_cell)))
        ring_out_cap.append(mb.v(x_cap, y_p, z_p, *_shade(c_pith_rim, n_cell)))

    for i in range(n_poly):
        inext = (i + 1) % n_poly
        mb.f(v_cap_center, ring_mid_cap[i], ring_mid_cap[inext])
        mb.quad(ring_mid_cap[i], ring_mid_cap[inext], ring_out_cap[i], ring_out_cap[inext])

    # =========================================================================
    # 4. PLEXO VASCULAR DEL CAPÍTULO (g Plexo_Vascular_Capitulo)
    # =========================================================================
    mb.group("Plexo_Vascular_Capitulo")
    mb.material("Mat_Filamento")

    c_vasc_main = (0.71, 0.69, 0.56)
    c_vasc_fine = (0.64, 0.63, 0.49)

    # Cilindro vascular central 3D en el pedunculo (visible en Rayos X y Corte Sagital)
    trunk_pts = []
    trunk_r = []
    for i in range(10):
        t = 0.04 + 0.96 * (i / 9.0)
        _, cy, cz = ped_center(t)
        trunk_pts.append((-0.18, cy, cz))
        trunk_r.append(0.75 + 0.35 * (t ** 2.0))
    trunk_pts.append((-0.18, -5.5, 0.0))
    trunk_r.append(1.25)
    mb.add_tube(trunk_pts, trunk_r, [c_vasc_main] * len(trunk_pts), radial_segs=8, cap_start=True, cap_end=True)

    # Haces vasculares dicotomicos en el plano sagital (x = -0.05 mm, relieve nitido sobre el parenquima)
    sag_targets = [-10.8, -8.8, -6.6, -4.2, -1.8, 1.8, 4.2, 6.6, 8.8, 10.8]
    for z_tgt in sag_targets:
        y_tgt = dome_y(abs(z_tgt)) - 0.65
        pts_v = [
            (-0.05, -14.0, -0.25 if z_tgt < 0 else 0.25),
            (-0.05, -8.5, z_tgt * 0.14),
            (-0.05, -4.2, z_tgt * 0.46),
            (-0.05, -1.2 + 0.4 * (1.0 - abs(z_tgt) / 12.0), z_tgt * 0.78),
            (-0.05, y_tgt, z_tgt),
        ]
        r_v = [0.22, 0.20, 0.17, 0.13, 0.09]
        mb.add_tube(pts_v, r_v, [c_vasc_fine] * len(pts_v), radial_segs=5, cap_end=True)

        # Sub-ramificacion lateral corta hacia flores vecinas
        z_sub = z_tgt * 0.82 + (0.9 if z_tgt > 0 else -0.9)
        if abs(z_sub) < 11.2:
            sub_pts = [
                pts_v[2],
                (-0.05, -1.4, (pts_v[2][2] + z_sub) * 0.5),
                (-0.05, dome_y(abs(z_sub)) - 0.65, z_sub),
            ]
            mb.add_tube(sub_pts, [0.13, 0.10, 0.07], [c_vasc_fine] * 3, radial_segs=4, cap_end=True)

    # Haces radiales 3D para vista de Rayos X (distribuidos en 12 azimuths)
    for k in range(12):
        ang = k * (2.0 * math.pi / 12.0) + 0.13
        ca, sa = math.cos(ang), math.sin(ang)
        if abs(ca) < 0.18:
            continue
        r_end = 10.4
        pts_3d = [
            (0.0, -9.0, 0.0),
            (r_end * 0.35 * ca, -5.0, r_end * 0.35 * sa),
            (r_end * 0.75 * ca, -1.5, r_end * 0.75 * sa),
            (r_end * ca, dome_y(r_end) - 0.6, r_end * sa),
        ]
        mb.add_tube(pts_3d, [0.28, 0.22, 0.16, 0.10], [c_vasc_main] * 4, radial_segs=5, cap_end=True)

    # =========================================================================
    # 5. AQUENIOS PERIFÉRICOS FÉRTILES (EPAPOSOS) Y 6. FLORES LIGULADAS FEMENINAS
    # =========================================================================
    # Pre-calcular las posiciones de las 3 series perifericas (compartidas entre aquenio y ligula)
    rng_lig = random.Random(305)
    ray_specs = []
    # Repartir n_ligulas en 3 series concentricas superpuestas (externa, media, interna)
    c0 = int(round(n_ligulas * 0.36))
    c1 = int(round(n_ligulas * 0.34))
    c2 = n_ligulas - c0 - c1
    ray_tiers = [
        {"cnt": c0, "r": 11.75, "len": l_ligula_base * 1.08, "w": w_ligula_base * 1.05, "pitch": -0.14, "droop": 3.4, "tilt_ach": 0.42},
        {"cnt": c1, "r": 11.15, "len": l_ligula_base * 1.00, "w": w_ligula_base * 0.98, "pitch":  0.03, "droop": 2.4, "tilt_ach": 0.30},
        {"cnt": c2, "r": 10.55, "len": l_ligula_base * 0.89, "w": w_ligula_base * 0.90, "pitch":  0.19, "droop": 1.6, "tilt_ach": 0.20},
    ]

    for t_idx, tc in enumerate(ray_tiers):
        cnt = tc["cnt"]
        for k in range(cnt):
            ang = k * (2.0 * math.pi / cnt) + t_idx * (math.pi / cnt) + rng_lig.uniform(-0.025, 0.025)
            ray_specs.append({
                "tier": t_idx,
                "ang": ang,
                "r": tc["r"] + rng_lig.uniform(-0.18, 0.18),
                "len": tc["len"] * rng_lig.uniform(0.91, 1.09),
                "w": tc["w"] * rng_lig.uniform(0.92, 1.08),
                "pitch": tc["pitch"] + rng_lig.uniform(-0.06, 0.06),
                "droop": tc["droop"] * rng_lig.uniform(0.75, 1.25),
                "twist": rng_lig.uniform(-0.16, 0.16),
                "tilt_ach": tc["tilt_ach"],
                "seed": rng_lig.uniform(0.0, 10.0),
            })

    # --- GRUPO 5: AQUENIOS / CIPSELAS OBOVOIDES FÉRTILES (3.8 mm, SIN VILANO) ---
    mb.group("Aquenios_Perifericos_Fertiles")
    mb.material("Mat_Ovario")

    ach_len = 3.8  # Rango verificado en Chisaca: 3.2 - 4.0 mm
    ach_r_max = 1.02
    na_u, na_v = 6, 7

    for sp in ray_specs:
        ang = sp["ang"]
        ca, sa = math.cos(ang), math.sin(ang)
        tx, tz = -sa, ca
        r0 = sp["r"]
        y0 = dome_y(r0) - 0.25

        # Eje del aquenio ligeramente inclinado hacia afuera sobre el borde del receptaculo
        ta = sp["tilt_ach"]
        ax_r, ax_y = math.sin(ta), math.cos(ta)
        # Vector perpendicular radial-vertical en el plano radial
        pr_r, pr_y = math.cos(ta), -math.sin(ta)

        ach_rings = []
        for i in range(na_u + 1):
            u = i / na_u
            # Perfil obovoide / obpiramidal tipico de Espeletia (mas ancho en el tercio superior)
            r_prof = ach_r_max * math.sin(math.pi * (u ** 0.72)) * (0.65 + 0.42 * u)
            r_prof = max(0.18, r_prof)
            cx = (r0 + ax_r * ach_len * u) * ca
            cz = (r0 + ax_r * ach_len * u) * sa
            cy = y0 + ax_y * ach_len * u

            ring = []
            for j in range(na_v):
                phi = j * (2.0 * math.pi / na_v)
                cp, sp_h = math.cos(phi), math.sin(phi)
                # Seccion ligeramente trigona-comprimida
                trig = 1.0 + 0.12 * math.cos(3.0 * phi)
                rad_d = r_prof * trig * 0.85 * cp
                lat_d = r_prof * trig * 1.05 * sp_h

                px = cx + (rad_d * pr_r) * ca + lat_d * tx
                pz = cz + (rad_d * pr_r) * sa + lat_d * tz
                py = cy + rad_d * pr_y

                # Pericarpio glabro pardo-castaño oscuro a negro brillante
                shine = 0.84 + 0.26 * (0.5 + 0.5 * math.cos(3.0 * phi)) * math.sin(math.pi * u)
                c_ach = _lerp_col((0.20, 0.12, 0.07), (0.36, 0.23, 0.13), u * 0.75)
                ring.append(mb.v(px, py, pz, *_shade(c_ach, shine)))
            ach_rings.append(ring)

        for i in range(na_u):
            for j in range(na_v):
                jn = (j + 1) % na_v
                mb.quad(ach_rings[i][j], ach_rings[i][jn], ach_rings[i + 1][j], ach_rings[i + 1][jn])

        # Guardar punto apical del aquenio para insertar el tubo de la ligula (sin vilano)
        sp["top_r"] = r0 + ax_r * ach_len
        sp["top_y"] = y0 + ax_y * ach_len

    # --- GRUPO 6: FLORES LIGULADAS FEMENINAS (3 SERIES, OCRE-DORADO, TRIDENTADAS) ---
    mb.group("Flores_Liguladas_Femeninas")
    mb.material("Mat_CorolaLimbo")

    nu_l, nv_l = 12, 6
    c_lig_tube = (0.72, 0.49, 0.08)
    c_lig_base = (0.86, 0.62, 0.10)
    c_lig_mid  = (0.94, 0.76, 0.18)
    c_lig_tip  = (0.96, 0.82, 0.28)
    c_lig_back = (0.82, 0.65, 0.16)

    for sp in ray_specs:
        ang = sp["ang"]
        ca, sa = math.cos(ang), math.sin(ang)
        tx, tz = -sa, ca
        tr = sp["top_r"]
        ty = sp["top_y"]
        l_len = sp["len"]
        w_max = sp["w"]

        # Tubo corolino basal corto (2.2 mm)
        t_pts = [
            (tr * ca, ty - 0.15, tr * sa),
            ((tr + 0.65) * ca, ty + 0.95, (tr + 0.65) * sa),
            ((tr + 1.35) * ca, ty + 1.90, (tr + 1.35) * sa),
        ]
        mb.add_tube(t_pts, [0.46, 0.52, 0.56], [c_lig_tube, c_lig_base, c_lig_base], radial_segs=5)

        # Estilo bifido exserto en la garganta de la flor ligulada femenina
        st_base = ((tr + 1.15) * ca, ty + 1.85, (tr + 1.15) * sa)
        st_mid  = ((tr + 1.45) * ca, ty + 3.05, (tr + 1.45) * sa)
        for side in (-1.0, 1.0):
            st_tip = (
                (tr + 1.85) * ca + (side * 0.52) * tx,
                ty + 3.55,
                (tr + 1.85) * sa + (side * 0.52) * tz,
            )
            mb.add_tube(
                [st_base, st_mid, st_tip],
                [0.14, 0.11, 0.06],
                [(0.86, 0.62, 0.12), (0.94, 0.78, 0.20), (0.96, 0.84, 0.26)],
                radial_segs=4,
                cap_end=True,
            )

        # Lamina linear-oblonga estrecha con 2 nervios suaves y apice minuciosamente tridentado
        r_start = tr + 1.25
        y_start = ty + 1.80
        top_grid, bot_grid = [], []

        for i in range(nu_l + 1):
            u = i / nu_l
            # Perfil linear-oblongo estrecho (nunca triangulo ancho de girasol)
            if u < 0.15:
                w_prof = 0.42 + 0.58 * math.sin((math.pi * 0.5) * (u / 0.15))
            elif u < 0.78:
                w_prof = 1.0 - 0.14 * ((u - 0.15) / 0.63)
            else:
                t_tip = (u - 0.78) / 0.22
                w_prof = 0.86 * (1.0 - 0.62 * (t_tip ** 1.65))
            w_loc = (w_max * 0.5) * max(0.12, w_prof)

            r_base_u = r_start + l_len * (u ** 0.96)
            y_base_u = (
                y_start
                + sp["pitch"] * l_len * u
                + 1.65 * math.sin(math.pi * (u ** 0.82))
                - sp["droop"] * (u ** 2.25)
            )

            row_t, row_b = [], []
            for j in range(nv_l + 1):
                v = (j / nv_l) - 0.5
                av = abs(v)
                lat = v * 2.0 * w_loc

                # Muescas tridentadas diminutas en el apice (u > 0.88)
                tooth_ext = 0.0
                if u > 0.85:
                    tu = _ss(0.85, 1.0, u)
                    # 3 dientes finos: central (v=0) y dos laterales (v=+/-0.35)
                    teeth = 0.55 * math.cos(v * 2.0 * math.pi * 2.0)
                    tooth_ext = tu * 0.55 * (0.5 + 0.5 * teeth)

                # Concavidad longitudinal + dos nervios suaves + ligera torsion organica
                vein = 0.16 * math.cos(v * 3.0 * math.pi) * math.sin(math.pi * u)
                cup = 0.42 * (v * v) * math.sin(math.pi * (u ** 0.75))
                twist_y = v * sp["twist"] * 2.6 * u
                thick = 0.16 * math.sin(math.pi * (u ** 0.75)) + 0.04

                px = (r_base_u + tooth_ext) * ca + lat * tx
                pz = (r_base_u + tooth_ext) * sa + lat * tz
                py_t = y_base_u + cup + vein + twist_y
                py_b = py_t - thick

                # Gradiente ocre-dorado calido (no neon) con leve variacion por nervio y serie
                tier_ao = 0.90 + 0.05 * sp["tier"]
                vein_sh = 0.95 + 0.06 * math.cos(v * 3.0 * math.pi)
                if u < 0.35:
                    ctop = _lerp_col(c_lig_base, c_lig_mid, u / 0.35)
                else:
                    ctop = _lerp_col(c_lig_mid, c_lig_tip, (u - 0.35) / 0.65)
                ctop = _shade(ctop, tier_ao * vein_sh * (0.94 + 0.06 * (1.0 - av)))
                cbot = _shade(_lerp_col(c_lig_back, c_lig_mid, u * 0.6), tier_ao * 0.92)

                row_t.append(mb.v(px, py_t, pz, *ctop))
                row_b.append(mb.v(px, py_b, pz, *cbot))
            top_grid.append(row_t)
            bot_grid.append(row_b)

        for i in range(nu_l):
            for j in range(nv_l):
                mb.quad(top_grid[i][j], top_grid[i][j + 1], top_grid[i + 1][j], top_grid[i + 1][j + 1])
                mb.quad(bot_grid[i][j + 1], bot_grid[i][j], bot_grid[i + 1][j + 1], bot_grid[i + 1][j])

    # =========================================================================
    # 7. PÁLEAS RECEPTACULARES ESCARIOSAS Y 8. FLÓSCULOS DEL DISCO (FIBONACCI)
    # =========================================================================
    n_flosculos = 235
    golden_angle = math.radians(137.507764)
    r_disc_fl = r_disco * 0.835
    c_vogel = r_disc_fl / math.sqrt(n_flosculos)

    disc_coords = []
    for n in range(1, n_flosculos + 1):
        theta = n * golden_angle
        r_n = c_vogel * math.sqrt(n)
        frac = r_n / r_disc_fl
        y_n = dome_y(r_n) - 0.15
        disc_coords.append((n, theta, r_n, frac, y_n))

    # --- GRUPO 7: PÁLEAS RECEPTACULARES ESCARIOSAS NAVICULARES ---
    mb.group("Paleas_Receptaculares")
    mb.material("Mat_CorolaGarganta")

    for n, theta, r_n, frac, y_n in disc_coords:
        if frac < 0.24:
            continue
        ca, sa = math.cos(theta), math.sin(theta)
        tx, tz = -sa, ca
        # Cada palea abraza el flosculo desde su lado externo
        r_p = r_n + 0.42
        h_pal = 5.4 + 1.6 * frac
        w_pal = 0.78

        p_grid = []
        for i in range(4):
            u = i / 3.0
            w_u = w_pal * (0.85 if u < 0.7 else (1.0 - (u - 0.7) / 0.35))
            y_u = y_n + h_pal * u
            r_u = r_p + 0.28 * math.sin(math.pi * u) + 0.25 * frac * u
            row = []
            for j in range(3):
                v = (j / 2.0) - 0.5
                lat = v * 2.0 * w_u
                # Forma navicular concava abrazando hacia adentro
                nav = -0.35 * (1.0 - 4.0 * v * v)
                px = (r_u + nav) * ca + lat * tx
                pz = (r_u + nav) * sa + lat * tz
                if u < 0.72:
                    col_p = _lerp_col((0.84, 0.80, 0.67), (0.76, 0.69, 0.52), u)
                else:
                    col_p = (0.56, 0.44, 0.26)  # Apice pardo-pubescente escarioso
                row.append(mb.v(px, y_u, pz, *col_p))
            p_grid.append(row)

        for i in range(3):
            for j in range(2):
                mb.quad(p_grid[i][j], p_grid[i][j + 1], p_grid[i + 1][j], p_grid[i + 1][j + 1])

    # --- GRUPO 8: FLORES TUBULOSAS DEL DISCO (FUNCIONALMENTE MASCULINAS) ---
    mb.group("Flores_Tubulosas_Disco")
    mb.material("Mat_Antera")

    rng_d = random.Random(405)
    c_ov_sterile = (0.76, 0.73, 0.60)
    c_bud_dark   = (0.48, 0.30, 0.08)
    c_bud_gold   = (0.86, 0.66, 0.14)
    c_cor_base   = (0.82, 0.58, 0.10)
    c_cor_lobe   = (0.94, 0.76, 0.16)
    c_anther_dk  = (0.22, 0.12, 0.06)
    c_anther_md  = (0.34, 0.20, 0.10)
    c_pollen     = (0.97, 0.81, 0.18)

    for n, theta, r_n, frac, y_n in disc_coords:
        ca, sa = math.cos(theta), math.sin(theta)
        tilt_f = 0.26 * (frac ** 1.35)
        fx_r, fx_y = math.sin(tilt_f), math.cos(tilt_f)

        def fl_pt(h):
            rr = r_n + fx_r * h
            return (rr * ca, y_n + fx_y * h, rr * sa)

        if frac < 0.36:
            # ZONA CENTRAL: botones cerrados compactos en espiral de Fibonacci
            h_bud = 3.8 + 1.4 * (frac / 0.36)
            bud_pts = [fl_pt(0.0), fl_pt(h_bud * 0.48), fl_pt(h_bud * 0.84), fl_pt(h_bud)]
            bud_r = [0.24, 0.44, 0.54, 0.18]
            c_top_b = _lerp_col((0.68, 0.48, 0.12), c_bud_gold, frac / 0.36)
            bud_c = [c_ov_sterile, c_bud_dark, c_top_b, _shade(c_top_b, 1.06)]
            mb.add_tube(bud_pts, bud_r, bud_c, radial_segs=5, cap_end=True)
        else:
            # ANILLO INTERMEDIO Y EXTERNO: flores tubulosas 5-lobadas con sinantero pardo y polen
            mat = _ss(0.36, 0.85, frac)
            h_ov = 1.85  # Ovario basal rudimentario esteril (delgado, contraste en Corte Sagital)
            h_cor = 4.1 + 0.7 * mat
            h_tot_cor = h_ov + h_cor

            # 1. Ovario rudimentario esteril + tubo corolino infundibuliforme 5-lobado
            cor_pts = [
                fl_pt(0.0),
                fl_pt(h_ov),
                fl_pt(h_ov + h_cor * 0.45),
                fl_pt(h_ov + h_cor * 0.85),
                fl_pt(h_tot_cor),
            ]
            cor_r = [0.22, 0.25, 0.38, 0.56, 0.68]
            cor_c = [c_ov_sterile, c_ov_sterile, c_cor_base, c_cor_lobe, c_cor_lobe]
            mb.add_tube(cor_pts, cor_r, cor_c, radial_segs=5, cap_start=False, cap_end=False)

            # 2. 5 lobulos agudos desplegados en el borde de la corola (en flores en antesis)
            top_c = fl_pt(h_tot_cor)
            for lb in range(5):
                la = theta + lb * (2.0 * math.pi / 5.0)
                lca, lsa = math.cos(la), math.sin(la)
                p_b1 = mb.v(top_c[0] + 0.50 * lca - 0.18 * lsa, top_c[1] - 0.10, top_c[2] + 0.50 * lsa + 0.18 * lca, *c_cor_lobe)
                p_b2 = mb.v(top_c[0] + 0.50 * lca + 0.18 * lsa, top_c[1] - 0.10, top_c[2] + 0.50 * lsa - 0.18 * lca, *c_cor_lobe)
                p_tip = mb.v(top_c[0] + 0.92 * lca, top_c[1] + 0.45, top_c[2] + 0.92 * lsa, *_shade(c_cor_lobe, 1.05))
                mb.f(p_b1, p_b2, p_tip)

            # 3. Tubo anteral singenesico pardo-negruzco exserto (rasgo diagnostico de Espeletia)
            h_ant_ext = 1.45 + 0.55 * mat
            ant_pts = [
                fl_pt(h_tot_cor - 0.55),
                fl_pt(h_tot_cor + h_ant_ext * 0.55),
                fl_pt(h_tot_cor + h_ant_ext),
            ]
            ant_r = [0.34, 0.32, 0.28]
            ant_c = [c_anther_md, c_anther_dk, c_anther_dk]
            mb.add_tube(ant_pts, ant_r, ant_c, radial_segs=5, cap_end=True)

            # 4. Presentacion secundaria de polen (corona amarillo oro en el apice del estilo indiviso)
            if rng_d.random() < (0.85 if frac < 0.82 else 0.55):
                pol_pts = [
                    fl_pt(h_tot_cor + h_ant_ext - 0.10),
                    fl_pt(h_tot_cor + h_ant_ext + 0.38),
                    fl_pt(h_tot_cor + h_ant_ext + 0.72),
                ]
                mb.add_tube(pol_pts, [0.22, 0.32, 0.12], [c_pollen, c_pollen, _shade(c_pollen, 1.05)], radial_segs=5, cap_end=True)

    return mb.build_obj()
