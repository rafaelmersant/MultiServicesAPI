
import argparse
import logging
import sys

from dotenv import load_dotenv

from ecf.certificate import (
    load_pkcs12,
    certificate_summary,
)
from ecf.config import Settings
from ecf.dgii_auth import DGIIAuthenticator
from ecf.logging_config import configure_logging


logger = logging.getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Autenticación DGII e-CF."
    )

    parser.add_argument(
        "--check-certificate",
        action="store_true",
        help="Solo revisa el certificado local.",
    )

    parser.add_argument(
        "--authenticate",
        action="store_true",
        help="Solicita semilla y pide token a DGII.",
    )

    args = parser.parse_args()

    if args.check_certificate == args.authenticate:
        parser.error(
            "Selecciona exactamente una opción: "
            "--check-certificate o --authenticate."
        )

    load_dotenv()
    configure_logging()

    try:
        settings = Settings.from_env()

        certificate = load_pkcs12(
            settings.certificate_path,
            settings.certificate_password,
        )
        
        if settings.expected_tax_id:
            logger.info(
                "Se configuró un identificador esperado "
                "para revisión adicional."
            )

        if args.check_certificate:
            summary = certificate_summary(
                certificate
            )

            print("Certificado cargado correctamente.")
            print(f"Titular: {summary['subject']}")
            print(f"Emisor: {summary['issuer']}")
            print(f"Serie: {summary['serial_number']}")
            print(f"Válido desde: {summary['not_before']}")
            print(f"Válido hasta: {summary['not_after']}")
            print(
                "Huella SHA-256: "
                f"{summary['sha256_fingerprint']}"
            )

            return 0

        if settings.environment != "precert":
            raise RuntimeError(
                "Este script de prueba solo permite "
                "autenticación en precertificación."
            )

        authenticator = DGIIAuthenticator(
            settings=settings,
            certificate=certificate,
        )
        
        token_data = authenticator.authenticate()

        print("Autenticación completada.")
        print(f"Expedido: {token_data.expedido}")
        print(f"Expira: {token_data.expira}")
        print(
            "El token fue recibido. "
            "Por seguridad no se mostrará en pantalla."
        )

        return 0

    except Exception as exc:
        logger.exception(
            "Falló el proceso: %s - %s",
            type(exc).__name__,
            str(exc),
        )

        print(
            f"ERROR REAL: {type(exc).__name__}: {exc}"
        )

        return 1


if __name__ == "__main__":
    sys.exit(main())