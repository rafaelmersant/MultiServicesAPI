import logging
import sys


def configure_logging(
    level: int = logging.INFO
) -> None:

    """
    Configura logging de la aplicación.

    IMPORTANTE:
    Nunca debemos escribir certificados,
    contraseñas, tokens o XML completos
    con información sensible en los logs.
    """

    logging.basicConfig(
        level=level,
        stream=sys.stdout,
        format=(
            "%(asctime)s | "
            "%(levelname)s | "
            "%(name)s | "
            "%(message)s"
        ),
    )