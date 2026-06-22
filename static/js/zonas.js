window.GPSZonas = {
    cargar: cargarZonas,
    mostrar: mostrarZonas,
    ocultar: ocultarZonas,
    seleccionarPunto: seleccionarPuntoZona,
};

var circulosZonas = [];
var marcadoresZonas = [];

// Asegurar que GPS esté definido
if (typeof GPS === 'undefined') {
    window.GPS = {
        zonas: [],
        zonasVisibles: false,
        modoColocarZona: false,
    };
}

async function cargarZonas() {
    try {
        var respuesta = await solicitarJson("/api/zones");
        GPS.zonas = respuesta.data || [];
        if (GPS.zonasVisibles) {
            dibujarZonas();
        }
    } catch (error) {
        mostrarMensaje('No fue posible cargar las zonas: ' + error.message, 'error');
    }
}

function alternarZonas() {
    GPS.zonasVisibles ? ocultarZonas() : mostrarZonas();
}

function mostrarZonas() {
    GPS.zonasVisibles = true;
    var btn = document.getElementById('botonAlternarZonas');
    btn.classList.add('active');
    btn.textContent = 'Ocultar zonas rojas';
    dibujarZonas();
}

function ocultarZonas() {
    GPS.zonasVisibles = false;
    var btn = document.getElementById('botonAlternarZonas');
    btn.classList.remove('active');
    btn.textContent = 'Mostrar zonas rojas';
    limpiarCapasZonas();
}

function dibujarZonas() {
    if (!window.mapa) return;
    limpiarCapasZonas();

    GPS.zonas.forEach(function(zona) {
        var lat = Number(zona.lat);
        var lng = Number(zona.lng);
        var radio = Number(zona.radius_m);
        if (!Number.isFinite(lat) || !Number.isFinite(lng)) return;

        var circulo = L.circle([lat, lng], {
            radius: Number.isFinite(radio) ? radio : 500,
            color: '#b91c1c',
            fillColor: '#dc2626',
            fillOpacity: 0.16,
            weight: 2,
            opacity: 0.8,
        }).addTo(window.mapa);

        var icono = L.divIcon({
            className: 'custom-marker',
            html: '<div style="background:#c62828;color:white;width:24px;height:24px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:bold;font-size:12px;border:2px solid white;box-shadow:0 2px 8px rgba(0,0,0,0.3);">!</div>',
            iconSize: [24, 24],
            iconAnchor: [12, 12],
        });

        var marcador = L.marker([lat, lng], {
            icon: icono,
            title: zona.name,
        }).addTo(window.mapa);

        marcador.on('click', function() { abrirDialogoZona(zona); });
        circulo.on('click', function() { abrirDialogoZona(zona); });

        marcador.bindPopup(
            '<strong>' + escaparHtml(zona.name) + '</strong><br>' +
            '<small>' + escaparHtml(zona.municipality || '') + (zona.state ? ', ' + escaparHtml(zona.state) : '') + '</small>' +
            (zona.risks && zona.risks.length ? '<br><span style="color:#c62828;">⚠️ ' + escaparHtml(zona.risks.join(', ')) + '</span>' : '')
        );

        circulosZonas.push(circulo);
        marcadoresZonas.push(marcador);
    });
}

function limpiarCapasZonas() {
    circulosZonas.forEach(function(c) { window.mapa.removeLayer(c); });
    marcadoresZonas.forEach(function(m) { window.mapa.removeLayer(m); });
    circulosZonas = [];
    marcadoresZonas = [];
}

function iniciarColocacionZona() {
    if (!window.mapa) {
        mostrarMensaje('El mapa todavía no está listo.', 'error');
        return;
    }
    GPS.modoColocarZona = true;
    mostrarMensaje('Haz clic en el mapa para colocar el centro de la nueva zona roja.');
}

async function seleccionarPuntoZona(latlng) {
    GPS.modoColocarZona = false;
    var posicion = {
        lat: latlng.lat,
        lng: latlng.lng,
    };
    abrirDialogoZona({
        id: '',
        name: '',
        municipality: '',
        state: '',
        risks: [],
        description: '',
        lat: posicion.lat,
        lng: posicion.lng,
        radius_m: 500,
    });
    await completarDireccionZona(posicion);
}

