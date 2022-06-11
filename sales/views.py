""" Sales views. """

# Django
from msilib import sequence
from django_filters.rest_framework import DjangoFilterBackend

# Django REST framework
from rest_framework.decorators import api_view
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from MultiServices.paginations import InvoiceListPagination, StandardResultsSetPaginationHigh

# Serializers
from . import serializers

# Models
from .models import InvoicesHeader, InvoicesDetail, InvoicesSequence, InvoicesLeadHeader, InvoicesLeadDetail, QuotationsDetail, QuotationsHeader

import datetime
from datetime import datetime as date_format


class InvoicesHeaderViewSet(ModelViewSet):
    queryset = InvoicesHeader.objects.select_related('company').select_related('customer').all()
    serializer_class = serializers.InvoicesHeaderSerializer
    pagination_class = InvoiceListPagination
    filter_backends = [SearchFilter, OrderingFilter]
    filterset_fields = ['id', 'company', 'company_id', 'customer', 'sequence', 'customer_id', 
                        'paymentMethod', 'ncf', 'createdUser']
    
    def get_serializer_class(self):
        sequence = self.request.query_params.get('sequence', None)
        
        if self.request.method == 'POST':
            return serializers.InvoicesHeaderCreateSerializer
        elif self.request.method == 'PUT':
            return serializers.InvoicesHeaderUpdateSerializer
        elif self.request.method == 'GET' and sequence is not None:
            return serializers.InvoicesHeaderReducedSerializer
        return serializers.InvoicesHeaderSerializer

    def get_queryset(self):
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)

        _start_date = date_format.strptime(start_date, '%Y-%m-%d')
        _end_date = date_format.strptime(end_date, '%Y-%m-%d')

        if start_date is not None and end_date is not None:
            self.queryset = self.queryset.filter(creationDate__gte=datetime.datetime.combine(_start_date, datetime.time.min), \
                                                creationDate__lte=datetime.datetime.combine(_end_date, datetime.time.max))

        sequence = self.request.query_params.get('sequence', None)

        if sequence is not None:
            query = """
                    select h.id, h.company_id, m.address company_address, m.rnc company_rnc, m.email company_email, 
                                m.phoneNumber company_phoneNumber, customer_id, c.firstName customer_firstName, 
                                c.lastName customer_lastName, c.identification customer_identification, 
                                c.address customer_address, c.email customer_email, h.paymentMethod, h.ncf, h.createdUser, 
                                h.creationDate, h.sequence, h.paid, h.printed, h.subtotal, h.itbis, h.discount, h.cost,
                                h.reference, h.serverDate, h.invoiceType, h.invoiceStatus, u.name created_user_name
                        from sales_invoicesheader h
                        inner join administration_customer c on c.id = h.customer_id
                        inner join administration_company m on m.id = h.company_id
                        inner join administration_user u on u.email = h.createdUser
                        where h.sequence = {sequence}
                    """
            if sequence is not None:
                query = query.replace("{sequence}", sequence)
            else:
                query = query.replace("where h.sequence = {sequence}", "")
           
            return InvoicesHeader.objects.raw(query)
        
        return self.queryset


