from django.conf.urls import url, include
from django.conf import settings
from django.contrib import admin
from rest_framework.authtoken import views

from django.urls import path


urlpatterns = [
    path('admin/', admin.site.urls),
]

urlpatterns += [
    url(r'^api/v1/', include('administration.urls')),
    url(r'^api/v1/', include('products.urls')),
    url(r'^api/v1/', include('sales.urls')),
    url(r'^api/v1/auth', include('rest_framework.urls'))
]
