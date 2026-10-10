import argparse
import logging
import sys

from dotenv import load_dotenv

from ecf.certificate import load_certificate
from ecf.config import load_settings
from ecf.dgii_auth import DGIIAuthenticator
from ecf.dgii_reception import DGIIReceptionClient


logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s | %(levelname)s | "
        "%(name)s | %(message)s"
    ),
)

logger = logging.getLogger(__name__)


def main() -> int:

    parser = argparse.ArgumentParser(
        description="Consulta el resultado de un e-CF en DGII."
    )

    parser.add_argument(
        "--track-id",
        required=True,
        help="TrackId devuelto por DGII.",
    )

    args = parser.parse_args()

    try:

        load_dotenv()

        settings = load_settings()

        certificate = load_certificate(
            settings.certificate_path,
            settings.certificate_password,
        )

        # Obtener token válido
        authenticator = DGIIAuthenticator(
            settings=settings,
            certificate=certificate,
        )

        token_data = authenticator.authenticate()

        token = token_data["token"]

        reception = DGIIReceptionClient(
            reception_base_url=(
                settings.reception_base_url
            ),
            result_base_url=(
                settings.result_base_url
            ),
        )

        result = reception.get_result(
            track_id=args.track_id,
            token=token,
        )

        print()
        print("========== RESULTADO DGII ==========")
        print(
            f"TrackId: {result.track_id}"
        )
        print(
            f"Código: {result.code}"
        )
        print(
            f"Estado: {result.status}"
        )
        print(
            f"RNC: {result.rnc}"
        )
        print(
            f"e-NCF: {result.encf}"
        )
        print(
            f"Secuencia utilizada: "
            f"{result.sequence_used}"
        )
        print(
            f"Fecha recepción: "
            f"{result.reception_date}"
        )

        if result.messages:
            print()
            print("Mensajes:")

            for message in result.messages:
                print(
                    f"  Código: "
                    f"{message.get('codigo')}"
                )
                print(
                    f"  Valor: "
                    f"{message.get('valor')}"
                )

        print(
            "===================================="
        )

        return 0

    except Exception as exc:

        logger.exception(
            "Falló la consulta: %s",
            type(exc).__name__,
        )

        print(
            f"ERROR REAL: "
            f"{type(exc).__name__}: {exc}"
        )

        return 1


if __name__ == "__main__":
    sys.exit(main())