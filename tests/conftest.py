import json

import pytest

from app import crear_aplicacion


@pytest.fixture()
def ruta_temporal(tmp_path):
    """Alias en español para la carpeta temporal proporcionada por pytest."""
    return tmp_path


@pytest.fixture()
def parche_mono(monkeypatch):
    """Alias en español para la utilidad monkeypatch de pytest."""
    return monkeypatch


@pytest.fixture()
def archivo_zonas(ruta_temporal):
    ruta = ruta_temporal / "zonas.json"
    ruta.write_text(
        json.dumps([
            {
                "id": "zona-1",
                "name": "Zona de prueba",
                "municipality": "Jilotepec",
                "state": "Estado de México",
                "risks": ["Robo"],
                "description": "Registro temporal para pruebas.",
                "lat": 19.95,
                "lng": -99.53,
                "radius_m": 500,
            }
        ]),
        encoding="utf-8",
    )
    return ruta


@pytest.fixture()
def aplicacion(archivo_zonas):
    return crear_aplicacion({
        "TESTING": True,
        "CLAVE_API_GOOGLE": "test-key",
        "ARCHIVO_ZONAS": archivo_zonas,
    })


@pytest.fixture()
def cliente(aplicacion):
    return aplicacion.test_client()
