"""Local e-CF document preparation and guarded certification transport."""
from __future__ import annotations

import hashlib
import hmac
from html import escape as html_escape
import json
import os
from io import BytesIO
import re
import sqlite3
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from decimal import ROUND_HALF_UP

from django.conf import settings as django_settings
from dotenv import load_dotenv
from lxml import etree

from .certificate import load_pkcs12
from .config import Settings
from .issuance import validate_production_record, link_accepted_sale
from .dgii_auth import DGIIAuthenticator
from .dgii_reception import DGIIReceptionClient, ECFResult, ReceptionResponse
from .dgii_rfce import DGIIRFCEClient, RFCEReceipt
from .exceptions import ECFError
from .models import ElectronicInvoice, ECFEnvironment, RFCEStatus
from .signing import sign_xml, verify_xml_signature
from .test_run_registry import ECFTestRegistry
from .test_set_loader import CERTIFICATION_EXPECTED_COUNTS, CERTIFICATION_SEND_ORDER
from .xml_builder import build_ecf_xml
from .xml_utils import validate_xsd

XSD_NS = "http://www.w3.org/2001/XMLSchema"

ECF_TYPE_LABELS = {
    "31": "Factura de Crédito Fiscal Electrónica",
    "32": "Factura de Consumo Electrónica",
    "33": "Nota de Débito Electrónica",
    "34": "Nota de Crédito Electrónica",
    "41": "Compras Electrónico",
    "43": "Gastos Menores Electrónico",
    "44": "Regímenes Especiales Electrónica",
    "45": "Gubernamental Electrónico",
    "46": "Comprobante para Exportaciones Electrónico",
    "47": "Comprobante para Pagos al Exterior Electrónico",
}

DGII_EMAIL_PATTERN = re.compile(
    r"[A-Za-z0-9]+([-+.]\w+)*@[A-Za-z0-9]+([-.]\w+)*\.[A-Za-z0-9]+([-.]\w+)*"
)


def _is_valid_dgii_email(value: str | None) -> bool:
    email = (value or "").strip()
    return len(email) <= 80 and bool(DGII_EMAIL_PATTERN.fullmatch(email))

ECF_UNIT_LABELS = {
    "1": "BARR · Barril", "2": "BOL · Bolsa", "3": "BOT · Bote",
    "4": "BULTO · Bultos", "5": "BOTELLA · Botella", "6": "CAJ · Caja/Cajón",
    "7": "CAJETILLA · Cajetilla", "8": "CM · Centímetro", "9": "CIL · Cilindro",
    "10": "CONJ · Conjunto", "11": "CONT · Contenedor", "12": "DÍA · Día",
    "13": "DOC · Docena", "14": "FARD · Fardo", "15": "GL · Galones",
    "16": "GRAD · Grado", "17": "GR · Gramo", "18": "GRAN · Granel",
    "19": "HOR · Hora", "20": "HUAC · Huacal", "21": "KG · Kilogramo",
    "22": "kWh · Kilovatio hora", "23": "LB · Libra", "24": "LITRO · Litro",
    "25": "LOT · Lote", "26": "M · Metro", "27": "M2 · Metro cuadrado",
    "28": "M3 · Metro cúbico", "29": "MMBTU · Millones de unidades térmicas",
    "30": "MIN · Minuto", "31": "PAQ · Paquete", "32": "PAR · Par",
    "33": "PIE · Pie", "34": "PZA · Pieza", "35": "ROL · Rollo",
    "36": "SOBR · Sobre", "37": "SEG · Segundo", "38": "TANQUE · Tanque",
    "39": "TONE · Tonelada", "40": "TUB · Tubo", "41": "YD · Yarda",
    "42": "YD2 · Yarda cuadrada", "43": "UND · Unidad", "44": "EA · Elemento",
    "45": "MILLAR · Millar", "46": "SAC · Saco", "47": "LAT · Lata",
    "48": "DIS · Display", "49": "BID · Bidón", "50": "RAC · Ración",
    "51": "Q · Quintal", "52": "GRT · Tonelada de registro bruto",
    "53": "P2 · Pie cuadrado", "54": "PAX · Pasajero", "55": "PULG · Pulgada",
    "56": "STAY · Parqueo de barcos en muelle", "57": "BDJ · Bandeja",
    "58": "HA · Hectárea", "59": "ML · Mililitro", "60": "MG · Miligramo",
    "61": "OZ · Onza", "62": "OZT · Onza Troy",
}

class ECFWorkflowError(ECFError):
    """A document cannot safely advance to the requested e-CF state."""


def project_path(*parts: str) -> Path:
    return Path(django_settings.BASE_DIR).joinpath(*parts)


def _settings_for_record(record: ElectronicInvoice, *, require_range: bool = True) -> Settings:
    load_dotenv(project_path(".env"), override=False)
    try:
        config = Settings.from_env()
    except Exception as exc:
        raise ECFWorkflowError("La configuración DGII o del certificado no está completa.") from exc
    try:
        if require_range:
            validate_production_record(record)
    except ValueError as exc:
        raise ECFWorkflowError(str(exc)) from exc
    if config.environment != record.environment:
        raise ECFWorkflowError(
            "El ambiente DGII configurado no coincide con el ambiente del documento."
        )
    if record.environment == ECFEnvironment.PROD and not config.expected_tax_id:
        raise ECFWorkflowError("Configura ECF_EXPECTED_TAX_ID antes de emitir en producción.")
    _validate_expected_tax_id(config.expected_tax_id, record.company.rnc)
    return config


def _validate_expected_tax_id(expected_tax_id: str | None, company_rnc: str | None) -> None:
    expected = (expected_tax_id or "").strip()
    actual = (company_rnc or "").strip()
    if expected and expected != actual:
        raise ECFWorkflowError(
            "ECF_EXPECTED_TAX_ID no coincide con el RNC de la empresa del comprobante."
        )


def _document_identity(xml_data: bytes) -> tuple[str, str, str]:
    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    try:
        root = etree.fromstring(xml_data, parser)
    except etree.XMLSyntaxError as exc:
        raise ECFWorkflowError("El documento e-CF no contiene XML válido.") from exc

    if etree.QName(root).localname != "ECF":
        raise ECFWorkflowError("El elemento raíz debe ser ECF.")

    def value(name: str) -> str:
        nodes = root.xpath(f".//*[local-name()='{name}']")
        return (nodes[0].text or "").strip() if nodes else ""

    rnc, encf, document_type = value("RNCEmisor"), value("eNCF"), value("TipoeCF")
    if not all((rnc, encf, document_type)):
        raise ECFWorkflowError("El XML debe incluir RNCEmisor, eNCF y TipoeCF.")
    return rnc, encf, document_type


def _xsd_for_record(record: ElectronicInvoice) -> Path:
    xsd_path = project_path("xsd", f"ECF{record.document_type}V1.0.xsd")
    if not xsd_path.is_file():
        raise ECFWorkflowError(
            f"No está instalado el XSD DGII para el tipo e-CF {record.document_type}."
        )
    return xsd_path


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _amount_text(value: Decimal) -> str:
    return format(_money(value), ".2f")


def _representation_qr_url(
    record: ElectronicInvoice,
    *,
    issuer_rnc: str,
    buyer_rnc: str,
    encf: str,
    emission_date: str,
    signed_date: str,
    total: Decimal,
    security_code: str,
) -> str:
    """Build the environment-specific DGII lookup URL printed in an RI QR."""
    from urllib.parse import quote, urlencode

    environment_path = {
        ECFEnvironment.PRECERT: "testecf",
        ECFEnvironment.CERT: "certecf",
        ECFEnvironment.PROD: "ecf",
    }.get(record.environment)
    if environment_path is None:
        raise ECFWorkflowError("El ambiente e-CF no tiene una ruta QR DGII configurada.")

    total_text = _amount_text(total)
    if record.document_type == "32" and total < Decimal("250000"):
        base_url = f"https://fc.dgii.gov.do/{environment_path}/consultatimbrefc"
        query = {
            "RncEmisor": issuer_rnc,
            "ENCF": encf,
            "MontoTotal": total_text,
            "CodigoSeguridad": security_code,
        }
    else:
        base_url = f"https://ecf.dgii.gov.do/{environment_path}/consultatimbre"
        query = {
            "RncEmisor": issuer_rnc,
            "RncComprador": buyer_rnc,
            "ENCF": encf,
            "FechaEmision": emission_date,
            "MontoTotal": total_text,
            "FechaFirma": signed_date,
            "CodigoSeguridad": security_code,
        }
        if not buyer_rnc:
            query.pop("RncComprador")
    # DGII specifies percent-encoding for reserved QR URL characters (%20 for spaces).
    return f"{base_url}?{urlencode(query, quote_via=quote, safe='')}"


