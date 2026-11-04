# from django.conf.urls import url, include
from ast import pattern
import debug_toolbar
from django.conf import settings
from django.contrib import admin
from rest_framework.authtoken import views
from rest_framework_simplejwt import views as jwt_views

from django.urls import include, path, re_path
from administration.fe_views import (
    dgii_semilla,
    dgii_validacion_certificado,
    dgii_recepcion_ecf,
    dgii_aprobacion_comercial,
)

urlpatterns = [
    re_path('admin/', admin.site.urls),
    re_path(r'^api/v1/', include('sales.urls')),
    re_path(r'^api/v1/', include('administration.urls')),
    re_path(r'^api/v1/', include('products.urls')),
    path('api/v1/ecf/', include('ecf.urls')),
    # DGII's published receiver endpoints use these fixed paths. Keep the
    # historical /api/v1 aliases in administration.urls for compatibility.
    re_path(r'^[fF][eE]/[aA][uU][tT][eE][nN][tT][iI][cC][aA][cC][iI][oO][nN]/[aA][pP][iI]/[sS][eE][mM][iI][lL][lL][aA]/?$', dgii_semilla, name='dgii-semilla-standard'),
    re_path(r'^[fF][eE]/[aA][uU][tT][eE][nN][tT][iI][cC][aA][cC][iI][oO][nN]/[aA][pP][iI]/[vV][aA][lL][iI][dD][aA][cC][iI][oO][nN][cC][eE][rR][tT][iI][fF][iI][cC][aA][dD][oO]/?$', dgii_validacion_certificado, name='dgii-auth-standard'),
    re_path(r'^[fF][eE]/[rR][eE][cC][eE][pP][cC][iI][oO][nN]/[aA][pP][iI]/[eE][cC][fF]/?$', dgii_recepcion_ecf, name='dgii-recepcion-standard'),
    re_path(r'^[fF][eE]/[aA][pP][rR][oO][bB][aA][cC][iI][oO][nN][cC][oO][mM][eE][rR][cC][iI][aA][lL]/[aA][pP][iI]/[eE][cC][fF]/?$', dgii_aprobacion_comercial, name='dgii-aprobacion-standard'),
    re_path(r'^api/v1/auth', include('rest_framework.urls')),
    re_path(r'^api/v1/token/', jwt_views.TokenObtainPairView.as_view(),
        name='token_obtain_pair'),
    re_path(r'^api/v1/token/refresh/',
        jwt_views.TokenRefreshView.as_view(), name='token_refresh'),
    path('__debug__/', include('debug_toolbar.urls')),
]
