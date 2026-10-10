from pathlib import Path

from lxml import etree

from .exceptions import XMLValidationError


XML_ENCODING = "UTF-8"


def parse_xml(
    xml: str | bytes
) -> etree._ElementTree:

    parser = etree.XMLParser(
        remove_blank_text=False,
        resolve_entities=False,
        no_network=True,
    )

    try:

        root = etree.fromstring(
            xml,
            parser=parser,
        )

    except (
        etree.XMLSyntaxError,
        ValueError,
    ) as exc:

        raise XMLValidationError(
            f"XML inválido: {exc}"
        ) from exc

    return root.getroottree()


def pretty_xml(
    tree: etree._ElementTree
) -> str:

    return etree.tostring(
        tree,
        encoding=XML_ENCODING,
        xml_declaration=True,
        pretty_print=True,
    ).decode(
        XML_ENCODING
    )


def validate_xsd(
    xml: str | bytes,
    xsd_path: str | Path,
) -> None:

    """
    Valida un XML contra el XSD correspondiente
    al e-CF y muestra los errores detallados.
    """

    try:

        schema_doc = etree.parse(
            str(xsd_path),
            parser=etree.XMLParser(
                no_network=True
            ),
        )

        schema = etree.XMLSchema(
            schema_doc
        )

        tree = parse_xml(xml)

        # Validar y mostrar todos los errores encontrados.
        if not schema.validate(tree):

            for error in schema.error_log:

                print(
                    f"XSD ERROR | "
                    f"Line: {error.line} | "
                    f"Column: {error.column} | "
                    f"Message: {error.message}"
                )

            # Lanza DocumentInvalid para conservar
            # el manejo de excepciones existente.
            schema.assertValid(tree)

    except (
        OSError,
        etree.XMLSchemaParseError,
        etree.DocumentInvalid,
    ) as exc:

        raise XMLValidationError(
            f"Fallo de validación XSD: {exc}"
        ) from exc