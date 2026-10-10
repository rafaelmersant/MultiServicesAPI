from lxml import etree
from signxml import XMLSigner, XMLVerifier, methods
from signxml.algorithms import SignatureMethod, DigestAlgorithm

from .certificate import LoadedCertificate
from .exceptions import XMLValidationError


def sign_xml(
    xml_data: bytes,
    certificate: LoadedCertificate,
) -> bytes:

    parser = etree.XMLParser(
        remove_blank_text=True,
        resolve_entities=False,
        no_network=True,
    )

    try:
        root = etree.fromstring(
            xml_data,
            parser=parser,
        )
    except etree.XMLSyntaxError as exc:
        raise XMLValidationError(
            "No se puede firmar: el XML recibido no es válido."
        ) from exc

    try:
        signer = XMLSigner(
            method=methods.enveloped,
            signature_algorithm="rsa-sha256",
            digest_algorithm="sha256",
            c14n_algorithm=(
                "http://www.w3.org/TR/2001/REC-xml-c14n-20010315"
            ),
        )

        signed_root = signer.sign(
            root,
            key=certificate.private_key_pem,
            cert=certificate.certificate_pem,
            reference_uri=None,
        )

    except Exception as exc:
        raise XMLValidationError(
            f"Error creando la firma XML: {exc}"
        ) from exc

    return etree.tostring(
        signed_root,
        encoding="UTF-8",
        xml_declaration=True,
        pretty_print=False,
    )


def verify_xml_signature(
    signed_xml: bytes,
    certificate: LoadedCertificate,
) -> bool:

    try:
        XMLVerifier().verify(
            signed_xml,
            x509_cert=certificate.certificate_pem,
        )

    except Exception as exc:
        raise XMLValidationError(
            f"Error verificando firma XML: {exc}"
        ) from exc

    return True