def _linked_sale_values(record: ElectronicInvoice) -> dict[str, str]:
    """Map a real, stored sale to the e-CF detail without changing legacy data."""
    from sales.models import InvoicesDetail

    invoice = record.invoice
    if invoice is None:
        raise ECFWorkflowError("Los e-CF tipo 31 y 32 requieren una factura fuente real.")
    if invoice.company_id != record.company_id or invoice.invoiceStatus:
        raise ECFWorkflowError("La factura fuente no está activa para esta empresa.")
    if invoice.paymentMethod not in {"CASH", "CREDIT"}:
        raise ECFWorkflowError("La factura fuente no tiene forma de pago clasificable.")

    company = record.company
    customer = invoice.customer
    buyer_raw = (customer.identification or "").strip()
    buyer_id = "".join(ch for ch in buyer_raw if ch.isdigit())
    buyer_id_valid = len(buyer_id) in {9, 11} and bool(re.fullmatch(r"[0-9-]+", buyer_raw))
    document_total = _money(Decimal(invoice.subtotal) - Decimal(invoice.discount))
    if document_total <= 0:
        raise ECFWorkflowError("La factura fuente tiene un total no positivo.")
    if record.document_type == "31" and not buyer_id_valid:
        raise ECFWorkflowError("El e-CF tipo 31 requiere RNC o cédula válida del comprador.")
    if record.document_type == "32" and document_total >= Decimal("250000") and not buyer_id_valid:
        raise ECFWorkflowError(
            "El e-CF tipo 32 de DOP 250,000 o más requiere RNC o cédula válida del comprador."
        )

    details = list(
        InvoicesDetail.objects.filter(invoice=invoice).select_related("product").order_by("id")
    )
    if not details:
        raise ECFWorkflowError("La factura fuente no contiene líneas de detalle.")

    values: dict[str, str] = dict(record.payload or {})
    values.update(
        {
            "Version": "1.0",
            "TipoeCF": record.document_type,
            "RNCEmisor": (company.rnc or "").strip(),
            "RazonSocialEmisor": (company.name or "").strip(),
            "FechaEmision": invoice.creationDate.astimezone(
                ZoneInfo("America/Santo_Domingo")
            ).strftime("%d-%m-%Y"),
            "TipoIngresos": values.get("TipoIngresos", "01"),
            "TipoPago": "1" if invoice.paymentMethod == "CASH" else "2",
        }
    )
    if customer.firstName or customer.lastName:
        values["RazonSocialComprador"] = f"{customer.firstName} {customer.lastName}".strip()
    if buyer_id_valid:
        values["RNCComprador"] = buyer_id
    else:
        values.pop("RNCComprador", None)
        values.pop("IdentificadorExtranjero", None)
    if _is_valid_dgii_email(customer.email):
        values["CorreoComprador"] = customer.email.strip()
    else:
        values.pop("CorreoComprador", None)
    if customer.address and len(customer.address) <= 100:
        values["DireccionComprador"] = customer.address
    if company.address and len(company.address) <= 100:
        values["DireccionEmisor"] = company.address
    if _is_valid_dgii_email(company.email):
        values["CorreoEmisor"] = company.email.strip()
    else:
        values.pop("CorreoEmisor", None)

    line_gross: list[Decimal] = []
    line_discounts: list[Decimal] = []
    line_tax: list[Decimal] = []
    line_codes: list[int] = []
    amount_indicators: set[int] = set()
    base_by_code = {1: Decimal("0"), 2: Decimal("0"), 3: Decimal("0"), 4: Decimal("0")}
    tax_by_code = {1: Decimal("0"), 2: Decimal("0"), 3: Decimal("0")}

    for index, detail in enumerate(details, 1):
        quantity = Decimal(detail.quantity)
        price = Decimal(detail.price)
        tax = Decimal(detail.itbis)
        # InvoicesDetail stores the discount for the entire line, not per unit.
        discount = _money(Decimal(detail.discount))
        if quantity <= 0 or quantity != quantity.quantize(Decimal("0.01")) or price < 0 or tax < 0 or discount < 0:
            raise ECFWorkflowError(
                "La factura contiene cantidades (máximo dos decimales), descuentos o impuestos inválidos."
            )
        gross = _money(quantity * price)
        if discount > gross:
            raise ECFWorkflowError("El descuento de una línea supera su importe.")
        net = gross - discount
        tax = _money(tax)

        code_key = f"IndicadorFacturacion[{index}]"
        supplied_code = values.get(code_key) or values.get("zero_tax_treatment") if tax == 0 else values.get(code_key)
        if tax == 0:
            if supplied_code not in {"3", "4"}:
                raise ECFWorkflowError(
                    f"Indica si la línea {index} es tasa ITBIS 0 (3) o exenta (4)."
                )
            code = int(supplied_code)
            values[code_key] = str(code)
            base = net
        else:
            inclusive = None
            code = None
            for candidate_code, rate in ((1, Decimal("0.18")), (2, Decimal("0.16"))):
                if gross > tax and abs(tax / (gross - tax) - rate) <= Decimal("0.001"):
                    inclusive, code = True, candidate_code
                    break
                if gross > 0 and abs(tax / gross - rate) <= Decimal("0.001"):
                    inclusive, code = False, candidate_code
                    break
            if inclusive is None or code is None:
                raise ECFWorkflowError(
                    f"La tasa ITBIS real de la línea {index} no se puede inferir con precisión."
                )
            amount_indicators.add(1 if inclusive else 0)
            if supplied_code and supplied_code != str(code):
                raise ECFWorkflowError(
                    f"El indicador de facturación de la línea {index} no coincide con el ITBIS guardado."
                )
            values[code_key] = str(code)
            if discount:
                rate = {1: Decimal("0.18"), 2: Decimal("0.16")}[code]
                tax = _money(net * rate / (1 + rate) if inclusive else net * rate)
            base = net - tax if inclusive else net
            tax_by_code[code] += tax

        line_codes.append(code)
        base_by_code[code] += base
        line_gross.append(net)
        line_discounts.append(discount)
        line_tax.append(tax)
        values.update(
            {
                f"NumeroLinea[{index}]": str(index),
                f"TipoItem[{index}]": "1",
                f"NombreItem[{index}]": (detail.product.description or "")[:80],
                f"IndicadorBienoServicio[{index}]": "1",
                f"CantidadItem[{index}]": format(quantity.quantize(Decimal("0.01")), ".2f"),
                f"PrecioUnitarioItem[{index}]": format(price.quantize(Decimal("0.0001")), ".4f"),
                f"MontoItem[{index}]": _amount_text(net),
            }
        )
        if discount:
            values[f"DescuentoMonto[{index}]"] = _amount_text(discount)
        if detail.product.measure and detail.product.measure.isdigit():
            values[f"UnidadMedida[{index}]" if len(details) > 1 else "UnidadMedida[1]"] = detail.product.measure

    if len(amount_indicators) > 1:
        raise ECFWorkflowError(
            "La factura mezcla precios con y sin ITBIS; no se puede representar con un solo IndicadorMontoGravado."
        )
    amount_indicator = next(iter(amount_indicators), 0)
    if "IndicadorMontoGravado" in values and values["IndicadorMontoGravado"] != str(amount_indicator):
        raise ECFWorkflowError("IndicadorMontoGravado no coincide con los precios guardados.")
    values["IndicadorMontoGravado"] = str(amount_indicator)

    total_tax = sum(line_tax, Decimal("0"))
    if abs(_money(total_tax) - _money(Decimal(invoice.itbis))) > Decimal("0.02"):
        raise ECFWorkflowError("El ITBIS de las líneas no coincide con el ITBIS de la factura fuente.")
    if abs(sum(line_discounts, Decimal("0")) - _money(Decimal(invoice.discount))) > Decimal("0.02"):
        raise ECFWorkflowError("Los descuentos de las líneas no coinciden con el descuento de la factura fuente.")
    if abs(_money(sum(line_gross, Decimal("0")) + sum(line_discounts, Decimal("0"))) - _money(Decimal(invoice.subtotal))) > Decimal("0.02"):
        raise ECFWorkflowError("Las líneas e-CF no coinciden con el subtotal de la factura fuente.")

    taxable_base = sum((base_by_code[n] for n in (1, 2, 3)), Decimal("0"))
    expected_total = sum(line_gross, Decimal("0")) if amount_indicator == 1 else sum(line_gross, Decimal("0")) + total_tax
    if abs(_money(expected_total) - document_total) > Decimal("0.02"):
        raise ECFWorkflowError(
            "El total calculado con los precios e ITBIS no coincide con el total de la factura fuente."
        )

    for name in (
        "MontoGravadoTotal", "MontoGravadoI1", "MontoGravadoI2", "MontoGravadoI3",
        "MontoExento", "ITBIS1", "ITBIS2", "ITBIS3", "TotalITBIS",
        "TotalITBIS1", "TotalITBIS2", "TotalITBIS3", "MontoTotal",
    ):
        values.pop(name, None)
    if taxable_base:
        values["MontoGravadoTotal"] = _amount_text(taxable_base)
    for code in (1, 2, 3):
        if base_by_code[code]:
            values[f"MontoGravadoI{code}"] = _amount_text(base_by_code[code])
        if tax_by_code[code] or any(c == code for c in line_codes):
            values[f"ITBIS{code}"] = str({1: 18, 2: 16, 3: 0}[code])
            values[f"TotalITBIS{code}"] = _amount_text(tax_by_code[code])
    if base_by_code[4]:
        values["MontoExento"] = _amount_text(base_by_code[4])
    if total_tax:
        values["TotalITBIS"] = _amount_text(total_tax)
    values["MontoTotal"] = _amount_text(document_total)
    return values


