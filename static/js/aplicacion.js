// ============================================
// CONFIGURACIÓN GLOBAL
// ============================================

window.GPS = {
    mapa: null,
    posicionOrigen: null,
    posicionDestino: null,
    lineaRuta: null,
    marcadoresRuta: [],
    marcadoresPeajes: [],
    zonas: [],
    capasZonas: [],
    zonasVisibles: false,
    modoColocarZona: false,
};

// ============================================
// UTILIDADES
// ============================================

function porId(id) {
    return document.getElementById(id);
}

function escaparHtml(valor) {
    return String(valor ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

function formatearMoneda(valor, codigoMoneda) {
    codigoMoneda = codigoMoneda || "MXN";
    var numero = Number(valor || 0);
    return new Intl.NumberFormat("es-MX", {
        style: "currency",
        currency: codigoMoneda,
        maximumFractionDigits: 2,
    }).format(Number.isFinite(numero) ? numero : 0);
}

function mostrarMensaje(texto, tipo) {
    tipo = tipo || "info";
    var caja = porId("cajaMensaje");
    caja.textContent = texto;
    caja.className = "message " + (tipo === "info" ? "" : tipo);
    caja.style.display = 'block';
}

function ocultarMensaje() {
    var caja = porId("cajaMensaje");
    caja.classList.add("hidden");
    caja.style.display = 'none';
}

function establecerCarga(activo) {
    var boton = porId("botonCalcular");
    boton.disabled = activo;
    boton.textContent = activo ? "Calculando..." : "Calcular ruta";
}

async function solicitarJson(url, opciones) {
    opciones = opciones || {};
    var respuesta = await fetch(url, {
        ...opciones,
        headers: {
            "Content-Type": "application/json",
            ...(opciones.headers || {}),
        },
    });

    var contenido = await respuesta.json().catch(function() {
        return { ok: false, error: "El servidor devolvió una respuesta no válida." };
    });

    if (!respuesta.ok || contenido.ok === false) {
        throw new Error(contenido.error || "Error HTTP " + respuesta.status);
    }
    return contenido;
}

// ============================================
// CALCULAR RUTA
// ============================================

async function calcularRuta() {
    var origen = porId("entradaOrigen").value.trim();
    var destino = porId("entradaDestino").value.trim();
    var rendimiento = Number(porId("entradaRendimiento").value);

    if (!origen || !destino) {
        mostrarMensaje("Escribe un origen y un destino.", "error");
        return;
    }
    if (!Number.isFinite(rendimiento) || rendimiento <= 0 || rendimiento > 100) {
        mostrarMensaje("El rendimiento debe estar entre 0 y 100 km/l.", "error");
        return;
    }

    establecerCarga(true);
    mostrarMensaje("Calculando la ruta y analizando las zonas rojas...");

    try {
        var respuesta = await solicitarJson("/api/route", {
            method: "POST",
            body: JSON.stringify({
                origin: origen,
                destination: destino,
                vehicle_type: porId("selectorVehiculo").value,
                efficiency_km_l: rendimiento,
            }),
        });
        
        console.log("📌 Datos de la ruta recibidos:", respuesta.data);
        console.log("📌 Zonas rojas en la respuesta:", respuesta.data.red_zones);
        
        if (window.GPSMapa && typeof window.GPSMapa.dibujarRuta === 'function') {
            window.GPSMapa.dibujarRuta(respuesta.data);
        } else {
            console.error("GPSMapa.dibujarRuta no está disponible");
        }
        
        mostrarResultado(respuesta.data);
        mostrarMensaje("Ruta calculada correctamente.", "success");
    } catch (error) {
        console.error("Error:", error);
        mostrarMensaje(error.message || "Error al calcular la ruta", "error");
    } finally {
        establecerCarga(false);
    }
}

// ============================================
// MOSTRAR RESULTADOS - CON DURACIÓN EN HORAS
// ============================================

function mostrarResultado(datos) {
    console.log("📌 Mostrando resultado:", datos);
    
    porId("panelResultados").classList.remove("hidden");
    porId("valorDistancia").textContent = Number(datos.distance_km).toFixed(2) + " km";
    
    // 🔥 CONVERTIR MINUTOS A HORAS Y MINUTOS
    var minutosTotales = Math.round(Number(datos.duration_min));
    var horas = Math.floor(minutosTotales / 60);
    var minutos = minutosTotales % 60;
    var textoDuracion = horas + "h " + minutos + "min";
    porId("valorDuracion").textContent = textoDuracion;
    
    porId("valorLitros").textContent = Number(datos.estimated_liters).toFixed(2) + " L";
    porId("valorCostoCombustible").textContent = formatearMoneda(datos.fuel_cost_mxn);
    porId("valorCostoPeajes").textContent = formatearMoneda(
        datos.toll_cost,
        datos.toll_currency || "MXN"
    );
    porId("valorCostoTotal").textContent = formatearMoneda(datos.total_cost_mxn);

    var origen = datos.origin?.address || datos.origin?.query || "Origen";
    var destino = datos.destination?.address || datos.destination?.query || "Destino";
    porId("descripcionRuta").textContent = origen + " → " + destino;
    
    mostrarZonasRojas(datos.red_zones || []);
    mostrarPeajes(datos);
}

// ============================================
// MOSTRAR ZONAS ROJAS - EN CUADRO FLOTANTE (CORREGIDO)
// ============================================

function mostrarZonasRojas(zonas) {
    console.log("📌 Mostrando zonas rojas. Datos recibidos:", zonas);
    console.log("📌 ¿Es un array?", Array.isArray(zonas));
    console.log("📌 Cantidad de zonas:", zonas ? zonas.length : 0);
    
    var bloque = document.getElementById("resultadoZonasRojas");
    var insignia = document.getElementById("insigniaAdvertenciaZona");
    var lista = document.getElementById("listaZonasRojas");
    var cuadroFlotante = document.getElementById("cuadroFlotante");
    
    console.log("📌 Elementos DOM encontrados:", {
        bloque: !!bloque,
        insignia: !!insignia,
        lista: !!lista,
        cuadroFlotante: !!cuadroFlotante
    });
    
    if (!bloque) {
        console.warn("⚠️ resultadoZonasRojas no encontrado en el DOM");
        return;
    }
    if (!lista) {
        console.warn("⚠️ listaZonasRojas no encontrado en el DOM");
        return;
    }
    
    lista.innerHTML = "";

    if (!zonas || zonas.length === 0) {
        console.log("📌 No hay zonas rojas para mostrar");
        bloque.classList.add("hidden");
        if (insignia) insignia.classList.add("hidden");
        
        // Verificar si hay peajes para mostrar
        var peajesBlock = document.getElementById("resultadoPeajes");
        var peajesList = document.getElementById("listaPeajes");
        if (peajesBlock && peajesList && peajesList.children.length === 0) {
            if (cuadroFlotante) cuadroFlotante.classList.add("hidden");
        }
        return;
    }

    console.log("✅ Mostrando", zonas.length, "zonas rojas");
    bloque.classList.remove("hidden");
    if (insignia) insignia.classList.remove("hidden");
    if (cuadroFlotante) cuadroFlotante.classList.remove("hidden");

    zonas.forEach(function(zona, index) {
        console.log("   Zona #" + (index + 1) + ":", zona.name);
        var elemento = document.createElement("li");
        var lugar = [zona.municipality, zona.state].filter(Boolean).join(", ");
        elemento.textContent = zona.name + (lugar ? " — " + lugar : "");
        lista.appendChild(elemento);
    });
}

// ============================================
// 🟢 MOSTRAR PEAJES - EN CUADRO FLOTANTE
// ============================================

function mostrarPeajes(datos) {
    var contenedor = document.getElementById("listaPeajes");
    var cuadroFlotante = document.getElementById("cuadroFlotante");
    var peajes = Array.isArray(datos.tolls) ? datos.tolls : [];

    console.log("📌 Mostrando peajes en UI:", peajes.length, "peajes");

    if (!contenedor) return;

    if (!datos.has_tolls || peajes.length === 0) {
        contenedor.innerHTML = '<p class="small-text" style="color:#16a34a;font-size:0.75rem;">🟢 Sin peajes</p>';
        // Si no hay zonas rojas ni peajes, ocultar el cuadro
        var zonasBlock = document.getElementById("resultadoZonasRojas");
        if (zonasBlock && zonasBlock.classList.contains("hidden")) {
            if (cuadroFlotante) cuadroFlotante.classList.add("hidden");
        }
        return;
    }

    // Eliminar duplicados y limpiar nombres
    var nombresVistos = new Set();
    var peajesUnicos = [];

    peajes.forEach(function(peaje) {
        var nombre = peaje.name || "Peaje";
        var nombreLimpio = nombre;
        
        // Limpiar texto extra
        if (nombreLimpio.includes('(Cuota)')) {
            nombreLimpio = nombreLimpio.replace('(Cuota)', '').trim();
        }
        if (nombreLimpio.startsWith('Autopista de Peaje')) {
            nombreLimpio = nombreLimpio.replace('Autopista de Peaje', '').trim();
        }
        if (nombreLimpio.includes(' - ')) {
            var partes = nombreLimpio.split(' - ');
            nombreLimpio = partes[0] + ' - ' + partes[partes.length - 1];
        }
        // Eliminar "estimado" del nombre
        if (nombreLimpio.toLowerCase().includes('estimado')) {
            nombreLimpio = nombreLimpio.replace(/estimado/i, '').trim();
        }
        
        var clave = nombreLimpio;
        if (!nombresVistos.has(clave) && nombreLimpio.length > 3) {
            nombresVistos.add(clave);
            peajesUnicos.push({
                name: nombreLimpio,
                price: peaje.price,
                estimated_location: peaje.estimated_location,
                lat: peaje.lat,
                lng: peaje.lng,
            });
        }
    });

    if (cuadroFlotante) cuadroFlotante.classList.remove("hidden");

    if (peajesUnicos.length === 0) {
        contenedor.innerHTML = '<p class="small-text" style="color:#16a34a;font-size:0.75rem;">🟢 Peajes detectados</p>';
        return;
    }

    var elementos = peajesUnicos.map(function(peaje) {
        var precio = peaje.price ? ' $' + Number(peaje.price).toFixed(2) + ' MXN' : '';
        
        return '<div class="toll-item" style="padding:6px 10px;border-radius:8px;background:#f0fdf4;border:1px solid #86efac;margin-bottom:4px;">' +
            '<strong style="display:block;color:#16a34a;font-size:0.82rem;font-weight:600;">🟢 ' + escaparHtml(peaje.name) + '</strong>' +
            (precio ? '<span style="display:block;margin-top:2px;color:var(--muted);font-size:0.7rem;">' + precio + '</span>' : '') +
            '</div>';
    }).join('');

    // Mostrar advertencia solo si es relevante
    var advertencias = (datos.toll_warnings || [])
        .filter(function(texto) { 
            return texto.includes('Costo de peaje estimado') && !texto.includes('Costo de peaje estimado (OSRM)');
        })
        .map(function(texto) { 
            return '<p style="font-size:0.65rem;color:#999;margin:4px 0 0 0;">💡 ' + escaparHtml(texto) + '</p>';
        })
        .join('');

    contenedor.innerHTML = elementos + advertencias;
}

// ============================================
// LIMPIAR
// ============================================

function limpiarOrigen() {
    porId("entradaOrigen").value = "";
    GPS.posicionOrigen = null;
    if (window.GPSMapa && typeof window.GPSMapa.limpiarRuta === 'function') {
        window.GPSMapa.limpiarRuta();
    }
    // Ocultar cuadro flotante al limpiar
    var cuadroFlotante = document.getElementById("cuadroFlotante");
    if (cuadroFlotante) cuadroFlotante.classList.add("hidden");
}

function limpiarDestino() {
    porId("entradaDestino").value = "";
    GPS.posicionDestino = null;
    if (window.GPSMapa && typeof window.GPSMapa.limpiarRuta === 'function') {
        window.GPSMapa.limpiarRuta();
    }
}

function limpiarTodo() {
    limpiarOrigen();
    limpiarDestino();
    porId("panelResultados").classList.add("hidden");
    ocultarMensaje();
    // Ocultar cuadro flotante al limpiar
    var cuadroFlotante = document.getElementById("cuadroFlotante");
    if (cuadroFlotante) cuadroFlotante.classList.add("hidden");
}

// ============================================
// PANEL
// ============================================

function cerrarPanel() {
    porId("panelControl").classList.add("closed");
    porId("botonAbrirPanel").classList.remove("hidden");
}

function abrirPanel() {
    porId("panelControl").classList.remove("closed");
    porId("botonAbrirPanel").classList.add("hidden");
}

// ============================================
// INICIALIZAR EVENTOS
// ============================================

document.addEventListener("DOMContentLoaded", function() {
    console.log("DOM cargado - inicializando eventos de aplicacion.js");
    
    // Botones principales
    var botonCalcular = porId("botonCalcular");
    var botonLimpiarTodo = porId("botonLimpiarTodo");
    var botonLimpiarOrigen = porId("botonLimpiarOrigen");
    var botonLimpiarDestino = porId("botonLimpiarDestino");
    var botonCerrarPanel = porId("botonCerrarPanel");
    var botonAbrirPanel = porId("botonAbrirPanel");
    var botonVolverInicio = porId("botonVolverInicio");
    
    if (botonCalcular) botonCalcular.addEventListener("click", calcularRuta);
    if (botonLimpiarTodo) botonLimpiarTodo.addEventListener("click", limpiarTodo);
    if (botonLimpiarOrigen) botonLimpiarOrigen.addEventListener("click", limpiarOrigen);
    if (botonLimpiarDestino) botonLimpiarDestino.addEventListener("click", limpiarDestino);
    if (botonCerrarPanel) botonCerrarPanel.addEventListener("click", cerrarPanel);
    if (botonAbrirPanel) botonAbrirPanel.addEventListener("click", abrirPanel);
    if (botonVolverInicio) {
        botonVolverInicio.addEventListener("click", function() {
            window.location.href = "/";
        });
    }

    // Enter en campos de texto
    var entradaOrigen = porId("entradaOrigen");
    var entradaDestino = porId("entradaDestino");
    
    if (entradaOrigen) {
        entradaOrigen.addEventListener("keydown", function(evento) {
            if (evento.key === "Enter") {
                evento.preventDefault();
                calcularRuta();
            }
        });
    }
    
    if (entradaDestino) {
        entradaDestino.addEventListener("keydown", function(evento) {
            if (evento.key === "Enter") {
                evento.preventDefault();
                calcularRuta();
            }
        });
    }

    console.log("Eventos inicializados correctamente");
});

// ============================================
// 🚀 INICIO AUTOMÁTICO DEL MAPA
// ============================================

// Si el DOM ya está cargado, iniciar el mapa inmediatamente
if (document.readyState === 'complete' || document.readyState === 'interactive') {
    console.log('📌 DOM ya cargado, iniciando mapa desde aplicacion.js...');
    if (typeof window.iniciarMapa === 'function') {
        setTimeout(window.iniciarMapa, 500);
    } else {
        console.warn('⚠️ window.iniciarMapa no está disponible');
        // Intentar de nuevo después de un momento
        setTimeout(function() {
            if (typeof window.iniciarMapa === 'function') {
                console.log('✅ window.iniciarMapa ahora está disponible');
                window.iniciarMapa();
            } else {
                console.error('❌ window.iniciarMapa nunca estuvo disponible');
            }
        }, 1000);
    }
} else {
    // Si el DOM aún no está cargado, esperar
    document.addEventListener('DOMContentLoaded', function() {
        console.log('📌 DOMContentLoaded - iniciando mapa desde aplicacion.js...');
        if (typeof window.iniciarMapa === 'function') {
            setTimeout(window.iniciarMapa, 500);
        } else {
            console.warn('⚠️ window.iniciarMapa no está disponible en DOMContentLoaded');
        }
    });
}