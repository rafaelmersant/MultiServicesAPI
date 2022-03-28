""" Sales views. """

# Django
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from django.db.models import Max

# Django REST framework
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.viewsets import ModelViewSet

# Models
from .models import InvoicesHeader, InvoicesDetail, InvoicesSequence, InvoicesLeadHeader, InvoicesLeadDetail

# Serializers
from .serializers import InvoicesHeaderSerializer, InvoicesDetailSerializer, InvoicesSequenceSerializer, \
    InvoicesLeadHeaderSerializer, InvoicesLeadDetailSerializer


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 10


class StandardResultsSetPagination2(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 50


class InvoicesHeaderViewSet(ModelViewSet):
    queryset = InvoicesHeader.objects.select_related('company').prefetch_related('customer').all()
    serializer_class = InvoicesHeaderSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['id', 'company', 'company_id', 'customer', 'sequence', 'customer_id', 
                        'paymentMethod', 'ncf', 'createdUser']


class InvoicesDetailViewSet(ModelViewSet):
    queryset = InvoicesDetail.objects.select_related('product').select_related('invoice').all()
    serializer_class = InvoicesDetailSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['id', 'invoice', 'invoice_id', 'product', 'product_id', 'creationDate']

    
class InvoicesSequenceViewSet(ModelViewSet):
    queryset = InvoicesSequence.objects.select_related('company').all()
    serializer_class = InvoicesSequenceSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['id', 'company', 'company_id', 'sequence', 'createdUser']


class InvoicesHeaderListFull(ModelViewSet):
    queryset = InvoicesHeader.objects.select_related('company').select_related('customer').all()
    serializer_class = InvoicesHeaderSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['id', 'company', 'company_id', 'customer', 'sequence',  'customer_id', 
                        'paymentMethod', 'ncf', 'createdUser']

    
class InvoicesLeadsHeaderViewSet(ModelViewSet):
    queryset = InvoicesLeadHeader.objects.prefetch_related('company').prefetch_related('invoice').all()
    serializer_class = InvoicesLeadHeaderSerializer
    pagination_class = StandardResultsSetPagination2
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['id', 'invoice', 'invoice_id', 'creationDate']


class InvoicesLeadsDetailViewSet(ModelViewSet):
    queryset = InvoicesLeadDetail.objects.select_related('header').select_related('product').all()
    serializer_class = InvoicesLeadDetailSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['id', 'header', 'header_id', 'product', 'product_id', 'creationDate']