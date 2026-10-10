"""Build DGII e-CF XML documents from the official Excel test-set rows.

The XSD controls element names, nesting and order. Excel columns supply values.
This module only builds and validates XML; it never signs or sends documents.
"""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from lxml import etree

from .exceptions import XMLValidationError

XSD_NS = "http://www.w3.org/2001/XMLSchema"
_INDEX_RE = re.compile(r"\[(\d+)\]")


def _normal_name(value: str) -> str:
    # The workbook contains a few padded headers and differs in eNCF casing.
    return re.sub(r"\s+", "", value).casefold()


def _split_header(header: str) -> tuple[str, tuple[int, ...]]:
    indexes = tuple(int(x) for x in _INDEX_RE.findall(header))
    base = _INDEX_RE.sub("", header).strip()
    return _normal_name(base), indexes


def _clean_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        if not value or value.casefold() == "#e":
            return None
        return value
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


class _ExcelValues:
    def __init__(self, values: Mapping[str, Any], ambiguous_names: set[str] | None = None):
        self.ambiguous_names = ambiguous_names or set()
        self.values: dict[tuple[str, tuple[int, ...]], str] = {}
        for header, raw in values.items():
            if not header:
                continue
            name, indexes = _split_header(str(header))
            value = _clean_value(raw)
            if value is None:
                continue
            self.values[(name, indexes)] = value

    def get(self, element_name: str, indexes: tuple[int, ...]) -> str | None:
        key = (_normal_name(element_name), indexes)
        if key in self.values:
            return self.values[key]
        # eNCF is called ENCF in the DGII workbook.
        if _normal_name(element_name) == "encf":
            return self.values.get(("encf", indexes))
        return None

    def max_for_subtree(self, element: etree._Element, indexes: tuple[int, ...]) -> int:
        """Largest occurrence index with data under this element and context."""
        candidates: list[int] = []
        for leaf in element.iter(f"{{{XSD_NS}}}element"):
            if leaf.get("name") is None:
                continue
            name = _normal_name(leaf.get("name"))
            # Allow duplicate field names only inside the per-item additional-tax table.
            if name in self.ambiguous_names and not _is_within_named_element(element, "TablaImpuestoAdicional"):
                continue
            for (column_name, column_indexes), _ in self.values.items():
                if column_name != name or len(column_indexes) <= len(indexes):
                    continue
                if column_indexes[:len(indexes)] == indexes:
                    candidates.append(column_indexes[len(indexes)])
        return max(candidates, default=0)


def _is_complex(element: etree._Element) -> bool:
    return element.find(f"{{{XSD_NS}}}complexType") is not None


def _is_within_named_element(element: etree._Element, ancestor_name: str) -> bool:
    """Return True when an XSD node is inside the named element context."""
    current = element
    while current is not None:
        if current.tag == f"{{{XSD_NS}}}element" and current.get("name") == ancestor_name:
            return True
        current = current.getparent()
    return False


def _children(element: etree._Element) -> list[etree._Element]:
    complex_type = element.find(f"{{{XSD_NS}}}complexType")
    if complex_type is None:
        return []
    sequence = complex_type.find(f"{{{XSD_NS}}}sequence")
    if sequence is None:
        return []
    return sequence.findall(f"{{{XSD_NS}}}element")


def _subtree_has_data(
    element: etree._Element,
    values: _ExcelValues,
    indexes: tuple[int, ...],
) -> bool:
    if not _is_complex(element):
        name = element.get("name")
        is_ambiguous = bool(name and _normal_name(name) in values.ambiguous_names)
        allowed_item_tax = _is_within_named_element(element, "TablaImpuestoAdicional")
        return bool(
            name
            and (not is_ambiguous or allowed_item_tax)
            and values.get(name, indexes) is not None
        )
    for child in _children(element):
        if _subtree_has_data(child, values, indexes):
            return True
        if child.get("maxOccurs", "1") != "1":
            limit = values.max_for_subtree(child, indexes)
            for i in range(1, limit + 1):
                if _subtree_has_data(child, values, indexes + (i,)):
                    return True
    return False


def _max_occurs(element: etree._Element) -> int:
    value = element.get("maxOccurs", "1")
    if value == "unbounded":
        return 10000
    try:
        return int(value)
    except ValueError:
        return 1