def _apply_registered_issuer_identity(values: dict[str, str], company) -> None:
    """Replace fixture issuer identity with the company's registered data."""
    issuer_rnc = (company.rnc or "").strip()
    legal_name = (company.name or "").strip()
    address = (company.address or "").strip()
    if not issuer_rnc or not legal_name or not address:
        raise ECFWorkflowError(
            "Completa RNC, razón social y dirección reales de la empresa antes de generar el e-CF."
        )
    if len(address) > 100:
        raise ECFWorkflowError(
            "La dirección legal de la empresa excede el límite permitido para el e-CF."
        )

    values["RNCEmisor"] = issuer_rnc
    values["RazonSocialEmisor"] = legal_name
    values["DireccionEmisor"] = address
    if _is_valid_dgii_email(company.email):
        values["CorreoEmisor"] = company.email.strip()
    else:
        values.pop("CorreoEmisor", None)
    # Optional issuer data from a test sheet must not replace real Company data.
    optional_issuer_fields = {
        "NombreComercial", "Sucursal", "Municipio", "Provincia", "TelefonoEmisor",
        "WebSite", "ActividadEconomica", "InformacionAdicionalEmisor",
    }
    for key in list(values):
        if re.sub(r"\[\d+\]", "", str(key)).strip() in optional_issuer_fields:
            values.pop(key)
    phone = re.sub(r"\D", "", getattr(company, "phoneNumber", "") or "")
    if len(phone) == 10:
        values["TelefonoEmisor[1]"] = f"{phone[:3]}-{phone[3:6]}-{phone[6:]}"


def build_unsigned_xml(record: ElectronicInvoice) -> bytes:
    try:
        validate_production_record(record)
    except ValueError as exc:
        raise ECFWorkflowError(str(exc)) from exc
    if not record.encf or not record.sequence_id:
        raise ECFWorkflowError("Reserva primero un e-NCF para el borrador.")
    if not isinstance(record.payload, dict) or (not record.payload and not record.invoice_id):
        raise ECFWorkflowError("El borrador no contiene datos fiscales estructurados.")

    values = (
        _linked_sale_values(record)
        if record.document_type in {"31", "32"} and record.invoice_id
        else dict(record.payload)
    )
    configured_rnc = (record.company.rnc or "").strip()
    _apply_registered_issuer_identity(values, record.company)
    values.setdefault("Version", "1.0")
    values["TipoeCF"] = record.document_type
    values["eNCF"] = record.encf
    if record.environment == ECFEnvironment.PROD:
        if record.document_type not in {"32", "34"} and record.sequence.due_date:
            values["FechaVencimientoSecuencia"] = record.sequence.due_date.strftime("%d-%m-%Y")
        else:
            values.pop("FechaVencimientoSecuencia", None)
    values["FechaHoraFirma"] = datetime.now(
        ZoneInfo("America/Santo_Domingo")
    ).strftime("%d-%m-%Y %H:%M:%S")

    test_case = SimpleNamespace(
        values=values,
        tipo_ecf=record.document_type,
        encf=record.encf,
    )
    xml_data = build_ecf_xml(test_case, _xsd_for_record(record), validate=True)
    rnc, encf, document_type = _document_identity(xml_data)
    if configured_rnc and rnc != configured_rnc:
        raise ECFWorkflowError("El RNC emisor del XML no corresponde a la empresa.")
    if encf != record.encf or document_type != record.document_type:
        raise ECFWorkflowError("La identidad XML no coincide con el borrador reservado.")
    return xml_data


def sign_record(record: ElectronicInvoice) -> tuple[bytes, str]:
    if record.status != ElectronicInvoice.Status.DRAFT:
        raise ECFWorkflowError("Solo se pueden firmar documentos en borrador.")
    if not record.raw_xml:
        raise ECFWorkflowError("Genera y valida primero el XML sin firma.")

    raw_bytes = record.raw_xml.encode("utf-8")
    _validate_signed_company_identity(record, raw_bytes)

    config = _settings_for_record(record)
    company_rnc = (record.company.rnc or "").strip()

    rnc, encf, document_type = _document_identity(raw_bytes)
    if (rnc, encf, document_type) != (
        company_rnc,
        record.encf,
        record.document_type,
    ):
        raise ECFWorkflowError("La identidad del XML no coincide con el borrador.")

    try:
        certificate = load_pkcs12(config.certificate_path, config.certificate_password)
        signed_xml = sign_xml(raw_bytes, certificate)
        verify_xml_signature(signed_xml, certificate)
        validate_xsd(signed_xml, _xsd_for_record(record))
    except ECFError:
        raise
    except Exception as exc:
        raise ECFWorkflowError("No se pudo firmar y validar el e-CF.") from exc
    return signed_xml, hashlib.sha256(signed_xml).hexdigest()


def _validate_rfce_xml(xml_data: bytes, *, allow_unsigned: bool) -> None:
    xsd_path = project_path("xsd", "RFCE32V1.0.xsd")
    if not xsd_path.is_file():
        raise ECFWorkflowError("No está instalado el XSD DGII para RFCE tipo 32.")
    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    schema_doc = etree.parse(str(xsd_path), parser)
    for pattern in schema_doc.getroot().iter(f"{{{XSD_NS}}}pattern"):
        value = pattern.get("value")
        if value and "(?:" in value:
            pattern.set("value", value.replace("(?:", "("))
    if allow_unsigned:
        for any_node in schema_doc.getroot().iter(f"{{{XSD_NS}}}any"):
            any_node.set("minOccurs", "0")
    schema = etree.XMLSchema(schema_doc)
    root = etree.fromstring(xml_data, parser)
    schema.assertValid(root)


def build_rfce_from_signed_ecf(record: ElectronicInvoice) -> bytes:
    if record.document_type != "32" or not record.signed_xml:
        raise ECFWorkflowError("El RFCE requiere un e-CF tipo 32 firmado.")
    _validate_signed_company_identity(record, record.signed_xml.encode("utf-8"))
    if _document_identity(record.signed_xml.encode("utf-8")) != (
        (record.company.rnc or "").strip(),
        record.encf,
        "32",
    ):
        raise ECFWorkflowError("La identidad del e-CF firmado no coincide con el registro.")

    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    ecf_root = etree.fromstring(record.signed_xml.encode("utf-8"), parser)
    if etree.QName(ecf_root).localname != "ECF":
        raise ECFWorkflowError("El comprobante firmado asociado no tiene raíz ECF.")

    def text_at(parent, name):
        nodes = parent.xpath(f"./*[local-name()='{name}']") if parent is not None else []
        return (nodes[0].text or "").strip() if nodes else ""

    header = ecf_root.xpath("./*[local-name()='Encabezado']")
    if not header:
        raise ECFWorkflowError("El e-CF firmado no contiene Encabezado.")
    header = header[0]
    id_doc = header.xpath("./*[local-name()='IdDoc']")
    issuer = header.xpath("./*[local-name()='Emisor']")
    totals = header.xpath("./*[local-name()='Totales']")
    if not id_doc or not issuer or not totals:
        raise ECFWorkflowError("Faltan secciones requeridas para preparar el RFCE.")
    id_doc, issuer, totals = id_doc[0], issuer[0], totals[0]

    total = text_at(totals, "MontoTotal")
    try:
        total_amount = Decimal(total)
    except Exception as exc:
        raise ECFWorkflowError("El MontoTotal del e-CF no es válido para RFCE.") from exc
    if total_amount >= Decimal("250000"):
        raise ECFWorkflowError("El RFCE solo aplica a facturas de consumo menores de DOP 250,000.")
    if total_amount <= 0:
        raise ECFWorkflowError("El MontoTotal del e-CF debe ser positivo para crear el RFCE.")

    signatures = ecf_root.xpath(".//*[local-name()='SignatureValue']")
    if not signatures or not (signatures[0].text or "").strip():
        raise ECFWorkflowError("El e-CF firmado no contiene SignatureValue.")
    security_code = "".join(signatures[0].text.split())[:6]

    rfce_root = etree.Element("RFCE")
    encabezado = etree.SubElement(rfce_root, "Encabezado")
    etree.SubElement(encabezado, "Version").text = "1.0"

    rfce_id = etree.SubElement(encabezado, "IdDoc")
    for name in ("TipoeCF", "eNCF", "TipoIngresos", "TipoPago"):
        value = text_at(id_doc, name)
        if not value:
            raise ECFWorkflowError(f"El e-CF firmado no contiene {name}.")
        etree.SubElement(rfce_id, name).text = value

    rfce_issuer = etree.SubElement(encabezado, "Emisor")
    for name in ("RNCEmisor", "RazonSocialEmisor", "FechaEmision"):
        value = text_at(issuer, name)
        if not value:
            raise ECFWorkflowError(f"El e-CF firmado no contiene {name}.")
        etree.SubElement(rfce_issuer, name).text = value

    rfce_buyer = etree.SubElement(encabezado, "Comprador")
    buyer_sections = header.xpath("./*[local-name()='Comprador']")
    if buyer_sections:
        for name in ("RNCComprador", "IdentificadorExtranjero", "RazonSocialComprador"):
            value = text_at(buyer_sections[0], name)
            if value:
                etree.SubElement(rfce_buyer, name).text = value

    rfce_totals = etree.SubElement(encabezado, "Totales")
    total_fields = (
        "MontoGravadoTotal",
        "MontoGravadoI1",
        "MontoGravadoI2",
        "MontoGravadoI3",
        "MontoExento",
        "TotalITBIS",
        "TotalITBIS1",
        "TotalITBIS2",
        "TotalITBIS3",
        "MontoImpuestoAdicional",
        "MontoTotal",
        "MontoNoFacturable",
        "MontoPeriodo",
    )
    for name in total_fields:
        value = text_at(totals, name)
        if value:
            etree.SubElement(rfce_totals, name).text = value

    etree.SubElement(encabezado, "CodigoSeguridadeCF").text = security_code
    xml_data = etree.tostring(
        rfce_root,
        encoding="UTF-8",
        xml_declaration=True,
        pretty_print=True,
    )
    _validate_rfce_xml(xml_data, allow_unsigned=True)
    return xml_data


