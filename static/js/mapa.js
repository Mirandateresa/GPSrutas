// static/js/mapa.js - VERSIÓN COMPLETA QUE FUNCIONA
// Mapa con Leaflet y OpenStreetMap

const TILE_LAYER = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
const TILE_ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';
const NOMINATIM_URL = 'https://nominatim.openstreetmap.org';

window.GPSMapa = {
    dibujarRuta: dibujarRuta,
    limpiarRuta: limpiarRuta,
    enfocarPosicion: enfocarPosicion,
    geocodificar: geocodificar,
};

let mapa = null;
let marcadorOrigen = null;
let marcadorDestino = null;
let marcadoresPeajes = [];
let lineaRuta = null;

function iniciarMapa() {
    console.log('📌 Iniciando mapa...');
    
    var contenedor = document.getElementById('mapa');
    if (!contenedor) {
        console.error('❌ No se encontró el contenedor del mapa');
        setTimeout(iniciarMapa, 500);
        return;
    }

    var panel = document.getElementById('panelControl');
    if (panel) {
        panel.style.display = 'block';
        panel.classList.remove('closed');
    }

    var botonAbrir = document.getElementById('botonAbrirPanel');
    if (botonAbrir) {
        botonAbrir.classList.add('hidden');
    }

    if (!mapa) {
        try {
            mapa = L.map('mapa', {
                center: [23.6345, -102.5528],
                zoom: 5,
                zoomControl: true,
                attributionControl: true,
            });

            L.tileLayer(TILE_LAYER, {
                attribution: TILE_ATTRIBUTION,
                maxZoom: 19,
            }).addTo(mapa);

            mapa.on('click', function(e) {
                if (window.GPS.modoColocarZona) {
                    seleccionarPuntoZona(e.latlng);
                    return;
                }
                seleccionarPuntoRuta(e.latlng);
            });

            setTimeout(function() {
                if (mapa) {
                    mapa.invalidateSize();
                }
            }, 200);

        } catch (error) {
            console.error('❌ Error al crear el mapa:', error);
            mostrarMensaje('Error al inicializar el mapa: ' + error.message, 'error');
            return;
        }
    }

    configurarAutocompletado('entradaOrigen', 'origen');
    configurarAutocompletado('entradaDestino', 'destino');

    if (typeof cargarZonas === 'function') {
        cargarZonas();
    }

    mostrarMensaje('Mapa listo. Escribe una dirección o selecciona puntos en el mapa.', 'success');
    
    setTimeout(function() {
        if (mapa) {
            mapa.invalidateSize();
        }
    }, 500);
}

// 🔑 EXPONER LA FUNCIÓN GLOBALMENTE
window.iniciarMapa = iniciarMapa;
console.log('✅ mapa.js cargado - window.iniciarMapa disponible');

// ============================================================
// GEOCODIFICACIÓN
// ============================================================

async function geocodificar(direccion) {
    try {
        var response = await fetch(
            NOMINATIM_URL + '/search?q=' + encodeURIComponent(direccion) + '&format=json&limit=1&countrycodes=mx&accept-language=es',
            { headers: { 'User-Agent': 'GPS-RutasSeguras/1.0' } }
        );
        var data = await response.json();
        if (data && data.length > 0) {
            return {
                lat: parseFloat(data[0].lat),
                lng: parseFloat(data[0].lon),
                display_name: data[0].display_name,
            };
        }
        return null;
    } catch (error) {
        console.error('Error en geocodificación:', error);
        return null;
    }
}

async function geocodificarReversa(lat, lng) {
    try {
        var response = await fetch(
            NOMINATIM_URL + '/reverse?lat=' + lat + '&lon=' + lng + '&format=json&accept-language=es',
            { headers: { 'User-Agent': 'GPS-RutasSeguras/1.0' } }
        );
        var data = await response.json();
        if (data && data.display_name) {
            return data.display_name;
        }
        return lat.toFixed(6) + ', ' + lng.toFixed(6);
    } catch (error) {
        console.error('Error en geocodificación inversa:', error);
        return lat.toFixed(6) + ', ' + lng.toFixed(6);
    }
}

// ============================================================
// AUTOCOMPLETADO
// ============================================================

