import xmltodict
import logging

from django.http import HttpResponse
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
    renderer_classes,
)
from rest_framework.permissions import AllowAny
from rest_framework.renderers import BaseRenderer, JSONRenderer
from rest_framework.response import Response
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from ecf.inbound import InboundDocumentError, receive_commercial_approval, receive_ecf
from ecf.inbound_auth import (
    ECFAuthenticationConfigError,
    ECFAuthenticationError,
    issue_seed,
    validate_seed,
    verify_receiver_authorization,
)

logger = logging.getLogger(__name__)


class DGIIXMLRenderer(BaseRenderer):
    media_type = "application/xml"
    format = "xml"
    charset = None

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data or b""


# ==========================================================
# 1. AUTENTICACION - SEMILLA
# URL:
# /api/api/v1/fe/autenticacion/api/semilla
# ==========================================================
@csrf_exempt
@api_view(['GET'])
@renderer_classes([JSONRenderer, DGIIXMLRenderer])
@authentication_classes([])
@permission_classes([AllowAny])
def dgii_semilla(request):
    return issue_seed()


@csrf_exempt
@api_view(['POST'])
@renderer_classes([JSONRenderer, DGIIXMLRenderer])
@authentication_classes([])
@permission_classes([AllowAny])
def dgii_validacion_certificado(request):
    try:
        result = validate_seed(request)
        if isinstance(result, HttpResponse):
            return result
        return Response(result, status=status.HTTP_200_OK)
    except ECFAuthenticationConfigError as exc:
        return Response({"status": "error", "message": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    except ECFAuthenticationError as exc:
        return Response({"status": "error", "message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


# ==========================================================
# 2. RECEPCION DGII
# URL:
# /api/api/v1/fe/recepcion/api/ecf
# ==========================================================

@csrf_exempt
@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def dgii_recepcion_ecf(request):
    try:
        verify_receiver_authorization(request)
        return receive_ecf(request)
    except ECFAuthenticationConfigError as exc:
        return Response({"status": "error", "message": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    except ECFAuthenticationError as exc:
        return Response({"status": "error", "message": str(exc)}, status=status.HTTP_401_UNAUTHORIZED)
    except InboundDocumentError as exc:
        return Response({"status": "error", "message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


# ==========================================================
# 3. APROBACION COMERCIAL
# URL:
# /api/api/v1/fe/aprobacioncomercial/api/ecf
# ==========================================================

@csrf_exempt
@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])  
def dgii_aprobacion_comercial(request):
    try:
        verify_receiver_authorization(request)
        return receive_commercial_approval(request)
    except ECFAuthenticationConfigError as exc:
        return HttpResponse(f"Error: {exc}", content_type="text/plain; charset=utf-8", status=503)
    except ECFAuthenticationError as exc:
        return HttpResponse(f"Error: {exc}", content_type="text/plain; charset=utf-8", status=401)
    except InboundDocumentError as exc:
        return HttpResponse(f"Error: {exc}", content_type="text/plain; charset=utf-8", status=400)


def parse_dgii_request(request):

    content_type = request.META.get('CONTENT_TYPE', '')

    # JSON
    if 'application/json' in content_type:
        return request.data

    # XML
    if 'xml' in content_type:
        body_unicode = request.body.decode('utf-8')
        return xmltodict.parse(body_unicode)

    return {}