def sign_rfce_record(record: ElectronicInvoice) -> bytes:
    if record.rfce_status != RFCEStatus.DRAFT:
        raise ECFWorkflowError("Solo se puede firmar un RFCE en borrador.")
    if not record.rfce_xml:
        raise ECFWorkflowError("Genera y valida primero el XML RFCE.")
    config = _settings_for_record(record)
    try:
        certificate = load_pkcs12(config.certificate_path, config.certificate_password)
        signed_xml = sign_xml(record.rfce_xml.encode("utf-8"), certificate)
        verify_xml_signature(signed_xml, certificate)
        _validate_rfce_xml(signed_xml, allow_unsigned=False)
    except ECFError:
        raise
    except Exception as exc:
        raise ECFWorkflowError("No se pudo firmar y validar el RFCE.") from exc
    return signed_xml


def _rfce_registry_for_environment(environment: str) -> ECFTestRegistry:
    if environment == ECFEnvironment.PROD:
        return ECFTestRegistry(_production_registry_path(rfce=True))
    name = (
        "test_run_registry_cert_rfce.sqlite3"
        if environment == ECFEnvironment.CERT
        else "test_run_registry_rfce.sqlite3"
    )
    return ECFTestRegistry(project_path("test_data", "ecf", name))


def _certification_attempt_records(record):
    attempt = (record.payload or {}).get("certification_attempt")
    if not attempt:
        return None
    if record.environment != ECFEnvironment.CERT:
        raise ECFWorkflowError("Los casos de certificación DGII solo se envían en el ambiente cert.")
    return ElectronicInvoice.objects.filter(
        company_id=record.company_id,
        environment=record.environment,
        payload__certification_attempt=attempt,
    )


def _accepted_type_count(records, document_type: str) -> int:
    accepted = records.filter(
        document_type=document_type,
        status=ElectronicInvoice.Status.ACCEPTED,
    )
    if document_type != "32":
        return accepted.count()

    # Only type-32 invoices at or above RD$250,000 belong to the ordered
    # direct-send group; the smaller invoices are portal uploads after RFCE.
    count = 0
    for item in accepted.only("signed_xml"):
        try:
            root = etree.fromstring(
                item.signed_xml.encode("utf-8"),
                etree.XMLParser(resolve_entities=False, no_network=True),
            )
            total = root.xpath(".//*[local-name()='MontoTotal']")
            if total and Decimal(total[0].text or "0") >= Decimal("250000"):
                count += 1
        except (AttributeError, UnicodeEncodeError, etree.XMLSyntaxError, ArithmeticError):
            continue
    return count


def _require_previous_certification_groups(record) -> None:
    records = _certification_attempt_records(record)
    if records is None:
        return
    if record.document_type not in CERTIFICATION_SEND_ORDER:
        raise ECFWorkflowError("El tipo e-CF no pertenece al orden de simulación DGII.")
    for previous_type in CERTIFICATION_SEND_ORDER[:CERTIFICATION_SEND_ORDER.index(record.document_type)]:
        accepted = _accepted_type_count(records, previous_type)
        expected = CERTIFICATION_EXPECTED_COUNTS[previous_type]
        if accepted != expected:
            raise ECFWorkflowError(
                f"Envío detenido por orden DGII: tipo {previous_type} aceptado "
                f"{accepted}/{expected}; complétalo antes del tipo {record.document_type}."
            )
    current_accepted = _accepted_type_count(records, record.document_type)
    current_expected = CERTIFICATION_EXPECTED_COUNTS[record.document_type]
    if current_accepted >= current_expected:
        raise ECFWorkflowError(
            f"Envío detenido por límite de simulación DGII: el tipo {record.document_type} "
            f"ya tiene {current_accepted}/{current_expected} comprobantes aceptados."
        )


def _require_primary_groups_before_rfce(record) -> None:
    records = _certification_attempt_records(record)
    if records is None:
        return
    for document_type in CERTIFICATION_SEND_ORDER:
        accepted = _accepted_type_count(records, document_type)
        expected = CERTIFICATION_EXPECTED_COUNTS[document_type]
        if accepted != expected:
            raise ECFWorkflowError(
                f"Envío RFCE detenido por orden DGII: tipo {document_type} aceptado "
                f"{accepted}/{expected}; complétalo antes de enviar los RFCE."
            )


def send_rfce_record(record: ElectronicInvoice) -> RFCEReceipt:
    if record.document_type != "32" or record.status != ElectronicInvoice.Status.READY:
        raise ECFWorkflowError("El RFCE requiere un e-CF tipo 32 firmado y listo.")
    if record.rfce_status != RFCEStatus.READY or not record.signed_rfce_xml:
        raise ECFWorkflowError("Genera y firma el RFCE antes de enviarlo.")
    signed_rfce = record.signed_rfce_xml.encode("utf-8")
    signed_ecf = record.signed_xml.encode("utf-8")
    _validate_signed_company_identity(record, signed_ecf)
    _require_primary_groups_before_rfce(record)

    config = _settings_for_record(record)
    if not record.xml_hash or not hmac.compare_digest(
        hashlib.sha256(signed_ecf).hexdigest(), record.xml_hash
    ):
        raise ECFWorkflowError("El hash del e-CF firmado asociado no coincide con el registro.")
    if _document_identity(signed_ecf) != (
        (record.company.rnc or "").strip(), record.encf, "32"
    ):
        raise ECFWorkflowError("La identidad del e-CF firmado asociado no coincide con el registro.")
    try:
        certificate = load_pkcs12(config.certificate_path, config.certificate_password)
        verify_xml_signature(signed_ecf, certificate)
        validate_xsd(signed_ecf, _xsd_for_record(record))
        verify_xml_signature(signed_rfce, certificate)
        _validate_rfce_xml(signed_rfce, allow_unsigned=False)
        rfce_root = etree.fromstring(
            signed_rfce, etree.XMLParser(resolve_entities=False, no_network=True)
        )
        if etree.QName(rfce_root).localname != "RFCE":
            raise ECFWorkflowError("El XML firmado asociado no tiene raíz RFCE.")
        rfce_encfs = rfce_root.xpath(".//*[local-name()='eNCF']")
        rfce_rncs = rfce_root.xpath(".//*[local-name()='RNCEmisor']")
        rfce_types = rfce_root.xpath(".//*[local-name()='TipoeCF']")
        if (
            not rfce_encfs or (rfce_encfs[0].text or "").strip() != record.encf
            or not rfce_rncs or (rfce_rncs[0].text or "").strip() != (record.company.rnc or "").strip()
            or not rfce_types or (rfce_types[0].text or "").strip() != "32"
        ):
            raise ECFWorkflowError("La identidad del RFCE firmado no coincide con el e-CF asociado.")
        rfce_totals = rfce_root.xpath(".//*[local-name()='MontoTotal']")
        if not rfce_totals or Decimal(rfce_totals[0].text or "0") >= Decimal("250000"):
            raise ECFWorkflowError("El RFCE firmado no corresponde a un consumo menor de DOP 250,000.")
        ecf_signature = etree.fromstring(
            signed_ecf, etree.XMLParser(resolve_entities=False, no_network=True)
        ).xpath(".//*[local-name()='SignatureValue']")
        rfce_codes = rfce_root.xpath(".//*[local-name()='CodigoSeguridadeCF']")
        expected_security_code = "".join(ecf_signature[0].text.split())[:6] if ecf_signature else ""
        if not rfce_codes or (rfce_codes[0].text or "").strip() != expected_security_code:
            raise ECFWorkflowError("El código de seguridad del RFCE no corresponde al e-CF firmado.")
        token = DGIIAuthenticator(config, certificate).authenticate().token
    except ECFWorkflowError:
        raise
    except Exception as exc:
        raise ECFWorkflowError("No se pudo verificar el RFCE firmado o autenticar con DGII.") from exc

    rnc = (record.company.rnc or "").strip()
    registry = _rfce_registry_for_environment(record.environment)
    registry.reserve_send(
        rnc=rnc,
        encf=record.encf,
        case_id=f"api-rfce-{record.pk}",
        tipo_ecf="RFCE-32",
        signed_xml=signed_rfce,
    )
    record.rfce_status = RFCEStatus.SENDING
    record.save(update_fields=("rfce_status", "updated_at"))

    try:
        receipt = DGIIRFCEClient(
            environment=record.environment,
            timeout_seconds=config.request_timeout_seconds,
        ).send_rfce(
            signed_xml=signed_rfce,
            token=token,
            filename=f"{rnc}{record.encf}.xml",
        )
    except Exception as exc:
        record.rfce_status = RFCEStatus.UNCERTAIN
        record.rfce_status_text = "Resultado de recepción incierto; conciliar antes de reintentar."
        record.rfce_resolved_at = datetime.now().astimezone()
        record.save(
            update_fields=("rfce_status", "rfce_status_text", "rfce_resolved_at", "updated_at")
        )
        raise ECFWorkflowError(record.rfce_status_text) from exc

    if receipt.encf and receipt.encf != record.encf:
        record.rfce_status = RFCEStatus.UNCERTAIN
        record.rfce_status_text = "DGII devolvió un e-NCF RFCE distinto; concilia antes de continuar."
        record.rfce_code = receipt.code
        record.rfce_messages = [
            {"codigo": message.code, "valor": message.value}
            for message in receipt.messages
        ]
        record.rfce_sequence_used = receipt.sequence_used
        record.rfce_sent_at = datetime.now().astimezone()
        record.rfce_resolved_at = record.rfce_sent_at
        record.save(update_fields=(
            "rfce_status", "rfce_status_text", "rfce_code", "rfce_messages",
            "rfce_sequence_used", "rfce_sent_at", "rfce_resolved_at", "updated_at",
        ))
        registry.mark_result(
            rnc=rnc, encf=record.encf, code=None, status="Respuesta e-NCF no coincide",
            sequence_used=receipt.sequence_used, notes=record.rfce_status_text,
        )
        raise ECFWorkflowError(record.rfce_status_text)

    normalized = receipt.status.strip().casefold()
    if normalized == "aceptado":
        record.rfce_status = RFCEStatus.ACCEPTED
    elif normalized == "aceptado condicional":
        record.rfce_status = RFCEStatus.ACCEPTED_CONDITIONAL
    elif normalized:
        record.rfce_status = RFCEStatus.REJECTED
    else:
        record.rfce_status = RFCEStatus.UNCERTAIN
    record.rfce_code = receipt.code
    record.rfce_status_text = receipt.status
    record.rfce_messages = [
        {"codigo": message.code, "valor": message.value}
        for message in receipt.messages
    ]
    record.rfce_sequence_used = receipt.sequence_used
    record.rfce_sent_at = datetime.now().astimezone()
    record.rfce_resolved_at = record.rfce_sent_at
    record.save(
        update_fields=(
            "rfce_status",
            "rfce_code",
            "rfce_status_text",
            "rfce_messages",
            "rfce_sequence_used",
            "rfce_sent_at",
            "rfce_resolved_at",
            "updated_at",
        )
    )
    registry.mark_result(
        rnc=rnc,
        encf=record.encf,
        code=receipt.code,
        status=receipt.status,
        sequence_used=receipt.sequence_used,
        notes="; ".join(message.value for message in receipt.messages if message.value) or None,
    )
    if record.environment == ECFEnvironment.PROD:
        # Production consumption <250,000 is resolved by the RFCE service;
        # uploading the full e-CF in the certification portal is not required.
        record.status = {
            RFCEStatus.ACCEPTED: ElectronicInvoice.Status.ACCEPTED,
            RFCEStatus.ACCEPTED_CONDITIONAL: ElectronicInvoice.Status.ACCEPTED_CONDITIONAL,
            RFCEStatus.REJECTED: ElectronicInvoice.Status.REJECTED,
        }.get(record.rfce_status, ElectronicInvoice.Status.UNCERTAIN)
        record.dgii_code = receipt.code
        record.dgii_status = receipt.status
        record.dgii_messages = record.rfce_messages
        record.sent_at = record.rfce_sent_at
        record.resolved_at = record.rfce_resolved_at
        record.save(update_fields=("status", "dgii_code", "dgii_status", "dgii_messages", "sent_at", "resolved_at", "updated_at"))
        try:
            link_accepted_sale(record)
        except ValueError as exc:
            raise ECFWorkflowError(str(exc)) from exc
    return receipt