class InvoicesHeaderSearchViewSet(ModelViewSet):
    http_method_names = ['get']
    queryset = InvoicesHeader.objects.select_related('company').select_related('customer').all()
    serializer_class = serializers.InvoicesHeaderSerializer
    pagination_class = InvoiceListPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['id', 'company', 'company_id', 'customer', 'sequence', 'customer_id', 
                         'paymentMethod', 'ncf', 'createdUser']
    

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
    http_method_names = ['get']
    serializer_class = serializers.InvoicesDetailSimpleSerializer
    filter_backends = [SearchFilter,]
    filterset_fields = ['id', 'invoice_id', 'creationDate']
    
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

        if self.request.method == 'PUT' or self.request.method == 'POST':
            return serializers.InvoicesLeadHeaderReducedSerializer
        elif self.request.method == 'GET' and (company is not None or id is not None):
            return serializers.InvoicesLeadHeaderListSerializer
        return serializers.InvoicesLeadHeaderSerializer
    
    def get_queryset(self):
        company_id = self.request.query_params.get('company', None)
        invoice_id = self.request.query_params.get('invoice', None)
        id = self.request.query_params.get('id', None)

        query = """
                select h.id, CONCAT(c.firstName, ' ', c.lastName) customer, i.sequence invoice_no, 
                        h.creationDate, h.company_id, c.identification customer_identification, 
                        c.identificationType customer_identification_type
                        from sales_invoicesleadheader h
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


class QuotationsHeaderViewSet(ModelViewSet):
    queryset = QuotationsHeader.objects.prefetch_related('company').all()
    pagination_class = StandardResultsSetPaginationHigh
    filter_backends = [DjangoFilterBackend, SearchFilter,]
    filterset_fields = ['id', 'customer', 'creationDate']
    # permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'PUT' or self.request.method == 'POST':
            return serializers.QuotationsHeaderReducedSerializer
        return serializers.QuotationsHeaderSerializer
  

class QuotationsDetailViewSet(ModelViewSet):
    queryset = QuotationsDetail.objects.select_related('header').select_related('product').all()
    serializer_class = serializers.QuotationsDetailSerializer
    filter_backends = [DjangoFilterBackend,]
    filterset_fields = ['id', 'header', 'header_id', 'product', 'product_id', 'creationDate']

    def get_serializer_class(self):
        if self.request.method == 'PUT' or self.request.method == 'POST':
            return serializers.QuotationsDetailReducedSerializer
        return serializers.QuotationsDetailSerializer


class InvoicesCustomerViewSet(ModelViewSet):
    http_method_names = ['get']
    serializer_class = serializers.InvoicesCustomerSerializer

    def get_queryset(self):
       start_date = self.request.query_params.get('start_date', None)
       end_date = self.request.query_params.get('end_date', None)

       if start_date is not None and end_date is not None:
           query = """
                    select 
                        c.id, CONCAT(c.firstName, ' ', c.lastName) customer_name, sum(h.subtotal) subtotal, sum(h.itbis) itbis, 
                        sum(h.cost) cost, sum(h.discount) discount
                    from sales_invoicesheader h
                    inner join administration_customer c on c.id = h.customer_id
                    where DATE(h.creationDate) between '#startDate#' and '#endDate#'
                    group by c.id, CONCAT(c.firstName, ' ', c.lastName)
                    order by sum(h.subtotal) desc
                    """.replace("#startDate#", start_date).replace("#endDate#", end_date)

           return InvoicesHeader.objects.raw(query)


@api_view(['GET','POST'])
def cancel_invoice(request, invoice):
    if request.method == 'POST':
        try:
            invoice_header = InvoicesHeader.objects.get(sequence=invoice)
            invoice_header.subtotal = 0
            invoice_header.discount = 0
            invoice_header.itbis = 0
            invoice_header.cost = 0
            invoice_header.paid = True
            invoice_header.invoiceStatus = 'ANULADA'
            invoice_header.save()

            invoice_details = InvoicesDetail.objects.filter(invoice__id=invoice_header.id)
            for detail in invoice_details:
                detail.price = 0
                detail.discount = 0
                detail.cost = 0
                detail.itbis = 0
                detail.save()

        except InvoicesHeader.DoesNotExist:
            return Response({"message": f"La factura #{invoice} no fue encontrada, favor verificar."})

    return Response({f"message": f"Factura #{invoice} anulada con exito!"})


class EmployeeSalesViewSet(ModelViewSet):
    http_method_names = ['get']
    serializer_class = serializers.InvoicesEmployeeSalesSerializer

    def get_queryset(self):
       start_date = self.request.query_params.get('start_date', None)
       end_date = self.request.query_params.get('end_date', None)

       if start_date is not None and end_date is not None:
           query = """
                    select 
                        u.id, u.name createdUser, sum(h.subtotal) subtotal, sum(h.itbis) itbis, 
                        sum(h.cost) cost, sum(h.discount) discount
                    from sales_invoicesheader h
                    inner join administration_user u on u.email = h.createdUser
                    where DATE(h.creationDate) between '#startDate#' and '#endDate#'
                    group by u.id, u.name
                    """.replace("#startDate#", start_date).replace("#endDate#", end_date)

           return InvoicesHeader.objects.raw(query)