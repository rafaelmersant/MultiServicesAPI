"""Local fiscal ID validation; this does not certify DGII registration status."""
import re
import unicodedata
from stdnum.do import cedula, rnc


def generic_customer(customer):
    name = " ".join((customer.firstName or "", customer.lastName or "")).strip().upper()
    name = "".join(char for char in unicodedata.normalize("NFKD", name) if not unicodedata.combining(char))
    name = " ".join(name.split())
    return name in {"GENERICO CLIENTE", "CLIENTE GENERICO", "CONSUMIDOR FINAL", "CLIENTE GENERAL", "PUBLICO GENERAL"}


def validate_fiscal_id(kind, number):
    kind, raw = str(kind or "").strip().upper(), str(number or "").strip()
    if kind not in {"C", "R"}:
        raise ValueError("Selecciona Cédula o RNC para el cliente.")
    if not raw or not re.fullmatch(r"[0-9 -]+", raw):
        raise ValueError("Digita la identificación fiscal del cliente usando números, espacios o guiones.")
    number = re.sub(r"[ -]", "", raw)
    lengths = {11} if kind == "C" else {9, 11}
    if len(number) not in lengths:
        raise ValueError("La cédula requiere 11 dígitos." if kind == "C" else "El RNC requiere 9 dígitos, o 11 para persona física.")
    validator = rnc if len(number) == 9 else cedula
    if not validator.is_valid(number) or len(set(number)) == 1:
        raise ValueError("La identificación no tiene un dígito verificador válido. Revisa el número del cliente.")
    return kind, number


def customer_fiscal_status(customer, *, kind=None, number=None):
    kind = customer.identificationType if kind is None else kind
    number = customer.identification if number is None else number
    result = {"customer": customer.pk, "identificationType": kind or "", "identification": number or "",
              "valid": False, "validation": "format_checksum", "dgii_registration_verified": False}
    try:
        if generic_customer(customer):
            raise ValueError("Selecciona o crea el cliente real para E31; no asignes un RNC particular al cliente genérico.")
        kind, number = validate_fiscal_id(kind, number)
        result.update(valid=True, identificationType=kind, identification=number,
                      message="Formato y dígito verificador correctos.")
    except ValueError as exc:
        result["message"] = str(exc)
    return result
