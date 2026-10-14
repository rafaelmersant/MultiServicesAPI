import argparse
import logging
import sys

from dotenv import load_dotenv

from ecf.certificate import load_pkcs12, certificate_summary
from ecf.config import Settings
from ecf.dgii_auth import DGIIAuthenticator
from ecf.logging_config import configure_logging


logger = logging.getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Autenticación DGII e-CF por ambiente configurado."
    )

    options = parser.add_mutually_exclusive_group(required=True)
    options.add_argument(
        "--check-certificate",
        action="store_true",
        help="Solo revisa el certificado local.",
    )
    options.add_argument(
        "--authenticate",
        action="store_true",
        help="Solicita la semilla y pide un token al ambiente DGII configurado.",
    )

    args = parser.parse_args()

    load_dotenv()
    configure_logging()

    try:
        settings = Settings.from_env()

        logger.info("Ambiente DGII configurado: %s", settings.environment)

        certificate = load_pkcs12(
            settings.certificate_path,
            settings.certificate_password,
        )

        if settings.expected_tax_id:
            logger.info(
                "Se configuró un identificador fiscal esperado "
                "para revisión adicional."
            )

        if args.check_certificate:
            summary = certificate_summary(certificate)
            print("Certificado cargado correctamente.")
            print(f"Ambiente configurado: {settings.environment}")
            print(f"Titular: {summary['subject']}")
            print(f"Emisor: {summary['issuer']}")
            print(f"Serie: {summary['serial_number']}")
            print(f"Válido desde: {summary['not_before']}")
            print(f"Válido hasta: {summary['not_after']}")
            print(f"Huella SHA-256: {summary['sha256_fingerprint']}")
            return 0

        # Settings determina la URL según DGII_ENVIRONMENT. No se debe
        # restringir la autenticación a precertificación aquí.
        print(f"Autenticando contra el ambiente: {settings.environment}")
        print(f"URL de autenticación: {settings.auth_base_url}")

        authenticator = DGIIAuthenticator(
            settings=settings,
            certificate=certificate,
        )
        token_data = authenticator.authenticate()

        print("Autenticación completada.")
        print(f"Expedido: {token_data.expedido}")
        print(f"Expira: {token_data.expira}")
        print("El token fue recibido. Por seguridad no se mostrará en pantalla.")
        return 0

    except Exception as exc:
        logger.exception(
            "Falló el proceso: %s - %s",
            type(exc).__name__,
            str(exc),
        )
        print(f"ERROR REAL: {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
