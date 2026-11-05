"""URL compatibility checks for the public DGII receiver services."""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "MultiServices.settings")

import django

django.setup()

import pytest
from django.urls import resolve, reverse


@pytest.mark.parametrize(
    ("url", "name"),
    [
        ("/FE/RECEPCION/API/ECF", "dgii-recepcion-standard"),
        ("/Fe/Autenticacion/Api/Semilla/", "dgii-semilla-standard"),
        ("/FE/AUTENTICACION/API/VALIDACIONCERTIFICADO", "dgii-auth-standard"),
        ("/Fe/AprobacionComercial/Api/Ecf/", "dgii-aprobacion-standard"),
        ("/api/v1/FE/RECEPCION/API/ECF", "dgii-recepcion"),
    ],
)
def test_dgii_service_paths_are_case_insensitive_and_allow_optional_trailing_slash(url, name):
    assert resolve(url).url_name == name


@pytest.mark.parametrize("name", [
    "invoicesheader-list", "company-list", "UserLogin",
    "dgii-semilla-standard", "dgii-auth-standard", "dgii-recepcion-standard",
    "dgii-aprobacion-standard", "dgii-semilla", "dgii-validacion-certificado",
    "dgii-recepcion", "dgii-aprobacion",
])
def test_url_reverse_does_not_break_legacy_invoices_or_dgii(name):
    assert resolve(reverse(name)).url_name == name


def test_normal_application_exposes_both_legacy_api_and_receiver():
    assert resolve("/api/v1/invoicesHeaders/").url_name == "invoicesheader-list"
    assert resolve("/FE/RECEPCION/API/ECF").url_name == "dgii-recepcion-standard"
    assert resolve("/admin/").view_name == "admin:index"
