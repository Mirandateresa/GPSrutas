from flask import Blueprint, current_app, render_template


plano_paginas = Blueprint("paginas", __name__)


@plano_paginas.get("/")
def inicio():
    """Pantalla de inicio con botón para entrar al mapa"""
    return render_template("inicio.html")


@plano_paginas.get("/mapa")
def mapa():
    """Pantalla principal del mapa"""
    return render_template(
        "index.html",
        clave_api_google=current_app.config["CLAVE_API_GOOGLE"],
        rendimiento_predeterminado=current_app.config["RENDIMIENTO_PREDETERMINADO_KM_L"],
    )