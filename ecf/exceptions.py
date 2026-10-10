class ECFError(Exception):
    """Base exception for the e-CF integration."""


class TestSetError(ECFError):
    """Error en el set de pruebas DGII."""


class DGIIClientError(ECFError):
    """Error de comunicación con DGII."""


class DGIIReceptionError(Exception):
    """Error de recepción o consulta de e-CF en DGII."""


class XMLValidationError(ECFError):
    """Error de estructura o validación XML."""