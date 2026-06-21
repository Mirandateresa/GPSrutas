window.GPSZonas = {
    cargar: cargarZonas,
    mostrar: mostrarZonas,
    ocultar: ocultarZonas,
    seleccionarPunto: seleccionarPuntoZona,
};

async function cargarZonas() {
    try {
        const respuesta = await solicitarJson("/api/zones");
        GPS.zonas = respuesta.data || [];
        if (GPS.zonasVisibles) {
            dibujarZonas();
        }
    } catch (error) {
        mostrarMensaje(`No fue posible cargar las zonas: ${error.message}`, "error");
    }
}

function alternarZonas() {
    GPS.zonasVisibles ? ocultarZonas() : mostrarZonas();
}

function mostrarZonas() {
    GPS.zonasVisibles = true;
    porId("botonAlternarZonas").classList.add("active");
    porId("botonAlternarZonas").textContent = "Ocultar zonas rojas";
    dibujarZonas();
}

function ocultarZonas() {
    GPS.zonasVisibles = false;
    porId("botonAlternarZonas").classList.remove("active");
    porId("botonAlternarZonas").textContent = "Mostrar zonas rojas";
    limpiarCapasZonas();
}

function dibujarZonas() {
    if (!GPS.mapa) {
        return;
    }
    limpiarCapasZonas();

    GPS.zonas.forEach((zona) => {
        const posicion = {
            lat: Number(zona.lat),
            lng: Number(zona.lng),
        };
        const radio = Number(zona.radius_m);
        if (!Number.isFinite(posicion.lat) || !Number.isFinite(posicion.lng)) {
            return;
        }

        const circulo = new google.maps.Circle({
            map: GPS.mapa,
            center: posicion,
            radius: Number.isFinite(radio) ? radio : 500,
            fillColor: "#dc2626",
            fillOpacity: 0.16,
            strokeColor: "#b91c1c",
            strokeOpacity: 0.8,
            strokeWeight: 2,
        });
        const marcador = new google.maps.Marker({
            map: GPS.mapa,
            position: posicion,
            title: zona.name,
            label: { text: "!", color: "white", fontWeight: "bold" },
            icon: {
                path: google.maps.SymbolPath.CIRCLE,
                fillColor: "#c62828",
                fillOpacity: 1,
                strokeColor: "#ffffff",
                strokeWeight: 2,
                scale: 11,
            },
        });
        marcador.addListener("click", () => abrirDialogoZona(zona));
        circulo.addListener("click", () => abrirDialogoZona(zona));
        GPS.capasZonas.push(circulo, marcador);
    });
}

function limpiarCapasZonas() {
    GPS.capasZonas.forEach((capa) => capa.setMap(null));
    GPS.capasZonas = [];
}

function iniciarColocacionZona() {
    if (!GPS.mapa) {
        mostrarMensaje("El mapa todavía no está listo.", "error");
        return;
    }
    GPS.modoColocarZona = true;
    mostrarMensaje("Haz clic en el mapa para colocar el centro de la nueva zona roja.");
}

async function seleccionarPuntoZona(coordenadaGoogle) {
    GPS.modoColocarZona = false;
    const posicion = {
        lat: coordenadaGoogle.lat(),
        lng: coordenadaGoogle.lng(),
    };
    abrirDialogoZona({
        id: "",
        name: "",
        municipality: "",
        state: "",
        risks: [],
        description: "",
        lat: posicion.lat,
        lng: posicion.lng,
        radius_m: 500,
    });
    await completarDireccionZona(posicion);
}

