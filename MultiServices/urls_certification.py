"""Expose only receiver services in the isolated certification instance."""

from django.urls import re_path
from administration.fe_views import (
    dgii_semilla, dgii_validacion_certificado,
    dgii_recepcion_ecf, dgii_aprobacion_comercial,
)


def insensitive(value):
    # Character classes are reversible by Django; inline (?i) flags are not.
    return "".join(f"[{c.lower()}{c.upper()}]" if c.isascii() and c.isalpha() else c for c in value)


urlpatterns = [
    re_path("^" + insensitive(route) + "/?$", view, name=name)
    for route, view, name in (
        ("fe/autenticacion/api/semilla", dgii_semilla, "dgii-semilla-standard"),
        ("fe/autenticacion/api/validacioncertificado", dgii_validacion_certificado, "dgii-auth-standard"),
        ("fe/recepcion/api/ecf", dgii_recepcion_ecf, "dgii-recepcion-standard"),
        ("fe/aprobacioncomercial/api/ecf", dgii_aprobacion_comercial, "dgii-aprobacion-standard"),
    )
]
