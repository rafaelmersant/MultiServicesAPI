""" Sales views. """

# Django
from django_filters.rest_framework import DjangoFilterBackend

# Django REST framework
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from MultiServices.paginations import InvoiceListPagination, StandardResultsSetPaginationHigh

# Serializers
from . import serializers

# Models
from .models import InvoicesHeader, InvoicesDetail, InvoicesSequence, InvoicesLeadHeader, InvoicesLeadDetail

class InvoicesHeaderViewSet(ModelViewSet):
    queryset = InvoicesHeader.objects.select_related('company').select_related('customer').all()
    serializer_class = serializers.InvoicesHeaderSerializer
    pagination_class = InvoiceListPagination
    filter_backends = [SearchFilter, OrderingFilter]
    filterset_fields = ['id', 'company', 'company_id', 'customer', 'sequence', 'customer_id', 
                        'paymentMethod', 'ncf', 'createdUser']
    
    def get_serializer_class(self):
        sequence = self.request.query_params.get('sequence', None)
        
        if self.request.method == 'PUT' or self.request.method == 'POST':
            return serializers.InvoicesHeaderUpdateSerializer
        elif self.request.method == 'GET' and sequence is not None:
            return serializers.InvoicesHeaderReducedSerializer
        return serializers.InvoicesHeaderSerializer

    def get_queryset(self):
        sequence = self.request.query_params.get('sequence', None)
        
        if sequence is not None:
            query = """
                    select h.id, h.company_id, m.address company_address, m.rnc company_rnc, m.email company_email, m.phoneNumber company_phoneNumber, 
                                customer_id, c.firstName customer_firstName, c.lastName customer_lastName, c.identification customer_identification, 
                                c.address customer_address, c.email customer_email, h.paymentMethod, h.ncf, h.createdUser, h.creationDate, 
                                h.sequence, h.paid, h.printed, h.subtotal, h.itbis, h.discount, h.reference, h.serverDate
                        from sales_invoicesheader h
                        inner join administration_customer c on c.id = h.customer_id
                        inner join administration_company m on m.id = h.company_id
                        where h.sequence = {sequence}
                    """
            if sequence is not None:
                query = query.replace("{sequence}", sequence)
            else:
                query = query.replace("where h.sequence = {sequence}", "")
           
            return InvoicesHeader.objects.raw(query)
        
        return self.queryset


class InvoicesHeaderCustomerViewSet(ModelViewSet):
    queryset = InvoicesHeader.objects.select_related('company').select_related('customer').all()
    serializer_class = serializers.InvoicesHeaderSerializer
    pagination_class = InvoiceListPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['id', 'company', 'company_id', 'customer', 'sequence', 'customer_id', 
                        'paymentMethod', 'ncf', 'createdUser']
    
    def get_serializer_class(self):
        sequence = self.request.query_params.get('sequence', None)
        
        if self.request.method == 'PUT' or self.request.method == 'POST':
            return serializers.InvoicesHeaderUpdateSerializer
        elif self.request.method == 'GET' and sequence is not None:
            return serializers.InvoicesHeaderReducedSerializer
        return serializers.InvoicesHeaderSerializer

    def get_queryset(self):
        sequence = self.request.query_params.get('sequence', None)
        
        if sequence is not None:
            query = """
                    select h.id, h.company_id, m.address company_address, m.rnc company_rnc, m.email company_email, m.phoneNumber company_phoneNumber, 
                                customer_id, c.firstName customer_firstName, c.lastName customer_lastName, c.identification customer_identification, 
                                c.address customer_address, c.email customer_email, h.paymentMethod, h.ncf, h.createdUser, h.creationDate, 
                                h.sequence, h.paid, h.printed, h.subtotal, h.itbis, h.discount, h.reference, h.serverDate
                        from sales_invoicesheader h
                        inner join administration_customer c on c.id = h.customer_id
                        inner join administration_company m on m.id = h.company_id
                        where h.sequence = {sequence}
                    """
            if sequence is not None:
                query = query.replace("{sequence}", sequence)
            else:
                query = query.replace("where h.sequence = {sequence}", "")
           
            return InvoicesHeader.objects.raw(query)
        
        return self.queryset

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


class InvoicesDetailSimpleViewSet(ModelViewSet):
    filter_backends = [SearchFilter,]
    filterset_fields = ['id', 'invoice_id', 'creationDate']
    
    def get_serializer_class(self):
        invoice = self.request.query_params.get('invoice', None)
        
        if self.request.method == 'GET' and (invoice is not None):
            return serializers.InvoicesDetailSimpleSerializer
        if self.request.method == 'PUT' or self.request.method == 'POST':
            return serializers.InvoicesDetailReducedSerializer
        return serializers.InvoicesDetailSerializer
    
    def get_queryset(self):
        invoice = self.request.query_params.get('invoice', None)
       
        query = """
                select d.id, d.invoice_id, d.product_id, p.description as product_description, d.quantity, d.price, d.cost, d.itbis, d.discount
                        from sales_invoicesdetail d
                        inner join products_product p on p.id = d.product_id
                        where d.invoice_id = {invoice_id}
                        order by d.id
                """
        if invoice is not None:
            query = query.replace("{invoice_id}", invoice)
        else:
            query = query.replace("where d.invoice_id = {invoice_id}", "")
        
        queryset = InvoicesDetail.objects.raw(query)
        
        return queryset


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
                        'paymentMethod', 'ncf', 'createdUser', 'creationDate']
    
    def get_queryset(self):
        year = self.request.query_params.get("year", None)

        if (year is not None):
            self.queryset = self.queryset.filter(creationDate__year=year)
        
        return self.queryset

    
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
                select h.id, c.firstName || ' ' || c.lastName customer, i.sequence invoice_no, h.creationDate, h.company_id,
                        c.identification customer_identification, c.identificationType customer_identification_type
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