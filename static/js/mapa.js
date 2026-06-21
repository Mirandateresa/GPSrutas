window.GPSMapa = {
    dibujarRuta,
    limpiarRuta,
    enfocarPosicion,
};

function iniciarMapa() {
    GPS.mapa = new google.maps.Map(porId("mapa"), {
        center: { lat: 23.6345, lng: -102.5528 },
        zoom: 5,
        mapTypeControl: false,
        streetViewControl: false,
        fullscreenControl: true,
        gestureHandling: "greedy",
    });
    GPS.geocodificador = new google.maps.Geocoder();

    configurarAutocompletado("entradaOrigen", "origen");
    configurarAutocompletado("entradaDestino", "destino");

    GPS.mapa.addListener("click", async (evento) => {
        if (GPS.modoColocarZona && window.GPSZonas) {
            window.GPSZonas.seleccionarPunto(evento.latLng);
            return;
        }
        await seleccionarPuntoRuta(evento.latLng);
    });

    window.GPSZonas?.cargar();
    mostrarMensaje(
        "Mapa listo. Escribe una dirección o selecciona puntos en el mapa.",
        "success",
    );
}

window.iniciarMapa = iniciarMapa;

function configurarAutocompletado(idEntrada, tipo) {
    const entrada = porId(idEntrada);
    const autocompletado = new google.maps.places.Autocomplete(entrada, {
        componentRestrictions: { country: "mx" },
        fields: ["formatted_address", "geometry", "name"],
    });

    autocompletado.addListener("place_changed", () => {
        const lugar = autocompletado.getPlace();
        if (!lugar.geometry?.location) {
            mostrarMensaje("Selecciona una dirección de la lista de sugerencias.", "error");
            return;
        }

        const posicion = {
            lat: lugar.geometry.location.lat(),
            lng: lugar.geometry.location.lng(),
        };
        entrada.value = lugar.formatted_address || lugar.name || entrada.value;

        if (tipo === "origen") {
            GPS.posicionOrigen = posicion;
        } else {
            GPS.posicionDestino = posicion;
        }
        enfocarPosicion(posicion, 14);
    });

    if (tipo === "origen") {
        GPS.autocompletadoOrigen = autocompletado;
    } else {
        GPS.autocompletadoDestino = autocompletado;
    }
}

async function seleccionarPuntoRuta(coordenadaGoogle) {
    const posicion = {
        lat: coordenadaGoogle.lat(),
        lng: coordenadaGoogle.lng(),
    };
    const objetivo = !porId("entradaOrigen").value.trim()
        ? "origen"
        : !porId("entradaDestino").value.trim()
            ? "destino"
            : "destino";

    try {
        const respuesta = await GPS.geocodificador.geocode({ location: posicion });
        const direccion = respuesta.results?.[0]?.formatted_address ||
            `${posicion.lat.toFixed(6)}, ${posicion.lng.toFixed(6)}`;

        if (objetivo === "origen") {
            porId("entradaOrigen").value = direccion;
            GPS.posicionOrigen = posicion;
            mostrarMensaje("Origen seleccionado. Ahora elige el destino.");
        } else {
            porId("entradaDestino").value = direccion;
            GPS.posicionDestino = posicion;
            mostrarMensaje("Destino seleccionado. Ya puedes calcular la ruta.");
        }
        dibujarMarcadoresSeleccion();
    } catch (error) {
        mostrarMensaje("No fue posible obtener la dirección del punto seleccionado.", "error");
    }
}