async function completarDireccionZona(posicion) {
    if (!GPS.geocodificador) {
        return;
    }
    porId("estadoFormularioZona").textContent = "Consultando la dirección del punto...";

    try {
        const respuesta = await GPS.geocodificador.geocode({ location: posicion });
        const resultado = respuesta.results?.[0];
        if (!resultado) {
            return;
        }

        const obtenerComponente = (tipos) => {
            const encontrado = (resultado.address_components || []).find((elemento) =>
                tipos.some((tipo) => elemento.types.includes(tipo))
            );
            return encontrado?.long_name || "";
        };

        if (!porId("nombreZona").value) {
            porId("nombreZona").value = resultado.formatted_address?.split(",")[0] || "";
        }
        porId("municipioZona").value = obtenerComponente([
            "locality",
            "administrative_area_level_2",
            "sublocality",
        ]);
        porId("estadoZona").value = obtenerComponente(["administrative_area_level_1"]);
    } catch (error) {
        porId("estadoFormularioZona").textContent =
            "No fue posible completar la dirección automáticamente.";
        return;
    }
    porId("estadoFormularioZona").textContent = "Ubicación completada correctamente.";
}

function abrirDialogoZona(zona = null) {
    const editando = Boolean(zona?.id);
    porId("tituloDialogoZona").textContent = editando ? "Editar zona roja" : "Nueva zona roja";
    porId("idZona").value = zona?.id || "";
    porId("nombreZona").value = zona?.name || "";
    porId("municipioZona").value = zona?.municipality || "";
    porId("estadoZona").value = zona?.state || "";
    porId("riesgosZona").value = (zona?.risks || []).join(", ");
    porId("descripcionZona").value = zona?.description || "";
    porId("latitudZona").value = zona?.lat ?? "";
    porId("longitudZona").value = zona?.lng ?? "";
    porId("radioZona").value = zona?.radius_m || 500;
    porId("estadoFormularioZona").textContent = "";
    porId("botonEliminarZona").classList.toggle("hidden", !editando);
    porId("dialogoZona").showModal();
}

function cerrarDialogoZona() {
    GPS.modoColocarZona = false;
    porId("dialogoZona").close();
}

function obtenerDatosFormularioZona() {
    return {
        name: porId("nombreZona").value.trim(),
        municipality: porId("municipioZona").value.trim(),
        state: porId("estadoZona").value.trim(),
        risks: porId("riesgosZona").value
            .split(",")
            .map((elemento) => elemento.trim())
            .filter(Boolean),
        description: porId("descripcionZona").value.trim(),
        lat: Number(porId("latitudZona").value),
        lng: Number(porId("longitudZona").value),
        radius_m: Number(porId("radioZona").value),
    };
}

async function guardarZona(evento) {
    evento.preventDefault();
    const id = porId("idZona").value;
    const metodo = id ? "PUT" : "POST";
    const url = id ? `/api/zones/${encodeURIComponent(id)}` : "/api/zones";
    porId("estadoFormularioZona").textContent = "Guardando...";

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
        mostrarMensaje("Zona guardada correctamente.", "success");
    } catch (error) {
        porId("estadoFormularioZona").textContent = error.message;
    }
}

async function eliminarZona() {
    const id = porId("idZona").value;
    if (!id || !window.confirm("¿Deseas eliminar esta zona roja?")) {
        return;
    }

    try {
        await solicitarJson(`/api/zones/${encodeURIComponent(id)}`, {
            method: "DELETE",
        });
        await cargarZonas();
        dibujarZonas();
        cerrarDialogoZona();
        mostrarMensaje("Zona eliminada correctamente.", "success");
    } catch (error) {
        porId("estadoFormularioZona").textContent = error.message;
    }
}

document.addEventListener("DOMContentLoaded", () => {
    porId("botonAlternarZonas").addEventListener("click", alternarZonas);
    porId("botonAgregarZona").addEventListener("click", iniciarColocacionZona);
    porId("formularioZona").addEventListener("submit", guardarZona);
    porId("botonEliminarZona").addEventListener("click", eliminarZona);
    porId("botonCerrarDialogoZona").addEventListener("click", cerrarDialogoZona);
    porId("botonCancelarZona").addEventListener("click", cerrarDialogoZona);
});
