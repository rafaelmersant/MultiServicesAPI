""" Sales views. """

# Django
from django_filters.rest_framework import DjangoFilterBackend

# Django REST framework
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

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

    def create(self, request, *args, **kwargs):
        serializer = serializers.InvoicesSequenceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        sequence = serializer.save()
        serializer = serializers.InvoicesSequenceSerializer(sequence)
        return Response(serializer.data)

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
    pagination_class = StandardResultsSetPaginationHigh
    filter_backends = [SearchFilter,]
    filterset_fields = ['id', 'invoice', 'invoice_id', 'creationDate']
    # permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        company = self.request.query_params.get('company', None)
        id = self.request.query_params.get('id', None)

        if self.request.method == 'PUT':
            return serializers.InvoicesLeadHeaderReducedSerializer
        elif self.request.method == 'GET' and (company is not None or id is not None):
            return serializers.InvoicesLeadHeaderListSerializer
        return serializers.InvoicesLeadHeaderSerializer
    
    def get_queryset(self):
        company_id = self.request.query_params.get('company', None)
        invoice_id = self.request.query_params.get('invoice', None)
        id = self.request.query_params.get('id', None)

        query = """
                select h.id, c.firstName || ' ' || c.lastName customer, i.sequence invoice_no, h.creationDate, h.company_id
                        from sales_invoicesLeadHeader h
                        inner join sales_invoicesheader i on i.id = h.invoice_id
                        inner join administration_customer c on c.id = i.customer_id
                        where h.id = {id} and h.company_id = {company_id} and i.id = {invoice_sequence}
                        order by h.creationDate desc
                """
        if company_id is not None:
            query = query.replace("{company_id}", company_id)
        else:
            query = query.replace(" and h.company_id = {company_id}", "")
        if invoice_id is not None:
            query = query.replace("{invoice_sequence}", invoice_id)
        else:
            query = query.replace("and i.id = {invoice_sequence}", "")
        
        if id is not None:
            query = query.replace("{id}", id)
        else:
            query = query.replace("h.id = {id} and", "")

        self.queryset = InvoicesLeadHeader.objects.raw(query)
        
        return self.queryset


class InvoicesLeadsDetailViewSet(ModelViewSet):
    queryset = InvoicesLeadDetail.objects.select_related('header').select_related('product').all()
    serializer_class = serializers.InvoicesLeadDetailSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['id', 'header', 'header_id', 'product', 'product_id', 'creationDate']

    def get_serializer_class(self):
        if self.request.method == 'PUT':
            return serializers.InvoicesLeadDetailReducedSerializer
        return serializers.InvoicesLeadDetailSerializer