def _append_element(
    parent_xml: etree._Element,
    xsd_element: etree._Element,
    values: _ExcelValues,
    indexes: tuple[int, ...],
    *,
    force: bool = False,
) -> bool:
    name = xsd_element.get("name")
    if not name:
        return False

    minimum = int(xsd_element.get("minOccurs", "1"))
    maximum = _max_occurs(xsd_element)
    repeated = maximum > 1

    if repeated:
        # Repeated groups use the index sequence encoded in Excel headers.
        limit = min(maximum, values.max_for_subtree(xsd_element, indexes))
        created = False
        for occurrence in range(1, limit + 1):
            child_indexes = indexes + (occurrence,)
            if not _subtree_has_data(xsd_element, values, child_indexes):
                continue
            node = etree.SubElement(parent_xml, name)
            if _is_complex(xsd_element):
                for child in _children(xsd_element):
                    _append_element(node, child, values, child_indexes)
            else:
                value = values.get(name, child_indexes)
                if value is not None:
                    node.text = value
            created = True
        if minimum > 0 and not created and force:
            node = etree.SubElement(parent_xml, name)
            if _is_complex(xsd_element):
                for child in _children(xsd_element):
                    _append_element(node, child, values, indexes + (1,))
            else:
                value = values.get(name, indexes + (1,))
                if value is not None:
                    node.text = value
            return True
        return created

    if not force and minimum == 0 and not _subtree_has_data(xsd_element, values, indexes):
        return False

    node = etree.SubElement(parent_xml, name)
    if _is_complex(xsd_element):
        for child in _children(xsd_element):
            _append_element(node, child, values, indexes)
    else:
        value = values.get(name, indexes)
        if value is not None:
            node.text = value
    return True


def build_ecf_xml(
    test_case: Any,
    xsd_path: str | Path,
    *,
    fecha_hora_firma: str | None = None,
    validate: bool = True,
) -> bytes:
    """Build XML for a TestCase-like object, optionally validating against XSD.

    ``test_case`` must expose ``values`` (mapping) and preferably ``tipo_ecf``.
    ``FechaHoraFirma`` is generated because it is not a column in the test Excel.
    """
    xsd_path = Path(xsd_path)
    if not xsd_path.is_file():
        raise FileNotFoundError(f"No existe el XSD: {xsd_path}")

    try:
        schema_doc = etree.parse(str(xsd_path), etree.XMLParser(no_network=True))
        schema_root = schema_doc.getroot()
        root_decl = schema_root.find(f"{{{XSD_NS}}}element[@name='ECF']")
        if root_decl is None:
            raise XMLValidationError(f"El XSD no define el elemento raíz ECF: {xsd_path}")
    except (OSError, etree.XMLSyntaxError) as exc:
        raise XMLValidationError(f"No se pudo leer el XSD {xsd_path}: {exc}") from exc

    values_dict = dict(test_case.values)
    if not values_dict.get("FechaHoraFirma"):
        values_dict["FechaHoraFirma"] = fecha_hora_firma or datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    # Some Excel labels (notably NumeroLinea and TipoImpuesto) are reused in
    # different XML branches. They must not activate an optional branch by name
    # alone; otherwise an empty DescuentosORecargos could be created from an
    # Item's NumeroLinea.
    leaf_names = [
        _normal_name(el.get("name"))
        for el in schema_root.iter(f"{{{XSD_NS}}}element")
        if el.get("name") and not _is_complex(el)
    ]
    name_counts: dict[str, int] = {}
    for leaf_name in leaf_names:
        name_counts[leaf_name] = name_counts.get(leaf_name, 0) + 1
    ambiguous_names = {name for name, count in name_counts.items() if count > 1}
    values = _ExcelValues(values_dict, ambiguous_names)

    root = etree.Element("ECF")
    for child in _children(root_decl):
        _append_element(root, child, values, ())

    xml_bytes = etree.tostring(
        root.getroottree(),
        encoding="UTF-8",
        xml_declaration=True,
        pretty_print=True,
    )
    if validate:
        # DGII's official ECF XSD requires an XMLDSig child (xs:any) at the end.
        # The unsigned document cannot pass that final check yet, so validate
        # the same official schema with only that signature placeholder optional.
        # The signed XML must still be validated against the untouched XSD.
        sequence = root_decl.find(f"{{{XSD_NS}}}complexType/{{{XSD_NS}}}sequence")
        if sequence is None:
            raise XMLValidationError(f"El XSD no tiene una secuencia raíz válida: {xsd_path}")
        any_nodes = sequence.findall(f"{{{XSD_NS}}}any")
        for any_node in any_nodes:
            any_node.set("minOccurs", "0")
        try:
            pre_sign_schema = etree.XMLSchema(schema_doc)
            pre_sign_schema.assertValid(etree.fromstring(xml_bytes))
        except (etree.XMLSchemaParseError, etree.DocumentInvalid) as exc:
            details = "\n".join(str(error) for error in pre_sign_schema.error_log) if "pre_sign_schema" in locals() else str(exc)
            raise XMLValidationError(f"Fallo de validación estructural previa a la firma:\n{details}") from exc
    return xml_bytes


def build_ecf_xml_text(
    test_case: Any,
    xsd_path: str | Path,
    *,
    fecha_hora_firma: str | None = None,
    validate: bool = True,
) -> str:
    return build_ecf_xml(
        test_case,
        xsd_path,
        fecha_hora_firma=fecha_hora_firma,
        validate=validate,
    ).decode("UTF-8")
