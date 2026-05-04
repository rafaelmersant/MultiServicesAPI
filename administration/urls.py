# Django
from django.urls import include, path, re_path

# Rest Framework
from rest_framework.routers import DefaultRouter

# Views
from . import views

from administration.fe_views import (
    dgii_semilla,
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

    path(
        'fe/autenticacion/api/semilla',
        dgii_semilla,
        name='dgii-semilla'
    ),

    path(
        'fe/recepcion/api/ecf',
        dgii_recepcion_ecf,
        name='dgii-recepcion'
    ),

    path(
        'fe/aprobacioncomercial/api/ecf',
        dgii_aprobacion_comercial,
        name='dgii-aprobacion'
    ),
]