function configurarAutocompletado(idInput, tipo) {
    var input = document.getElementById(idInput);
    if (!input) return;

    var timeoutId = null;
    var container = document.createElement('div');
    container.className = 'autocomplete-suggestions';
    container.style.cssText = 'position:absolute;background:white;border:2px solid #E8D5C4;border-radius:12px;max-height:200px;overflow-y:auto;z-index:9999;display:none;width:100%;box-shadow:0 18px 45px rgba(92,64,51,0.15);';
    
    if (input.parentNode.style.position !== 'relative') {
        input.parentNode.style.position = 'relative';
    }
    input.parentNode.appendChild(container);

    input.addEventListener('input', function() {
        var query = this.value.trim();
        if (query.length < 3) {
            container.style.display = 'none';
            return;
        }

        clearTimeout(timeoutId);
        timeoutId = setTimeout(async function() {
            try {
                var response = await fetch(
                    NOMINATIM_URL + '/search?q=' + encodeURIComponent(query) + '&format=json&limit=5&countrycodes=mx&accept-language=es',
                    { headers: { 'User-Agent': 'GPS-RutasSeguras/1.0' } }
                );
                var data = await response.json();
                
                container.innerHTML = '';
                if (data && data.length > 0) {
                    data.forEach(function(item) {
                        var div = document.createElement('div');
                        div.className = 'autocomplete-item';
                        div.style.cssText = 'padding:10px 14px;cursor:pointer;border-bottom:1px solid #FAF5EF;font-size:0.9rem;color:#5C4033;transition:background 0.2s ease;';
                        div.textContent = item.display_name;
                        div.addEventListener('click', function() {
                            input.value = item.display_name;
                            container.style.display = 'none';
                            
                            var pos = {
                                lat: parseFloat(item.lat),
                                lng: parseFloat(item.lon),
                            };
                            
                            if (tipo === 'origen') {
                                window.GPS.posicionOrigen = pos;
                            } else {
                                window.GPS.posicionDestino = pos;
                            }
                            enfocarPosicion(pos, 14);
                            dibujarMarcadoresSeleccion();
                            input.blur();
                        });
                        div.addEventListener('mouseenter', function() {
                            this.style.background = '#FAF5EF';
                        });
                        div.addEventListener('mouseleave', function() {
                            this.style.background = 'transparent';
                        });
                        container.appendChild(div);
                    });
                    container.style.display = 'block';
                } else {
                    container.style.display = 'none';
                }
            } catch (error) {
                console.error('Error en autocompletado:', error);
                container.style.display = 'none';
            }
        }, 300);
    });

    input.addEventListener('blur', function() {
        setTimeout(function() {
            container.style.display = 'none';
        }, 200);
    });

    input.addEventListener('focus', function() {
        if (this.value.trim().length >= 3) {
            this.dispatchEvent(new Event('input'));
        }
    });
}

// ============================================================
// SELECCIÓN DE PUNTOS
// ============================================================

async function seleccionarPuntoRuta(latlng) {
    var posicion = {
        lat: latlng.lat,
        lng: latlng.lng,
    };
    
    var origenVacio = !document.getElementById('entradaOrigen').value.trim();
    var destinoVacio = !document.getElementById('entradaDestino').value.trim();
    var objetivo = origenVacio ? 'origen' : (destinoVacio ? 'destino' : 'destino');

    try {
        var direccion = await geocodificarReversa(posicion.lat, posicion.lng);

        if (objetivo === 'origen') {
            document.getElementById('entradaOrigen').value = direccion;
            window.GPS.posicionOrigen = posicion;
            mostrarMensaje('Origen seleccionado. Ahora elige el destino.');
        } else {
            document.getElementById('entradaDestino').value = direccion;
            window.GPS.posicionDestino = posicion;
            mostrarMensaje('Destino seleccionado. Ya puedes calcular la ruta.');
        }
        dibujarMarcadoresSeleccion();
    } catch (error) {
        mostrarMensaje('No fue posible obtener la dirección del punto seleccionado.', 'error');
    }
}

