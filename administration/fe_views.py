import xmltodict
import json
import logging

from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger(__name__)


# ==========================================================
# 1. AUTENTICACION - SEMILLA
# URL:
# /api/api/v1/fe/autenticacion/api/semilla
# ==========================================================
@csrf_exempt
@api_view(['POST', 'GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def dgii_semilla(request):

    logger.info("DGII AUTENTICACION HIT")

    return Response({
        "status": "OK",
        "message": "Endpoint autenticacion disponible"
    }, status=status.HTTP_200_OK)


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
        data = request.data

        logger.info("DGII RECEPCION DATA")
        logger.info(data)

        track_id = data.get("trackId")
        estado = data.get("estado")

        # 🔥 Aquí guardarás en DB luego
        # Invoice.objects.filter(track_id=track_id).update(status=estado)

        return Response({
            "status": "received",
            "trackId": track_id
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(str(e))

        return Response({
            "status": "error",
            "message": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
        data = request.data

        logger.info("DGII EVENTO COMERCIAL")
        logger.info(data)

        evento = data.get("evento")

        # guardar evento comercial luego

        return Response({
            "status": "evento recibido",
            "evento": evento
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(str(e))

        return Response({
            "status": "error",
            "message": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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