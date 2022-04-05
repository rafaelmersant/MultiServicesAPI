""" Sales views. """

# Django
from django_filters.rest_framework import DjangoFilterBackend

# Django REST framework
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated

from MultiServices.paginations import StandardResultsSetPagination, StandardResultsSetPaginationHigh

# Serializers
from . import serializers

# Models
from .models import InvoicesHeader, InvoicesDetail, InvoicesSequence, InvoicesLeadHeader, InvoicesLeadDetail

class InvoicesHeaderViewSet(ModelViewSet):
    queryset = InvoicesHeader.objects.select_related('company').select_related('customer').all()
    serializer_class = serializers.InvoicesHeaderSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['id', 'company', 'company_id', 'customer', 'sequence', 'customer_id', 
                        'paymentMethod', 'ncf', 'createdUser']
    
    def get_serializer_class(self):
        if self.request.method == 'PUT':
            return serializers.InvoicesHeaderReducedSerializer
        return serializers.InvoicesHeaderSerializer


class InvoicesDetailViewSet(ModelViewSet):
    queryset = InvoicesDetail.objects.select_related('product').select_related('invoice').all()
    serializer_class = serializers.InvoicesDetailSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['id', 'invoice', 'invoice_id', 'product', 'product_id', 'creationDate']

    def get_serializer_class(self):
        if self.request.method == 'PUT':
            return serializers.InvoicesDetailReducedSerializer
        return serializers.InvoicesDetailSerializer


class InvoicesDetailReducedViewSet(ModelViewSet):
    queryset = InvoicesDetail.objects.select_related('product').all()
    serializer_class = serializers.InvoicesDetailReducedSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['id', 'product', 'creationDate']

    
class InvoicesSequenceViewSet(ModelViewSet):
    queryset = InvoicesSequence.objects.select_related('company').all()
    serializer_class = serializers.InvoicesSequenceSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['id', 'company', 'company_id', 'sequence', 'createdUser']

    def get_serializer_class(self):
        if self.request.method == 'PUT':
            return serializers.InvoicesSequenceReducedSerializer
        return serializers.InvoicesSequenceSerializer


class InvoicesHeaderListFull(ModelViewSet):
    queryset = InvoicesHeader.objects.select_related('company').select_related('customer').all()
    serializer_class = serializers.InvoicesHeaderSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['id', 'company', 'company_id', 'customer', 'sequence',  'customer_id', 
                        'paymentMethod', 'ncf', 'createdUser']

    
class InvoicesLeadsHeaderViewSet(ModelViewSet):
    queryset = InvoicesLeadHeader.objects.prefetch_related('company').prefetch_related('invoice').all()
    serializer_class = serializers.InvoicesLeadHeaderSerializer
    pagination_class = StandardResultsSetPaginationHigh
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['id', 'invoice', 'invoice_id', 'creationDate']
    # permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'PUT':
            return serializers.InvoicesLeadHeaderReducedSerializer
        return serializers.InvoicesLeadHeaderSerializer


class InvoicesLeadsDetailViewSet(ModelViewSet):
    queryset = InvoicesLeadDetail.objects.select_related('header').select_related('product').all()
    serializer_class = serializers.InvoicesLeadDetailSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['id', 'header', 'header_id', 'product', 'product_id', 'creationDate']

    def get_serializer_class(self):
        if self.request.method == 'PUT':
            return serializers.InvoicesLeadDetailReducedSerializer
        return serializers.InvoicesLeadDetailSerializer