function dibujarMarcadoresSeleccion() {
    if (!mapa) return;

    if (marcadorOrigen) {
        mapa.removeLayer(marcadorOrigen);
        marcadorOrigen = null;
    }
    if (marcadorDestino) {
        mapa.removeLayer(marcadorDestino);
        marcadorDestino = null;
    }

    var iconoOrigen = L.divIcon({
        className: 'custom-marker',
        html: '<div style="background:#2563eb;color:white;width:30px;height:30px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:bold;font-size:14px;border:3px solid white;box-shadow:0 2px 8px rgba(0,0,0,0.3);">A</div>',
        iconSize: [30, 30],
        iconAnchor: [15, 15],
    });

    var iconoDestino = L.divIcon({
        className: 'custom-marker',
        html: '<div style="background:#c62828;color:white;width:30px;height:30px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:bold;font-size:14px;border:3px solid white;box-shadow:0 2px 8px rgba(0,0,0,0.3);">B</div>',
        iconSize: [30, 30],
        iconAnchor: [15, 15],
    });

    if (window.GPS.posicionOrigen) {
        marcadorOrigen = L.marker([window.GPS.posicionOrigen.lat, window.GPS.posicionOrigen.lng], {
            icon: iconoOrigen,
            title: 'Origen',
        }).addTo(mapa);
    }

    if (window.GPS.posicionDestino) {
        marcadorDestino = L.marker([window.GPS.posicionDestino.lat, window.GPS.posicionDestino.lng], {
            icon: iconoDestino,
            title: 'Destino',
        }).addTo(mapa);
    }
}

function enfocarPosicion(posicion, zoom) {
    if (!mapa) return;
    mapa.setView([posicion.lat, posicion.lng], zoom || 15);
}

// ============================================================
// DIBUJAR RUTA
// ============================================================

function dibujarRuta(datos) {
    console.log('📌 dibujarRuta llamado con datos:', datos);
    
    if (!datos) {
        console.error('❌ No hay datos para dibujar');
        return;
    }

    limpiarRuta();

    var trayecto = (datos.coordinates || [])
        .map(function(punto) { return [Number(punto.lat), Number(punto.lng)]; })
        .filter(function(punto) { return Number.isFinite(punto[0]) && Number.isFinite(punto[1]); });

    if (trayecto.length < 2) {
        mostrarMensaje('La ruta no contiene coordenadas suficientes para dibujarla.', 'error');
        return;
    }

    if (!mapa) {
        console.error('❌ El mapa no está inicializado');
        return;
    }

    lineaRuta = L.polyline(trayecto, {
        color: '#2563eb',
        weight: 6,
        opacity: 0.95,
        smoothFactor: 1,
    }).addTo(mapa);

    var bounds = L.latLngBounds(trayecto);
    mapa.fitBounds(bounds, { padding: [50, 50] });

    window.GPS.posicionOrigen = {
        lat: Number(datos.origin.lat),
        lng: Number(datos.origin.lng),
    };
    window.GPS.posicionDestino = {
        lat: Number(datos.destination.lat),
        lng: Number(datos.destination.lng),
    };
    dibujarMarcadoresSeleccion();

    var peajes = datos.tolls || [];
    console.log('📌 Peajes a dibujar:', peajes.length);
    dibujarMarcadoresPeajes(peajes);

    if (datos.has_red_zones && !window.GPS.zonasVisibles) {
        mostrarZonas();
    }
}

// ============================================================
// 🟢 MARCADORES DE PEAJES - VERDES CON $
// ============================================================

function dibujarMarcadoresPeajes(peajes) {
    console.log('📌 dibujarMarcadoresPeajes llamado con:', peajes);
    
    if (!mapa) return;
    
    marcadoresPeajes.forEach(function(m) { if (m && mapa.hasLayer(m)) mapa.removeLayer(m); });
    marcadoresPeajes = [];

    if (!peajes || peajes.length === 0) {
        console.log('📌 No hay peajes para dibujar');
        return;
    }

    var iconoPeaje = L.divIcon({
        className: 'custom-marker',
        html: '<div style="background:#16a34a;color:white;width:32px;height:32px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:bold;font-size:16px;border:3px solid white;box-shadow:0 2px 10px rgba(22,163,74,0.5);">$</div>',
        iconSize: [32, 32],
        iconAnchor: [16, 16],
    });

    peajes.forEach(function(peaje) {
        var lat = Number(peaje.lat);
        var lng = Number(peaje.lng);
        
        if (!Number.isFinite(lat) || !Number.isFinite(lng) || (lat === 0 && lng === 0)) {
            console.log('⚠️ Peaje sin coordenadas:', peaje.name);
            return;
        }

        console.log('📍 Agregando peaje:', peaje.name, 'en', lat, lng);

        var marcador = L.marker([lat, lng], {
            icon: iconoPeaje,
            title: peaje.name || 'Peaje',
        }).addTo(mapa);

        var nombreLimpio = peaje.name || 'Peaje';
        if (nombreLimpio.includes('(Cuota)')) nombreLimpio = nombreLimpio.replace('(Cuota)', '').trim();
        if (nombreLimpio.startsWith('Autopista de Peaje')) nombreLimpio = nombreLimpio.replace('Autopista de Peaje', '').trim();
        if (nombreLimpio.includes(' - ')) {
            var partes = nombreLimpio.split(' - ');
            nombreLimpio = partes[0] + ' - ' + partes[partes.length - 1];
        }

        var contenido = '<div style="min-width:120px;max-width:220px;font-family:Quicksand,sans-serif;padding:2px 0;">';
        contenido += '<strong style="color:#16a34a;font-size:0.95rem;">🟢 ' + escaparHtml(nombreLimpio) + '</strong>';
        if (peaje.price) {
            contenido += '<br><span style="color:#16a34a;font-weight:bold;font-size:0.85rem;">$' + Number(peaje.price).toFixed(2) + ' MXN</span>';
        }
        contenido += '</div>';
        marcador.bindPopup(contenido);
        marcadoresPeajes.push(marcador);
    });

    console.log('✅ Total marcadores de peajes:', marcadoresPeajes.length);
}