def _production_registry_path(*, rfce=False) -> Path:
    # Keep transport state out of MEDIA_ROOT, which may be served by Nginx.
    folder = Path(os.getenv("ECF_PRODUCTION_REGISTRY_DIR", str(project_path("private_ecf_state"))))
    if not folder.is_absolute():
        raise ECFWorkflowError("ECF_PRODUCTION_REGISTRY_DIR debe ser una ruta absoluta privada.")
    return folder / ("registry-rfce-prod.sqlite3" if rfce else "registry-prod.sqlite3")


def _registry_for_environment(environment: str) -> ECFTestRegistry:
    if environment == ECFEnvironment.PROD:
        return ECFTestRegistry(_production_registry_path())
    name = (
        "test_run_registry_cert.sqlite3"
        if environment == ECFEnvironment.CERT
        else "test_run_registry.sqlite3"
    )
    return ECFTestRegistry(project_path("test_data", "ecf", name))


def registries_for_environment(
    environment: str,
    document_type: str,
) -> list[ECFTestRegistry]:
    registries = [_registry_for_environment(environment)]
    if document_type == "32":
        if environment == ECFEnvironment.PROD:
            rfce_path = _production_registry_path(rfce=True)
            if rfce_path.is_file():
                registries.append(ECFTestRegistry(rfce_path))
            return registries
        rfce_name = (
            "test_run_registry_cert_rfce.sqlite3"
            if environment == ECFEnvironment.CERT
            else "test_run_registry_rfce.sqlite3"
        )
        rfce_path = project_path("test_data", "ecf", rfce_name)
        if rfce_path.is_file():
            registries.append(ECFTestRegistry(rfce_path))
    return registries


def used_encfs_for_company(company_rnc: str) -> set[str]:
    """Read every existing local certification registry without modifying it."""
    rnc = (company_rnc or "").strip()
    if not rnc:
        raise ECFWorkflowError("La empresa no tiene RNC configurado.")

    used: set[str] = set()
    registry_dir = project_path("test_data", "ecf")
    for db_path in registry_dir.glob("test_run_registry*.sqlite3"):
        uri = f"file:{db_path.as_posix()}?mode=ro"
        try:
            with sqlite3.connect(uri, uri=True) as db:
                tables = {
                    row[0]
                    for row in db.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    )
                }
                if "ecf_test_runs" in tables:
                    used.update(
                        row[0]
                        for row in db.execute(
                            "SELECT encf FROM ecf_test_runs WHERE rnc=? AND encf IS NOT NULL",
                            (rnc,),
                        )
                    )
                if "ecf_test_run_history" in tables:
                    for (record_json,) in db.execute(
                        "SELECT record_json FROM ecf_test_run_history"
                    ):
                        try:
                            entry = json.loads(record_json)
                        except (TypeError, ValueError):
                            continue
                        if entry.get("rnc") == rnc and entry.get("encf"):
                            used.add(str(entry["encf"]))
        except sqlite3.Error as exc:
            raise ECFWorkflowError(
                f"No se pudo conciliar el registro de secuencias {db_path.name}."
            ) from exc
    return used


