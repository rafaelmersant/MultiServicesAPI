# from django.conf.urls import url, include
from django.conf import settings
from django.contrib import admin
from rest_framework.authtoken import views
from rest_framework_simplejwt import views as jwt_views

from django.urls import re_path, include

urlpatterns = [
    re_path('admin/', admin.site.urls),
    re_path(r'^api/v1/', include('administration.urls')),
    re_path(r'^api/v1/', include('products.urls')),
    re_path(r'^api/v1/', include('sales.urls')),
    re_path(r'^api/v1/auth', include('rest_framework.urls')),
    re_path(r'^api/v1/token/', jwt_views.TokenObtainPairView.as_view(),
        name='token_obtain_pair'),
    re_path(r'^api/v1/token/refresh/',
        jwt_views.TokenRefreshView.as_view(), name='token_refresh'),
]