// ============================================================
// LIMPIAR RUTA
// ============================================================

function limpiarRuta() {
    if (!mapa) return;
    
    if (lineaRuta) {
        mapa.removeLayer(lineaRuta);
        lineaRuta = null;
    }
    
    marcadoresPeajes.forEach(function(m) {
        if (m && mapa.hasLayer(m)) {
            mapa.removeLayer(m);
        }
    });
    marcadoresPeajes = [];
}

// ============================================================
// ZONAS ROJAS
// ============================================================

var circulosZonas = [];
var marcadoresZonas = [];

async function cargarZonas() {
    try {
        var respuesta = await solicitarJson('/api/zones');
        window.GPS.zonas = respuesta.data || [];
        if (window.GPS.zonasVisibles) {
            dibujarZonas();
        }
    } catch (error) {
        mostrarMensaje('No fue posible cargar las zonas: ' + error.message, 'error');
    }
}

function alternarZonas() {
    window.GPS.zonasVisibles ? ocultarZonas() : mostrarZonas();
}

function mostrarZonas() {
    window.GPS.zonasVisibles = true;
    var btn = document.getElementById('botonAlternarZonas');
    btn.classList.add('active');
    btn.textContent = 'Ocultar zonas rojas';
    dibujarZonas();
}

function ocultarZonas() {
    window.GPS.zonasVisibles = false;
    var btn = document.getElementById('botonAlternarZonas');
    btn.classList.remove('active');
    btn.textContent = 'Mostrar zonas rojas';
    limpiarCapasZonas();
}

function dibujarZonas() {
    if (!mapa) return;
    limpiarCapasZonas();

    window.GPS.zonas.forEach(function(zona) {
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
        }).addTo(mapa);

        var icono = L.divIcon({
            className: 'custom-marker',
            html: '<div style="background:#c62828;color:white;width:24px;height:24px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:bold;font-size:12px;border:2px solid white;box-shadow:0 2px 8px rgba(0,0,0,0.3);">!</div>',
            iconSize: [24, 24],
            iconAnchor: [12, 12],
        });

        var marcador = L.marker([lat, lng], {
            icon: icono,
            title: zona.name,
        }).addTo(mapa);

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
    circulosZonas.forEach(function(c) { if (mapa && mapa.hasLayer(c)) mapa.removeLayer(c); });
    marcadoresZonas.forEach(function(m) { if (mapa && mapa.hasLayer(m)) mapa.removeLayer(m); });
    circulosZonas = [];
    marcadoresZonas = [];
}

function iniciarColocacionZona() {
    if (!mapa) {
        mostrarMensaje('El mapa todavía no está listo.', 'error');
        return;
    }
    window.GPS.modoColocarZona = true;
    mostrarMensaje('Haz clic en el mapa para colocar el centro de la nueva zona roja.');
}

async function seleccionarPuntoZona(latlng) {
    window.GPS.modoColocarZona = false;
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
            NOMINATIM_URL + '/reverse?lat=' + posicion.lat + '&lon=' + posicion.lng + '&format=json&accept-language=es',
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
    window.GPS.modoColocarZona = false;
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
        if (!window.GPS.zonasVisibles) {
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

console.log('✅ mapa.js completamente cargado');