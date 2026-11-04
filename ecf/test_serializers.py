"""API representation checks for certification workflow metadata."""

from types import SimpleNamespace

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "MultiServices.settings")

import django

django.setup()

from ecf.serializers import ElectronicInvoiceSerializer
from ecf.models import ECFEnvironment


def test_electronic_invoice_serializer_exposes_only_certification_attempt_identifier():
    record = SimpleNamespace(payload={"certification_attempt": "portal-reset-20261017-01"})

    assert ElectronicInvoiceSerializer().get_certification_attempt(record) == "portal-reset-20261017-01"


def test_electronic_invoice_serializer_uses_empty_attempt_for_normal_invoice():
    record = SimpleNamespace(payload={})

    assert ElectronicInvoiceSerializer().get_certification_attempt(record) == ""


def test_electronic_invoice_serializer_reports_certification_identity_mismatch():
    record = SimpleNamespace(
        environment=ECFEnvironment.CERT,
        signed_xml=(
            "<ECF><Encabezado><Emisor>"
            "<RazonSocialEmisor>DOCUMENTOS ELECTRONICOS DE 02</RazonSocialEmisor>"
            "<RNCEmisor>132018559</RNCEmisor>"
            "<DireccionEmisor>AVE. ISABEL AGUIAR NO. 269</DireccionEmisor>"
            "</Emisor></Encabezado></ECF>"
        ),
        company=SimpleNamespace(
            name="Ferreteria Casa Minaya Arias, S.R.L.",
            rnc="132018559",
            address="Calle Corazón de Jesús, esq. 12, El Almirante Caña, Sto. Dgo. Este",
        ),
    )

    assert ElectronicInvoiceSerializer().get_representation_identity_current(record) is False
