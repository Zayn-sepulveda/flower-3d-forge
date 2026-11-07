import re

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

tarjetas = """
            <!-- Ficha: Passiflora vitifolia (Colecta 03) -->
            <div class="card" data-search="passiflora vitifolia passifloraceae buenaventura bajo calima valle colombia corona roja">
                <img class="card-img" src="images/passiflora_vitifolia.jpg" alt="Passiflora vitifolia">
                <div class="card-body">
                    <span class="card-tag">Passifloraceae</span>
                    <h2 class="card-title">Passiflora vitifolia</h2>
                    <div class="card-meta">
                        <div><strong>Localidad:</strong> Bajo Calima, Buenaventura, Valle del Cauca</div>
                        <div><strong>Muestra:</strong> COL-VAL-003</div>
                        <div><strong>Inflorescencia:</strong> Flor escarlata con androginóforo exerto</div>
                    </div>
                    <a href="models/passiflora_vitifolia.html" class="btn-view">Explorar en 3D ➔</a>
                </div>
            </div>

            <!-- Ficha: Passiflora incarnata (Colecta 04) -->
            <div class="card" data-search="passiflora incarnata passifloraceae palmira valle colombia corona purpura lavanda">
                <img class="card-img" src="images/passiflora_incarnata.jpg" alt="Passiflora incarnata">
                <div class="card-body">
                    <span class="card-tag">Passifloraceae</span>
                    <h2 class="card-title">Passiflora incarnata</h2>
                    <div class="card-meta">
                        <div><strong>Localidad:</strong> Palmira, Valle del Cauca</div>
                        <div><strong>Muestra:</strong> COL-VAL-004</div>
                        <div><strong>Inflorescencia:</strong> Corona bandeada púrpura con filamentos rizados</div>
                    </div>
                    <a href="models/passiflora_incarnata.html" class="btn-view">Explorar en 3D ➔</a>
                </div>
            </div>
"""

if "Passiflora vitifolia" not in html:
    # Inserta las nuevas tarjetas justo antes de la Crotalaria
    html = html.replace('<!-- Ficha: Crotalaria sp -->', tarjetas + '\n            <!-- Ficha: Crotalaria sp -->')
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("✅ Tarjetas inyectadas perfectamente en index.html sin romper el código.")
else:
    print("⚠️ Las tarjetas ya estaban en el archivo.")