def send_record(record: ElectronicInvoice) -> ReceptionResponse:
    if record.status != ElectronicInvoice.Status.READY or not record.signed_xml:
        raise ECFWorkflowError("El e-CF debe estar firmado y listo antes del envío.")

    signed_xml = record.signed_xml.encode("utf-8")
    _validate_signed_company_identity(record, signed_xml)

    config = _settings_for_record(record)
    if not record.xml_hash or not hmac.compare_digest(
        hashlib.sha256(signed_xml).hexdigest(), record.xml_hash
    ):
        raise ECFWorkflowError("El hash del XML firmado no coincide con el registro; no se enviará.")
    rnc, encf, document_type = _document_identity(signed_xml)
    if (rnc, encf, document_type) != (
        (record.company.rnc or "").strip(),
        record.encf,
        record.document_type,
    ):
        raise ECFWorkflowError("La identidad del XML firmado no coincide con el registro.")
    _require_previous_certification_groups(record)

    # Small consumer invoices must be preceded by an accepted RFCE.
    if document_type == "32":
        root = etree.fromstring(
            signed_xml,
            etree.XMLParser(resolve_entities=False, no_network=True),
        )
        total_nodes = root.xpath(".//*[local-name()='MontoTotal']")
        if total_nodes and Decimal(total_nodes[0].text or "0") < Decimal("250000"):
            if record.environment == ECFEnvironment.PROD:
                raise ECFWorkflowError("Para consumo menor de DOP 250,000 envía el RFCE firmado.")
            raise ECFWorkflowError(
                "El e-CF tipo 32 menor de DOP 250,000 se carga en el portal DGII después de aceptar su RFCE; descarga el XML firmado."
            )
    if document_type in {"31", "32"}:
        root = etree.fromstring(
            signed_xml,
            etree.XMLParser(resolve_entities=False, no_network=True),
        )
        buyer_id = root.xpath(
            ".//*[local-name()='RNCComprador' or local-name()='IdentificadorExtranjero']"
        )
        if document_type == "31" and not buyer_id:
            raise ECFWorkflowError("El e-CF tipo 31 debe identificar al comprador.")
        if document_type == "32":
            total_nodes = root.xpath(".//*[local-name()='MontoTotal']")
            if total_nodes and Decimal(total_nodes[0].text or "0") >= Decimal("250000") and not buyer_id:
                raise ECFWorkflowError(
                    "El e-CF tipo 32 de DOP 250,000 o más debe identificar al comprador."
                )

    if document_type in {"33", "34"}:
        root = etree.fromstring(
            signed_xml,
            etree.XMLParser(resolve_entities=False, no_network=True),
        )
        references = root.xpath(".//*[local-name()='NCFModificado']")
        reference = (references[0].text or "").strip() if references else ""
        if not reference:
            raise ECFWorkflowError("La nota e-CF debe referenciar un comprobante modificado.")
        if record.environment == ECFEnvironment.PROD:
            from sales.models import InvoicesHeader
            accepted_reference = ElectronicInvoice.objects.filter(
                company_id=record.company_id, environment="prod", encf=reference,
                status__in=(ElectronicInvoice.Status.ACCEPTED, ElectronicInvoice.Status.ACCEPTED_CONDITIONAL),
            ).exists()
            legacy_reference = reference.startswith("B") and InvoicesHeader.objects.filter(
                company_id=record.company_id, ncf=reference, invoiceStatus="",
            ).exists()
            if not accepted_reference and not legacy_reference:
                raise ECFWorkflowError("La nota debe referenciar un comprobante real de esta empresa, aceptado o tradicional registrado.")
        else:
            _registry_for_environment(record.environment).require_accepted_reference(rnc=rnc, encf=reference)

    try:
        certificate = load_pkcs12(config.certificate_path, config.certificate_password)
        verify_xml_signature(signed_xml, certificate)
        validate_xsd(signed_xml, _xsd_for_record(record))
        authenticator = DGIIAuthenticator(config, certificate)
        token = authenticator.authenticate().token
    except Exception as exc:
        if isinstance(exc, ECFWorkflowError):
            raise
        raise ECFWorkflowError("No se pudo verificar el XML firmado o autenticar con DGII.") from exc
    registry = _registry_for_environment(record.environment)
    registry.reserve_send(
        rnc=rnc,
        encf=encf,
        case_id=f"api-electronic-invoice-{record.pk}",
        tipo_ecf=document_type,
        signed_xml=signed_xml,
    )

    client = DGIIReceptionClient(
        config.reception_base_url,
        config.result_base_url,
        config.request_timeout_seconds,
    )
    try:
        receipt = client.send_ecf(
            signed_xml=signed_xml,
            token=token,
            filename=f"{rnc}{encf}.xml",
        )
    except Exception as exc:
        record.status = ElectronicInvoice.Status.UNCERTAIN
        record.last_error = (
            "DGII no confirmó el envío; concilia el e-NCF y el registro de recepción "
            "antes de cualquier reintento."
        )
        record.save(update_fields=("status", "last_error", "updated_at"))
        raise ECFWorkflowError(record.last_error) from exc

    if not receipt.track_id:
        record.status = ElectronicInvoice.Status.UNCERTAIN
        record.last_error = receipt.error or receipt.message or (
            "DGII no devolvió TrackId; concilia antes de reintentar."
        )
        record.save(update_fields=("status", "last_error", "updated_at"))
        raise ECFWorkflowError(record.last_error)

    registry.mark_submitted(rnc=rnc, encf=encf, track_id=receipt.track_id)
    record.track_id = receipt.track_id
    record.status = ElectronicInvoice.Status.SUBMITTED
    record.sent_at = datetime.now().astimezone()
    record.last_error = ""
    record.save(
        update_fields=("track_id", "status", "sent_at", "last_error", "updated_at")
    )
    return receipt


def query_record_result(record: ElectronicInvoice) -> ECFResult:
    if not record.track_id or record.status not in {
        ElectronicInvoice.Status.SUBMITTED,
        ElectronicInvoice.Status.PROCESSING,
        ElectronicInvoice.Status.UNCERTAIN,
    }:
        raise ECFWorkflowError("El registro no tiene un TrackId pendiente de consulta.")

    config = _settings_for_record(record, require_range=False)
    try:
        certificate = load_pkcs12(config.certificate_path, config.certificate_password)
        token = DGIIAuthenticator(config, certificate).authenticate().token
        result = DGIIReceptionClient(
            config.reception_base_url,
            config.result_base_url,
            config.request_timeout_seconds,
        ).get_result(record.track_id, token)
    except Exception as exc:
        raise ECFWorkflowError("No se pudo consultar el estado en DGII.") from exc

    if result.rnc and result.rnc != (record.company.rnc or "").strip():
        raise ECFWorkflowError("El RNC de la respuesta DGII no coincide con el documento.")
    if result.encf and result.encf != record.encf:
        raise ECFWorkflowError("El e-NCF de la respuesta DGII no coincide con el documento.")

    status_by_code = {
        1: ElectronicInvoice.Status.ACCEPTED,
        2: ElectronicInvoice.Status.REJECTED,
        3: ElectronicInvoice.Status.PROCESSING,
        4: ElectronicInvoice.Status.ACCEPTED_CONDITIONAL,
    }
    record.status = status_by_code.get(result.code, ElectronicInvoice.Status.UNCERTAIN)
    record.dgii_code = result.code
    record.dgii_status = result.status
    record.dgii_messages = result.messages or []
    record.resolved_at = datetime.now().astimezone()
    record.last_error = ""
    record.save(
        update_fields=(
            "status",
            "dgii_code",
            "dgii_status",
            "dgii_messages",
            "resolved_at",
            "last_error",
            "updated_at",
        )
    )

    _registry_for_environment(record.environment).mark_result(
        rnc=(record.company.rnc or "").strip(),
        encf=record.encf,
        code=result.code,
        status=result.status,
        sequence_used=result.sequence_used,
        notes="; ".join(
            str(message.get("valor", ""))
            for message in result.messages
            if isinstance(message, dict) and message.get("valor")
        ) or None,
    )
    try:
        link_accepted_sale(record)
    except ValueError as exc:
        raise ECFWorkflowError(str(exc)) from exc
    return result


def _validate_ri_issuer_identity(
    record: ElectronicInvoice,
    issuer_name: str,
    issuer_rnc: str,
    issuer_address: str,
    requested_identity: dict[str, str] | None = None,
) -> None:
    company = record.company
    registered_identity = {
        "name": (company.name or "").strip(),
        "rnc": (company.rnc or "").strip(),
        "address": (company.address or "").strip(),
    }
    signed_identity = {
        "name": issuer_name.strip(),
        "rnc": issuer_rnc.strip(),
        "address": issuer_address.strip(),
    }
    if not all(registered_identity.values()) or signed_identity != registered_identity:
        raise ECFWorkflowError(
            "La identidad del XML firmado no coincide con la razón social, RNC y dirección "
            "registrados de la empresa. Se requiere un e-CF nuevo firmado con los datos reales."
        )
    if requested_identity is not None and {
        "name": requested_identity.get("name", "").strip(),
        "address": requested_identity.get("address", "").strip(),
    } != {"name": registered_identity["name"], "address": registered_identity["address"]}:
        raise ECFWorkflowError(
            "No se permite sustituir la identidad legal en la representación impresa."
        )


def _validate_signed_company_identity(
    record: ElectronicInvoice,
    xml_data: bytes,
) -> None:
    try:
        root = etree.fromstring(
            xml_data,
            etree.XMLParser(resolve_entities=False, no_network=True),
        )
    except etree.XMLSyntaxError as exc:
        raise ECFWorkflowError("El XML no tiene una estructura válida para verificar el emisor.") from exc
    issuers = root.xpath("./*[local-name()='Encabezado']/*[local-name()='Emisor']")
    if not issuers:
        raise ECFWorkflowError("El XML no contiene la sección Emisor requerida.")

    def value(name: str) -> str:
        nodes = issuers[0].xpath(f"./*[local-name()='{name}']")
        return (nodes[0].text or "").strip() if nodes else ""

    _validate_ri_issuer_identity(
        record,
        value("RazonSocialEmisor"),
        value("RNCEmisor"),
        value("DireccionEmisor"),
    )


def representation_pdf_identity_is_current(record: ElectronicInvoice) -> bool:
    """Return whether the signed e-CF issuer matches the current legal Company record."""
    if record.environment != ECFEnvironment.CERT:
        return True
    if not record.signed_xml:
        return False
    try:
        root = etree.fromstring(
            record.signed_xml.encode("utf-8"),
            etree.XMLParser(resolve_entities=False, no_network=True),
        )
        issuers = root.xpath("./*[local-name()='Encabezado']/*[local-name()='Emisor']")
        if not issuers:
            return False

        def value(name):
            nodes = issuers[0].xpath(f"./*[local-name()='{name}']")
            return (nodes[0].text or "").strip() if nodes else ""

        _validate_ri_issuer_identity(
            record,
            value("RazonSocialEmisor"),
            value("RNCEmisor"),
            value("DireccionEmisor"),
        )
    except (ECFWorkflowError, etree.XMLSyntaxError, UnicodeEncodeError):
        return False
    return True


