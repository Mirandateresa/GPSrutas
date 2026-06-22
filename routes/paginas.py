from flask import Blueprint, current_app, render_template


plano_paginas = Blueprint("paginas", __name__)


@plano_paginas.get("/")
def inicio():
    """Pantalla de inicio con botón para entrar al mapa"""
    return render_template("inicio.html")


@plano_paginas.get("/mapa")
def mapa():
    """Pantalla principal del mapa - sin API key de Google"""
    return render_template(
        "index.html",
        rendimiento_predeterminado=current_app.config.get("RENDIMIENTO_PREDETERMINADO_KM_L", 14.0),
    )