function dibujarMarcadoresSeleccion() {
    GPS.marcadoresRuta.forEach((marcador) => marcador.setMap(null));
    GPS.marcadoresRuta = [];

    if (GPS.posicionOrigen) {
        GPS.marcadoresRuta.push(new google.maps.Marker({
            map: GPS.mapa,
            position: GPS.posicionOrigen,
            title: "Origen",
            label: { text: "A", color: "white", fontWeight: "bold" },
            icon: iconoCircular("#2563eb"),
        }));
    }

    if (GPS.posicionDestino) {
        GPS.marcadoresRuta.push(new google.maps.Marker({
            map: GPS.mapa,
            position: GPS.posicionDestino,
            title: "Destino",
            label: { text: "B", color: "white", fontWeight: "bold" },
            icon: iconoCircular("#c62828"),
        }));
    }
}

function iconoCircular(color) {
    return {
        path: google.maps.SymbolPath.CIRCLE,
        fillColor: color,
        fillOpacity: 1,
        strokeColor: "#ffffff",
        strokeWeight: 3,
        scale: 13,
    };
}

function dibujarRuta(datos) {
    limpiarRuta();
    const trayecto = (datos.coordinates || [])
        .map((punto) => ({
            lat: Number(punto.lat),
            lng: Number(punto.lng),
        }))
        .filter((punto) => Number.isFinite(punto.lat) && Number.isFinite(punto.lng));

    if (trayecto.length < 2) {
        mostrarMensaje("La ruta no contiene coordenadas suficientes para dibujarla.", "error");
        return;
    }

    GPS.lineaRuta = new google.maps.Polyline({
        map: GPS.mapa,
        path: trayecto,
        strokeColor: "#2563eb",
        strokeOpacity: 0.95,
        strokeWeight: 6,
        geodesic: true,
    });

    GPS.posicionOrigen = {
        lat: Number(datos.origin.lat),
        lng: Number(datos.origin.lng),
    };
    GPS.posicionDestino = {
        lat: Number(datos.destination.lat),
        lng: Number(datos.destination.lng),
    };

    dibujarMarcadoresSeleccion();
    dibujarMarcadoresPeajes(datos.tolls || []);

    const limites = new google.maps.LatLngBounds();
    trayecto.forEach((punto) => limites.extend(punto));
    GPS.mapa.fitBounds(limites, 55);

    if (datos.has_red_zones && !GPS.zonasVisibles) {
        window.GPSZonas?.mostrar();
    }
}

function dibujarMarcadoresPeajes(peajes) {
    GPS.marcadoresPeajes.forEach((marcador) => marcador.setMap(null));
    GPS.marcadoresPeajes = [];

    peajes.forEach((peaje) => {
        const latitud = Number(peaje.lat);
        const longitud = Number(peaje.lng);
        if (!Number.isFinite(latitud) || !Number.isFinite(longitud)) {
            return;
        }

        const marcador = new google.maps.Marker({
            map: GPS.mapa,
            position: { lat: latitud, lng: longitud },
            title: peaje.name || "Caseta de cobro",
            label: { text: "$", color: "white", fontWeight: "bold" },
            icon: iconoCircular("#b45309"),
        });
        const informacion = new google.maps.InfoWindow({
            content: `<strong>${escaparHtml(peaje.name || "Caseta")}</strong><br>` +
                `<small>${escaparHtml(peaje.address || peaje.instruction || peaje.source || "")}</small>`,
        });
        marcador.addListener("click", () => {
            informacion.open({ map: GPS.mapa, anchor: marcador });
        });
        GPS.marcadoresPeajes.push(marcador);
    });
}

function limpiarRuta() {
    if (GPS.lineaRuta) {
        GPS.lineaRuta.setMap(null);
        GPS.lineaRuta = null;
    }
    GPS.marcadoresRuta.forEach((marcador) => marcador.setMap(null));
    GPS.marcadoresPeajes.forEach((marcador) => marcador.setMap(null));
    GPS.marcadoresRuta = [];
    GPS.marcadoresPeajes = [];
}

function enfocarPosicion(posicion, acercamiento = 15) {
    if (!GPS.mapa) {
        return;
    }
    GPS.mapa.panTo(posicion);
    GPS.mapa.setZoom(acercamiento);
}