async function completarDireccionZona(posicion) {
    document.getElementById('estadoFormularioZona').textContent = 'Consultando la dirección del punto...';

    try {
        var response = await fetch(
            'https://nominatim.openstreetmap.org/reverse?lat=' + posicion.lat + '&lon=' + posicion.lng + '&format=json&accept-language=es',
            { headers: { 'User-Agent': 'GPS-RutasSeguras/1.0' } }
        );
        var data = await response.json();
        
        if (data && data.address) {
            var addr = data.address;
            var nombreZona = document.getElementById('nombreZona');
            if (!nombreZona.value) {
                nombreZona.value = addr.road || addr.suburb || addr.city || '';
            }
            document.getElementById('municipioZona').value = addr.city || addr.town || addr.village || '';
            document.getElementById('estadoZona').value = addr.state || '';
            document.getElementById('estadoFormularioZona').textContent = 'Ubicación completada correctamente.';
        } else {
            document.getElementById('estadoFormularioZona').textContent = 'No se pudo obtener la dirección automáticamente.';
        }
    } catch (error) {
        document.getElementById('estadoFormularioZona').textContent = 'Error al obtener la dirección: ' + error.message;
    }
}

function abrirDialogoZona(zona) {
    var editando = Boolean(zona && zona.id);
    document.getElementById('tituloDialogoZona').textContent = editando ? 'Editar zona roja' : 'Nueva zona roja';
    document.getElementById('idZona').value = zona && zona.id ? zona.id : '';
    document.getElementById('nombreZona').value = zona && zona.name ? zona.name : '';
    document.getElementById('municipioZona').value = zona && zona.municipality ? zona.municipality : '';
    document.getElementById('estadoZona').value = zona && zona.state ? zona.state : '';
    document.getElementById('riesgosZona').value = zona && zona.risks ? zona.risks.join(', ') : '';
    document.getElementById('descripcionZona').value = zona && zona.description ? zona.description : '';
    document.getElementById('latitudZona').value = zona && zona.lat ? zona.lat : '';
    document.getElementById('longitudZona').value = zona && zona.lng ? zona.lng : '';
    document.getElementById('radioZona').value = zona && zona.radius_m ? zona.radius_m : 500;
    document.getElementById('estadoFormularioZona').textContent = '';
    document.getElementById('botonEliminarZona').classList.toggle('hidden', !editando);
    document.getElementById('dialogoZona').showModal();
}

function cerrarDialogoZona() {
    GPS.modoColocarZona = false;
    document.getElementById('dialogoZona').close();
}

function obtenerDatosFormularioZona() {
    return {
        name: document.getElementById('nombreZona').value.trim(),
        municipality: document.getElementById('municipioZona').value.trim(),
        state: document.getElementById('estadoZona').value.trim(),
        risks: document.getElementById('riesgosZona').value
            .split(',')
            .map(function(e) { return e.trim(); })
            .filter(Boolean),
        description: document.getElementById('descripcionZona').value.trim(),
        lat: Number(document.getElementById('latitudZona').value),
        lng: Number(document.getElementById('longitudZona').value),
        radius_m: Number(document.getElementById('radioZona').value),
    };
}

async function guardarZona(evento) {
    evento.preventDefault();
    var id = document.getElementById('idZona').value;
    var metodo = id ? 'PUT' : 'POST';
    var url = id ? '/api/zones/' + encodeURIComponent(id) : '/api/zones';
    document.getElementById('estadoFormularioZona').textContent = 'Guardando...';

    try {
        await solicitarJson(url, {
            method: metodo,
            body: JSON.stringify(obtenerDatosFormularioZona()),
        });
        await cargarZonas();
        if (!GPS.zonasVisibles) {
            mostrarZonas();
        } else {
            dibujarZonas();
        }
        cerrarDialogoZona();
        mostrarMensaje('Zona guardada correctamente.', 'success');
    } catch (error) {
        document.getElementById('estadoFormularioZona').textContent = error.message;
    }
}

async function eliminarZona() {
    var id = document.getElementById('idZona').value;
    if (!id || !window.confirm('¿Deseas eliminar esta zona roja?')) {
        return;
    }

    try {
        await solicitarJson('/api/zones/' + encodeURIComponent(id), {
            method: 'DELETE',
        });
        await cargarZonas();
        dibujarZonas();
        cerrarDialogoZona();
        mostrarMensaje('Zona eliminada correctamente.', 'success');
    } catch (error) {
        document.getElementById('estadoFormularioZona').textContent = error.message;
    }
}

document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('botonAlternarZonas').addEventListener('click', alternarZonas);
    document.getElementById('botonAgregarZona').addEventListener('click', iniciarColocacionZona);
    document.getElementById('formularioZona').addEventListener('submit', guardarZona);
    document.getElementById('botonEliminarZona').addEventListener('click', eliminarZona);
    document.getElementById('botonCerrarDialogoZona').addEventListener('click', cerrarDialogoZona);
    document.getElementById('botonCancelarZona').addEventListener('click', cerrarDialogoZona);
});