def build_representation_pdf(
    record: ElectronicInvoice,
    *,
    registered_issuer: dict[str, str] | None = None,
) -> bytes:
    """Render an RI from signed transaction data without changing signed issuer data."""
    if record.status not in {
        ElectronicInvoice.Status.ACCEPTED,
        ElectronicInvoice.Status.ACCEPTED_CONDITIONAL,
    }:
        raise ECFWorkflowError("La RI solo se genera para e-CF recibidos por DGII.")
    if not record.signed_xml:
        raise ECFWorkflowError("El registro no conserva el XML firmado.")

    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    root = etree.fromstring(record.signed_xml.encode("utf-8"), parser)

    def find_text(parent, name, default=""):
        nodes = parent.xpath(f".//*[local-name()='{name}']") if parent is not None else []
        return (nodes[0].text or "").strip() if nodes else default

    header_nodes = root.xpath("./*[local-name()='Encabezado']")
    if not header_nodes:
        raise ECFWorkflowError("El XML firmado no contiene Encabezado.")
    header = header_nodes[0]
    issuer_nodes = header.xpath("./*[local-name()='Emisor']")
    buyer_nodes = header.xpath("./*[local-name()='Comprador']")
    totals_nodes = header.xpath("./*[local-name()='Totales']")
    details_nodes = root.xpath("./*[local-name()='DetallesItems']/*[local-name()='Item']")
    if not issuer_nodes or not totals_nodes:
        raise ECFWorkflowError("El XML firmado no contiene emisor y totales.")
    issuer = issuer_nodes[0]
    buyer = buyer_nodes[0] if buyer_nodes else None
    totals = totals_nodes[0]
    signature_values = root.xpath(".//*[local-name()='SignatureValue']")
    if not signature_values or not (signature_values[0].text or "").strip():
        raise ECFWorkflowError("El XML firmado no contiene SignatureValue.")
    security_code = "".join(signature_values[0].text.split())[:6]
    if len(security_code) != 6:
        raise ECFWorkflowError("El código de seguridad del XML firmado no tiene seis caracteres.")

    issuer_rnc = find_text(issuer, "RNCEmisor")
    if record.environment == ECFEnvironment.CERT:
        _validate_ri_issuer_identity(
            record,
            find_text(issuer, "RazonSocialEmisor"),
            issuer_rnc,
            find_text(issuer, "DireccionEmisor"),
            registered_issuer,
        )
    elif registered_issuer is not None:
        signed_identity = {
            "name": find_text(issuer, "RazonSocialEmisor"),
            "address": find_text(issuer, "DireccionEmisor"),
        }
        if {
            "name": registered_issuer.get("name", "").strip(),
            "address": registered_issuer.get("address", "").strip(),
        } != signed_identity:
            raise ECFWorkflowError(
                "No se permite sustituir la identidad legal en la representación impresa."
            )
    buyer_rnc = find_text(buyer, "RNCComprador")
    encf = find_text(header, "eNCF")
    emission_date = find_text(issuer, "FechaEmision")
    signed_date = find_text(root, "FechaHoraFirma")
    total = find_text(totals, "MontoTotal")
    if not all((issuer_rnc, encf, emission_date, signed_date, total)):
        raise ECFWorkflowError("Faltan datos obligatorios del encabezado para la RI.")

    total_value = Decimal(total)
    qr_url = _representation_qr_url(
        record,
        issuer_rnc=issuer_rnc,
        buyer_rnc=buyer_rnc,
        encf=encf,
        emission_date=emission_date,
        signed_date=signed_date,
        total=total_value,
        security_code=security_code,
    )

    # ReportLab and qrcode are declared runtime requirements for this endpoint.
    import qrcode
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen.canvas import Canvas
    from reportlab.platypus import BaseDocTemplate, Flowable, Frame, Image, PageTemplate, Paragraph, Spacer, Table, TableStyle

    buffer = BytesIO()
    doc = BaseDocTemplate(
        buffer, pagesize=letter, rightMargin=18 * mm, leftMargin=20 * mm,
        topMargin=16 * mm, bottomMargin=54 * mm,
        title=f"Representación impresa {encf}",
    )
    styles = getSampleStyleSheet()
    styles["Normal"].fontSize = 8
    styles["Normal"].leading = 10
    rule_color = colors.HexColor("#3a8bc4")
    heading_color = "#205677"
    styles.add(ParagraphStyle(name="RIRight", parent=styles["Normal"], alignment=TA_RIGHT))
    styles.add(ParagraphStyle(name="RICenter", parent=styles["Normal"], alignment=TA_CENTER))
    story = []
    type_label = ECF_TYPE_LABELS.get(record.document_type, "Comprobante Fiscal Electrónico")

    issuer_name = html_escape(find_text(issuer, "RazonSocialEmisor"))
    trade_name = html_escape(find_text(issuer, "NombreComercial"))
    issuer_address = html_escape(find_text(issuer, "DireccionEmisor"))
    issuer_municipality = html_escape(find_text(issuer, "Municipio"))
    issuer_province = html_escape(find_text(issuer, "Provincia"))
    branch_name = html_escape(find_text(issuer, "Sucursal"))
    municipality_names = {
        "010100": "Santo Domingo de Guzmán",
        "010101": "Santo Domingo de Guzmán (D. M.)",
    }
    province_names = {"010000": "Distrito Nacional"}
    if issuer_municipality:
        issuer_municipality = municipality_names.get(
            issuer_municipality, f"Municipio (código {issuer_municipality})"
        )
    if issuer_province:
        issuer_province = province_names.get(
            issuer_province, f"Provincia (código {issuer_province})"
        )
    buyer_name = html_escape(find_text(buyer, "RazonSocialComprador"))
    expiry = find_text(header, "FechaVencimientoSecuencia")
    modified_encf = find_text(root, "NCFModificado")
    modification_code = find_text(root, "CodigoModificacion")
    modified_desc = {
        "1": "Anula el comprobante modificado",
        "2": "Corrige el texto del comprobante modificado",
        "3": "Corrige los montos del comprobante modificado",
        "4": "Reemplaza un comprobante emitido en contingencia",
    }.get(modification_code, "")
    if record.document_type == "33" and modification_code == "3":
        modified_desc = "Corrige montos del NCF modificado"
    issuer_location = " · ".join(value for value in (issuer_municipality, issuer_province) if value)
    issuer_header = "<br/>".join(
        value for value in (
            f'<b><font color="{heading_color}">{trade_name}</font></b>' if trade_name else "",
            issuer_name if issuer_name else "",
            f"Sucursal: {branch_name}" if branch_name else "",
            f"RNC {issuer_rnc}", f"Dirección: {issuer_address}", issuer_location,
            f"<b>Fecha Emisión:</b> {emission_date}",
        ) if value
    )
    buyer_identifier = buyer_rnc or find_text(buyer, "IdentificadorExtranjero")
    buyer_header = "" if record.document_type == "32" else "<br/>".join(value for value in (
        f"<b>Razón Social Cliente:</b> {buyer_name}" if buyer_name else "",
        f"<b>RNC Cliente:</b> {html_escape(buyer_identifier)}" if buyer_identifier else "",
    ) if value)
    issuer_block = [Paragraph(issuer_header, styles["Normal"])]
    logo_space = 0
    # Assets are keyed by the signed issuer RNC, so another company cannot
    # inherit this branding. Keep the backend independent of the React folder.
    logo_path = project_path("ecf", "assets", f"{issuer_rnc}.png")
    if logo_path.is_file():
        logo_width, logo_height = ImageReader(str(logo_path)).getSize()
        logo_space = 22 * mm * logo_height / logo_width + 2 * mm
        logo = Image(str(logo_path), width=22 * mm, height=22 * mm * logo_height / logo_width)
        logo.hAlign = "LEFT"
        issuer_block = [logo, Spacer(1, 2 * mm), *issuer_block]
    doc_fields = [
        [issuer_block,
         [Spacer(1, logo_space), Paragraph(f'<b><font color="{heading_color}" size="10">{html_escape(type_label)}</font></b><br/><b>e-NCF:</b> {encf}<br/>' + (f"<b>Fecha Vencimiento:</b> {expiry}<br/>" if expiry and record.document_type != "33" else "") + (f"<b>NCF Modificado:</b> {html_escape(modified_encf)}<br/>" if record.document_type == "33" and modified_encf else f"<b>e-NCF modificado:</b> {html_escape(modified_encf)}<br/>" if modified_encf else "") + (f"<b>{html_escape(modified_desc)}</b><br/>" if record.document_type == "33" and modified_desc else f"<b>Modificación:</b> {modification_code} {modified_desc}<br/>" if modification_code or modified_desc else ""), styles["RIRight"])]],
    ]
    if buyer_header:
        doc_fields.append([Paragraph(buyer_header, styles["Normal"]), ""])
    header_table = Table(doc_fields, colWidths=[95 * mm, 82 * mm])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, 0), 1.2, rule_color),
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    if buyer_header:
        header_table.setStyle(TableStyle([
            ("SPAN", (0, 1), (1, 1)),
            ("LINEBELOW", (0, 1), (-1, 1), 1.2, rule_color),
            ("TOPPADDING", (0, 1), (-1, 1), 10),
        ]))
    # Reserve the same header space on every page, as in DGII's paginated model.
    _, header_height = header_table.wrap(doc.width, doc.height)
    doc.topMargin = 16 * mm + header_height + 4 * mm

    table_header_style = ParagraphStyle(
        name="RITableHeader", parent=styles["Normal"], fontSize=7, leading=8,
        alignment=TA_CENTER, fontName="Helvetica-Bold",
    )
    table_cell_style = ParagraphStyle(
        name="RITableCell", parent=styles["Normal"], fontSize=7, leading=8,
    )
    rows = [[
        Paragraph("Cantidad", table_header_style),
        Paragraph("Descripción", table_header_style),
        Paragraph("Unidad de<br/>Medida", table_header_style),
        Paragraph("Precio", table_header_style),
        Paragraph("ITBIS", table_header_style),
        Paragraph("Valor", table_header_style),
    ]]
    for item in details_nodes:
        quantity = find_text(item, "CantidadItem")
        description = html_escape(find_text(item, "NombreItem"))
        if find_text(item, "IndicadorFacturacion") == "4":
            description = "E " + description
        alcohol = find_text(item, "GradosAlcohol")
        reference_price = find_text(item, "PrecioUnitarioReferencia")
        if alcohol:
            description += f"<br/>Grados alcohol: {html_escape(alcohol)}%"
        if reference_price:
            description += f"<br/>PVP: {html_escape(reference_price)}"
        unit_code = find_text(item, "UnidadMedida")
        unit = ECF_UNIT_LABELS.get(unit_code, unit_code)
        unit = html_escape(unit)
        price = find_text(item, "PrecioUnitarioItem")
        tax = find_text(item, "MontoITBIS") or find_text(item, "SubTotaITBIS")
        if not tax:
            tax_parts = [find_text(item, f"SubTotaITBIS{rate}") for rate in (1, 2, 3)]
            tax = _amount_text(sum((Decimal(value) for value in tax_parts if value), Decimal("0"))) if any(tax_parts) else ""
        amount = find_text(item, "MontoItem")
        if not tax:
            try:
                item_amount = Decimal(amount or "0")
                indicator = find_text(item, "IndicadorFacturacion")
                rate = {"1": Decimal("0.18"), "2": Decimal("0.16")}.get(indicator)
                if rate and item_amount > 0:
                    tax_amount = (
                        item_amount * rate / (Decimal("1") + rate)
                        if find_text(header, "IndicadorMontoGravado") == "1"
                        else item_amount * rate
                    )
                    tax = _amount_text(tax_amount)
            except Exception:
                tax = ""
        discount = find_text(item, "DescuentoMonto")
        surcharge = find_text(item, "RecargoMonto")
        discount_surcharge = "; ".join(value for value in (
            f"Desc.: {html_escape(discount)}" if discount else "",
            f"Rec.: {html_escape(surcharge)}" if surcharge else "",
        ) if value)
        if discount_surcharge:
            description += f"<br/><font size='7'>{discount_surcharge}</font>"
        def printed_amount(value):
            if not value:
                return "—"
            decimal_value = Decimal(value)
            precision = max(2, -decimal_value.normalize().as_tuple().exponent)
            return f"{decimal_value:,.{precision}f}"

        rows.append([
            format(Decimal(quantity), ",f").rstrip("0").rstrip(".") if "." in quantity else quantity,
            Paragraph(description, styles["Normal"]),
            Paragraph(unit or "—", table_cell_style),
            printed_amount(price), printed_amount(tax), printed_amount(amount),
        ])
    if len(rows) == 1:
        raise ECFWorkflowError("El XML firmado no tiene líneas de detalle para representar.")
    details_table = Table(rows, repeatRows=1, colWidths=[17 * mm, 64 * mm, 18 * mm, 24 * mm, 21 * mm, 33 * mm])
    details_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#d9d9d9")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f2f2")]),
        ("GRID", (0, 0), (-1, -1), .4, colors.HexColor("#999999")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, 0), 4), ("BOTTOMPADDING", (0, 0), (-1, 0), 4),
        ("ALIGN", (0, 0), (0, -1), "RIGHT"), ("ALIGN", (3, 0), (-1, -1), "RIGHT"),
    ]))
    story.append(details_table)

    total_labels = (
        ("MontoGravadoTotal", "Subtotal Gravado:"),
        ("MontoGravadoI1", "Subtotal gravado ITBIS 18%"),
        ("MontoGravadoI2", "Subtotal gravado ITBIS 16%"),
        ("MontoGravadoI3", "Subtotal gravado ITBIS 0%"),
        ("MontoExento", "Subtotal Exento:"),
        ("TotalITBIS", "Total ITBIS:"), ("MontoImpuestoAdicional", "Impuestos adicionales"),
        ("MontoNoFacturable", "Monto no facturable"),
        ("MontoAvancePago", "Avance de pago"),
        ("SaldoAnterior", "Saldo anterior"), ("MontoTotal", "Total:"),
    )
    total_values = {tag: find_text(totals, tag) for tag, _ in total_labels}
    # An entirely exempt debit note still shows the fiscal summary structure.
    # These zeroes describe the signed exempt total; they do not change the XML.
    if (record.document_type == "33" and total_values["MontoExento"]
            and total_values["MontoTotal"]
            and Decimal(total_values["MontoExento"]) == Decimal(total_values["MontoTotal"])
            and not any(total_values[tag] for tag in (
                "MontoGravadoTotal", "MontoGravadoI1", "MontoGravadoI2", "MontoGravadoI3", "TotalITBIS"
            ))):
        total_values["MontoGravadoTotal"] = "0.00"
        total_values["TotalITBIS"] = "0.00"
    totals_rows = [[label, f"{Decimal(total_values[tag]):,.2f}"] for tag, label in total_labels if total_values[tag]
                   and not (tag in {"MontoGravadoI1", "MontoGravadoI2", "MontoGravadoI3"} and total_values["MontoGravadoTotal"])]
    totals_table = Table(totals_rows, colWidths=[42 * mm, 40 * mm], hAlign="RIGHT")
    totals_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("BACKGROUND", (1, 0), (1, -1), colors.HexColor("#f2f2f2")),
        ("GRID", (1, 0), (1, -1), .4, colors.HexColor("#999999")),
    ]))
    global_adjustments = header.xpath(
        "./*[local-name()='DescuentosORecargos']/*[local-name()='DescuentoORecargo']"
    )
    if global_adjustments:
        adjustment_rows = [["Ajuste", "Descripción", "Valor"]]
        for adjustment in global_adjustments:
            adjust_type = find_text(adjustment, "TipoAjuste")
            adjust_label = {"D": "Descuento", "R": "Recargo"}.get(adjust_type, adjust_type)
            adjustment_rows.append([
                html_escape(adjust_label),
                html_escape(find_text(adjustment, "DescripcionDescuentooRecargo")),
                html_escape(find_text(adjustment, "MontoDescuentooRecargo")),
            ])
        adjustment_table = Table(adjustment_rows, colWidths=[35 * mm, 95 * mm, 35 * mm])
        adjustment_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8edf2")),
            ("GRID", (0, 0), (-1, -1), .35, colors.HexColor("#aab3bc")),
            ("ALIGN", (2, 0), (2, -1), "RIGHT"),
        ]))
        story.extend([Spacer(1, 4 * mm), adjustment_table])
    qr = qrcode.QRCode(version=8, box_size=8, border=4, error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(qr_url)
    qr.make(fit=True)
    qr_buffer = BytesIO()
    qr.make_image(fill_color="black", back_color="white").save(qr_buffer, format="PNG")
    qr_buffer.seek(0)
    qr_reader = ImageReader(qr_buffer)

    def draw_qr(canvas, x, top):
        canvas.drawImage(qr_reader, x, top - 22 * mm, width=22 * mm, height=22 * mm, mask="auto")
        for label, value, offset in (
            ("Código de Seguridad:", security_code, 26),
            ("Fecha Firma:", signed_date, 30),
        ):
            text = canvas.beginText(x, top - offset * mm)
            text.setFont("Helvetica-Bold", 7)
            text.textOut(label + " ")
            text.setFont("Helvetica", 7)
            text.textOut(value)
            canvas.drawText(text)

    class FiscalSummary(Flowable):
        def wrap(self, available_width, available_height):
            self.width = 177 * mm
            _, self.totals_height = totals_table.wrap(82 * mm, available_height)
            self.height = max(34 * mm, self.totals_height) + 10 * mm
            return self.width, self.height

        def draw(self):
            canvas = self.canv
            canvas._ri_summary_drawn = True
            canvas.setStrokeColor(rule_color)
            canvas.setLineWidth(1.2)
            canvas.line(0, self.height - 5 * mm, self.width, self.height - 5 * mm)
            draw_qr(canvas, 3 * mm, self.height - 10 * mm)
            totals_table.drawOn(canvas, self.width - 82 * mm, self.height - 10 * mm - self.totals_height)

    story.append(FiscalSummary())

    def draw_header(canvas, _document):
        canvas.saveState()
        header_table.drawOn(canvas, 20 * mm, letter[1] - 16 * mm - header_height)
        canvas._ri_summary_drawn = False
        canvas.restoreState()

    def draw_consultation_footer(canvas, _document):
        canvas.saveState()
        if not getattr(canvas, "_ri_summary_drawn", False):
            canvas.setStrokeColor(rule_color)
            canvas.setLineWidth(1.2)
            canvas.line(20 * mm, 51 * mm, 197 * mm, 51 * mm)
            draw_qr(canvas, 23 * mm, 47 * mm)
        canvas.restoreState()

    class PaginatedCanvas(Canvas):
        """Only paginated invoices need the page label shown in DGII's model."""
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.page_states = []

        def showPage(self):
            self.page_states.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            count = len(self.page_states)
            for state in self.page_states:
                self.__dict__.update(state)
                if count > 1:
                    self.setFont("Helvetica", 7)
                    self.drawRightString(197 * mm, 12 * mm, f"Página {self._pageNumber} de {count}")
                super().showPage()
            super().save()

    doc.addPageTemplates(PageTemplate(
        id="DGII", frames=[Frame(doc.leftMargin, doc.bottomMargin, doc.width,
            letter[1] - doc.topMargin - doc.bottomMargin, leftPadding=0, rightPadding=0,
            topPadding=0, bottomPadding=0)], onPage=draw_header, onPageEnd=draw_consultation_footer,
    ))
    doc.build(story, canvasmaker=PaginatedCanvas)
    return buffer.getvalue()
