// static/js/config.js
// ============================================
// CONFIGURACIÓN GLOBAL
// ============================================

var CONFIG = {
    TILE_LAYER: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    TILE_ATTRIBUTION: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    NOMINATIM_URL: 'https://nominatim.openstreetmap.org',
    CENTRO_MAPA: [23.6345, -102.5528],
    ZOOM_INICIAL: 5,
    USER_AGENT: 'GPS-RutasSeguras/1.0',
};

// Estado global de la aplicación
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