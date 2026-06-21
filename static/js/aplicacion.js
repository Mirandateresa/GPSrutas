window.GPS = {
    mapa: null,
    geocodificador: null,
    autocompletadoOrigen: null,
    autocompletadoDestino: null,
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

function formatearMoneda(valor, codigoMoneda = "MXN") {
    const numero = Number(valor || 0);
    return new Intl.NumberFormat("es-MX", {
        style: "currency",
        currency: codigoMoneda,
        maximumFractionDigits: 2,
    }).format(Number.isFinite(numero) ? numero : 0);
}

async function solicitarJson(url, opciones = {}) {
    const respuesta = await fetch(url, {
        ...opciones,
        headers: {
            "Content-Type": "application/json",
            ...(opciones.headers || {}),
        },
    });

    const contenido = await respuesta.json().catch(() => ({
        ok: false,
        error: "El servidor devolvió una respuesta no válida.",
    }));

    if (!respuesta.ok || contenido.ok === false) {
        throw new Error(contenido.error || `Error HTTP ${respuesta.status}`);
    }
    return contenido;
}

function mostrarMensaje(texto, tipo = "info") {
    const caja = porId("cajaMensaje");
    caja.textContent = texto;
    caja.className = `message ${tipo === "info" ? "" : tipo}`.trim();
}

function ocultarMensaje() {
    porId("cajaMensaje").classList.add("hidden");
}

function establecerCarga(activo) {
    const boton = porId("botonCalcular");
    boton.disabled = activo;
    boton.textContent = activo ? "Calculando..." : "Calcular ruta";
}

async function calcularRuta() {
    const origen = porId("entradaOrigen").value.trim();
    const destino = porId("entradaDestino").value.trim();
    const rendimiento = Number(porId("entradaRendimiento").value);

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
        const respuesta = await solicitarJson("/api/route", {
            method: "POST",
            body: JSON.stringify({
                origin: origen,
                destination: destino,
                vehicle_type: porId("selectorVehiculo").value,
                efficiency_km_l: rendimiento,
            }),
        });
        window.GPSMapa.dibujarRuta(respuesta.data);
        mostrarResultado(respuesta.data);
        mostrarMensaje("Ruta calculada correctamente.", "success");
    } catch (error) {
        mostrarMensaje(error.message, "error");
    } finally {
        establecerCarga(false);
    }
}

function mostrarResultado(datos) {
    porId("panelResultados").classList.remove("hidden");
    porId("valorDistancia").textContent = `${Number(datos.distance_km).toFixed(2)} km`;
    porId("valorDuracion").textContent = `${Math.round(Number(datos.duration_min))} min`;
    porId("valorLitros").textContent = `${Number(datos.estimated_liters).toFixed(2)} L`;
    porId("valorCostoCombustible").textContent = formatearMoneda(datos.fuel_cost_mxn);
    porId("valorCostoPeajes").textContent = formatearMoneda(
        datos.toll_cost,
        datos.toll_currency || "MXN",
    );
    porId("valorCostoTotal").textContent = formatearMoneda(datos.total_cost_mxn);

    const origen = datos.origin?.address || datos.origin?.query || "Origen";
    const destino = datos.destination?.address || datos.destination?.query || "Destino";
    porId("descripcionRuta").textContent = `${origen} → ${destino}`;
    mostrarZonasRojas(datos.red_zones || []);
    mostrarPeajes(datos);
}

function mostrarZonasRojas(zonas) {
    const bloque = porId("resultadoZonasRojas");
    const insignia = porId("insigniaAdvertenciaZona");
    const lista = porId("listaZonasRojas");
    lista.innerHTML = "";

    if (!zonas.length) {
        bloque.classList.add("hidden");
        insignia.classList.add("hidden");
        return;
    }

    bloque.classList.remove("hidden");
    insignia.classList.remove("hidden");
    zonas.forEach((zona) => {
        const elemento = document.createElement("li");
        const lugar = [zona.municipality, zona.state].filter(Boolean).join(", ");
        elemento.textContent = `${zona.name}${lugar ? ` — ${lugar}` : ""}`;
        lista.appendChild(elemento);
    });
}

function mostrarPeajes(datos) {
    const contenedor = porId("listaPeajes");
    const peajes = Array.isArray(datos.tolls) ? datos.tolls : [];

    if (!datos.has_tolls) {
        contenedor.innerHTML = '<p class="small-text">La ruta seleccionada no reporta peajes.</p>';
        return;
    }

    const advertencias = (datos.toll_warnings || [])
        .map((texto) => `<p class="small-text">${escaparHtml(texto)}</p>`)
        .join("");

    const elementos = peajes.map((peaje) => {
        const detalle = peaje.address || peaje.instruction || "";
        return `
            <article class="toll-item">
                <strong>${escaparHtml(peaje.name || "Caseta de cobro")}</strong>
                ${detalle ? `<span>${escaparHtml(detalle)}</span>` : ""}
            </article>`;
    }).join("");

    const mensajeSinCasetas = '<p class="small-text">Se detectaron peajes, pero no fue posible identificar cada caseta.</p>';
    contenedor.innerHTML = `${elementos || mensajeSinCasetas}${advertencias}`;
}

function limpiarOrigen() {
    porId("entradaOrigen").value = "";
    GPS.posicionOrigen = null;
    window.GPSMapa?.limpiarRuta();
}

function limpiarDestino() {
    porId("entradaDestino").value = "";
    GPS.posicionDestino = null;
    window.GPSMapa?.limpiarRuta();
}

function limpiarTodo() {
    limpiarOrigen();
    limpiarDestino();
    porId("panelResultados").classList.add("hidden");
    ocultarMensaje();
}

function cerrarPanel() {
    porId("panelControl").classList.add("closed");
    porId("botonAbrirPanel").classList.remove("hidden");
}

function abrirPanel() {
    porId("panelControl").classList.remove("closed");
    porId("botonAbrirPanel").classList.add("hidden");
}

window.gm_authFailure = function () {
    mostrarMensaje(
        "La API key fue rechazada. Revisa configuracion.py y los servicios habilitados.",
        "error",
    );
};

document.addEventListener("DOMContentLoaded", () => {
    porId("botonCalcular").addEventListener("click", calcularRuta);
    porId("botonLimpiarTodo").addEventListener("click", limpiarTodo);
    porId("botonLimpiarOrigen").addEventListener("click", limpiarOrigen);
    porId("botonLimpiarDestino").addEventListener("click", limpiarDestino);
    porId("botonCerrarPanel").addEventListener("click", cerrarPanel);
    porId("botonAbrirPanel").addEventListener("click", abrirPanel);

    [porId("entradaOrigen"), porId("entradaDestino")].forEach((entrada) => {
        entrada.addEventListener("keydown", (evento) => {
            if (evento.key === "Enter") {
                evento.preventDefault();
                calcularRuta();
            }
        });
    });
});
