""" Sales URLs. """


# Django
from django.urls import include, path

# Rest Framework
from rest_framework.routers import DefaultRouter

# Views
from . import views

router = DefaultRouter()
router.register('invoicesHeaders', views.InvoicesHeaderViewSet)
router.register('invoicesDetails', views.InvoicesDetailViewSet)
router.register('invoicesSequences', views.InvoicesSequenceViewSet)
router.register('invoicesHeadersFull', views.InvoicesHeaderListFull)
router.register('invoicesLeadHeader', views.InvoicesLeadsHeaderViewSet)
router.register('invoicesLeadDetail', views.InvoicesLeadsDetailViewSet)

urlpatterns = [
    path('', include(router.urls)),
]

# urlpatterns = [
#     re_path(r'^invoicesHeaders/$', InvoicesHeaderList.as_view(),
#         name='invoicesHeader'),
#     re_path(r'^invoicesHeaders/(?P<pk>[0-9]+)', InvoicesHeaderList.as_view(),
#         name='invoicesHeader_byId'),

#     re_path(r'^invoicesDetails/$', InvoicesDetailList.as_view(),
#         name='invoicesDetail'),
#     re_path(r'^invoicesDetails/(?P<pk>[0-9]+)', InvoicesDetailList.as_view(),
#         name='invoicesDetail_byId'),

#     re_path(r'^invoicesSequences/$', InvoicesSequenceList.as_view(),
#         name='invoicesSequence'),
#     re_path(r'^invoicesSequences/(?P<pk>[0-9]+)',
#         InvoicesSequenceList.as_view(),
#         name='invoicesSequence_byId'),

#     re_path(r'^invoicesHeadersFull/$', InvoicesHeaderListFull.as_view(),
#         name='invoicesHeaderFull'),

#     re_path(r'^invoicesLeadHeader/$', InvoicesLeadsHeaderList.as_view(),
#         name='invoicesLeadHeader'),
#     re_path(r'^invoicesLeadHeader/(?P<id>[0-9]+)',
#         InvoicesLeadsHeaderList.as_view(),
#         name='invoicesLeadHeader_byId'),

#     re_path(r'^invoicesLeadDetail/$', InvoicesLeadsDetailList.as_view(),
#         name='invoicesLeadsDetail'),
#     re_path(r'^invoicesLeadDetail/(?P<pk>[0-9]+)',
#         InvoicesLeadsDetailList.as_view(),
#         name='invoicesLeadsDetail_byId'),

# ]
