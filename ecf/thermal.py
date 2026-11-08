"""Thermal RI data derived exclusively from the stored signed E31/E32 XML."""
import base64
import hashlib
import hmac
from decimal import Decimal
from io import BytesIO

import qrcode
from lxml import etree

from .workflow import ECFWorkflowError, ECF_TYPE_LABELS, ECF_UNIT_LABELS, _amount_text, _representation_qr_url


def thermal_representation(record):
    if record.status not in {"accepted", "accepted_conditional"}:
        raise ECFWorkflowError("La impresión e-CF requiere aceptación DGII.")
    if record.document_type not in {"31", "32"}:
        raise ECFWorkflowError("El formato térmico está habilitado para E31 y E32.")
    raw = (record.signed_xml or "").encode("utf-8")
    if not raw or not record.xml_hash or not hmac.compare_digest(hashlib.sha256(raw).hexdigest(), record.xml_hash):
        raise ECFWorkflowError("El XML firmado no coincide con su hash guardado.")
    root = etree.fromstring(raw, etree.XMLParser(resolve_entities=False, no_network=True))
    def value(node, name):
        values = node.xpath(f".//*[local-name()='{name}']/text()") if node is not None else []
        return str(values[0]).strip() if values else ""
    def section(name):
        values = root.xpath(f".//*[local-name()='{name}']")
        return values[0] if values else None
    header, issuer, buyer, totals = (section(name) for name in ("Encabezado", "Emisor", "Comprador", "Totales"))
    if header is None or issuer is None or totals is None:
        raise ECFWorkflowError("El XML no contiene el encabezado fiscal requerido.")
    encf, rnc = value(header, "eNCF"), value(issuer, "RNCEmisor")
    if (encf, rnc, value(header, "TipoeCF")) != (record.encf, (record.company.rnc or "").strip(), record.document_type):
        raise ECFWorkflowError("La identidad del XML no corresponde al registro e-CF.")
    signature = "".join(value(root, "SignatureValue").split())
    signed_date, emission_date = value(root, "FechaHoraFirma"), value(issuer, "FechaEmision")
    total = value(totals, "MontoTotal")
    legal_name, address = value(issuer, "RazonSocialEmisor"), value(issuer, "DireccionEmisor")
    if not all((legal_name, address, signed_date, emission_date, total)) or len(signature) < 6:
        raise ECFWorkflowError("Faltan datos firmados necesarios para la representación térmica.")
    qr_url = _representation_qr_url(record, issuer_rnc=rnc, buyer_rnc=value(buyer, "RNCComprador"), encf=encf,
                                    emission_date=emission_date, signed_date=signed_date, total=Decimal(total), security_code=signature[:6])
    qr = qrcode.QRCode(box_size=8, border=4, error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(qr_url)
    qr.make(fit=True)
    image = BytesIO()
    qr.make_image(fill_color="black", back_color="white").save(image, format="PNG")
    items = []
    for item in root.xpath(".//*[local-name()='DetallesItems']/*[local-name()='Item']"):
        amount = value(item, "MontoItem")
        tax = value(item, "MontoITBIS") or value(item, "SubTotaITBIS")
        if not tax:
            parts = [value(item, f"SubTotaITBIS{n}") for n in (1, 2, 3)]
            if any(parts):
                tax = _amount_text(sum((Decimal(part) for part in parts if part), Decimal("0")))
        if not tax:
            rate = {"1": Decimal(".18"), "2": Decimal(".16"), "3": Decimal("0"), "4": Decimal("0"), "0": Decimal("0")}.get(value(item, "IndicadorFacturacion"))
            if rate is None:
                raise ECFWorkflowError("Una línea no tiene tratamiento ITBIS representable.")
            tax = _amount_text(Decimal(amount) * rate / (1 + rate) if value(header, "IndicadorMontoGravado") == "1" else Decimal(amount) * rate)
        unit = value(item, "UnidadMedida")
        items.append({"quantity": value(item, "CantidadItem"), "description": value(item, "NombreItem"),
                      "unit": ECF_UNIT_LABELS.get(unit, unit), "price": value(item, "PrecioUnitarioItem"),
                      "tax": tax, "amount": amount, "discount": value(item, "DescuentoMonto"), "surcharge": value(item, "RecargoMonto")})
    if not items:
        raise ECFWorkflowError("El XML firmado no contiene líneas de detalle.")
    summary = []
    for key, label in (("MontoGravadoTotal", "Subtotal Gravado:"), ("MontoExento", "Subtotal Exento:"),
                       ("TotalITBIS", "Total ITBIS:"), ("MontoImpuestoAdicional", "Impuestos adicionales:"),
                       ("MontoNoFacturable", "Monto no facturable:"), ("MontoTotal", "Total:")):
        text = value(totals, key)
        if key == "TotalITBIS" and not text:
            text = "0.00"
        if text:
            summary.append({"label": label, "value": text})
    # No buyer block on the E32 illustrative model. E31 retains signed identity.
    return {"encf": encf, "document_type": record.document_type, "title": ECF_TYPE_LABELS[record.document_type],
            "issuer": {"name": legal_name, "trade_name": value(issuer, "NombreComercial"), "rnc": rnc, "address": address,
                       "branch": value(issuer, "Sucursal"), "phone": value(issuer, "TelefonoEmisor"), "email": value(issuer, "CorreoEmisor")},
            "buyer": {"name": value(buyer, "RazonSocialComprador"), "rnc": value(buyer, "RNCComprador")} if record.document_type == "31" else None,
            "emission_date": emission_date, "expiry": value(header, "FechaVencimientoSecuencia"),
            "signed_date": signed_date, "security_code": signature[:6], "items": items, "totals": summary,
            "qr_url": qr_url, "qr_image": "data:image/png;base64," + base64.b64encode(image.getvalue()).decode("ascii")}
