# Django
from django.urls import include, path, re_path

# Rest Framework
from rest_framework.routers import DefaultRouter

# Views
from . import views

from administration.fe_views import (
    dgii_semilla,
    dgii_validacion_certificado,
    dgii_recepcion_ecf,
    dgii_aprobacion_comercial
)

router = DefaultRouter()
router.register('companies', views.CompanyViewSet)
router.register('users', views.UserViewSet)
router.register('customers', views.CustomerViewSet)
router.register('providers', views.ProviderViewSet)
router.register('fiscalGov', views.FiscalGovViewSet)

urlpatterns = [
    path('', include(router.urls)),
    re_path(r'^auth/login/$', views.UserLogin.as_view(), name='UserLogin'),

     # =============================
    # DGII FACTURACION ELECTRONICA
    # =============================

    re_path(
        r'^[fF][eE]/[aA][uU][tT][eE][nN][tT][iI][cC][aA][cC][iI][oO][nN]/[aA][pP][iI]/[sS][eE][mM][iI][lL][lL][aA]/?$',
        dgii_semilla,
        name='dgii-semilla'
    ),

    re_path(
        r'^[fF][eE]/[aA][uU][tT][eE][nN][tT][iI][cC][aA][cC][iI][oO][nN]/[aA][pP][iI]/[vV][aA][lL][iI][dD][aA][cC][iI][oO][nN][cC][eE][rR][tT][iI][fF][iI][cC][aA][dD][oO]/?$',
        dgii_validacion_certificado,
        name='dgii-validacion-certificado'
    ),

    re_path(
        r'^[fF][eE]/[rR][eE][cC][eE][pP][cC][iI][oO][nN]/[aA][pP][iI]/[eE][cC][fF]/?$',
        dgii_recepcion_ecf,
        name='dgii-recepcion'
    ),

    re_path(
        r'^[fF][eE]/[aA][pP][rR][oO][bB][aA][cC][iI][oO][nN][cC][oO][mM][eE][rR][cC][iI][aA][lL]/[aA][pP][iI]/[eE][cC][fF]/?$',
        dgii_aprobacion_comercial,
        name='dgii-aprobacion'
    ),
]
