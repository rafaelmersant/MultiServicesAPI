from django.conf.urls import url, include
from django.conf import settings
from django.contrib import admin
from rest_framework.authtoken import views
from rest_framework_simplejwt import views as jwt_views

from django.urls import path


urlpatterns = [
    path('admin/', admin.site.urls),
]

urlpatterns += [
    url(r'^api/v1/', include('administration.urls')),
    url(r'^api/v1/', include('products.urls')),
    url(r'^api/v1/', include('sales.urls')),
    url(r'^api/v1/auth', include('rest_framework.urls')),
    url(r'^api/v1/token/', jwt_views.TokenObtainPairView.as_view(),
        name='token_obtain_pair'),
    url(r'^api/v1/token/refresh/',
        jwt_views.TokenRefreshView.as_view(), name='token_refresh'),
]
