""" Sales serializers. """

# Django REST framework
from rest_framework import serializers

# Models
from .models import InvoicesHeader, InvoicesDetail, InvoicesSequence, \
    InvoicesLeadHeader, InvoicesLeadDetail, QuotationsHeader, QuotationsDetail

# Serializers
from products.serializers import CompanySerializer, ProductReducedSerializer, ProductSerializer
from administration.serializers import CustomerSerializer


class InvoicesHeaderSerializer(serializers.ModelSerializer):
    """ Invoices header serializer. """

    company = CompanySerializer(many=False, read_only=True)
    company_id = serializers.IntegerField(write_only=True)

    customer = CustomerSerializer(many=False, read_only=True)
    customer_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = InvoicesHeader
        fields = ('id', 'company', 'company_id', 'customer', 'customer_id',
                  'paymentMethod',  'ncf', 'creationDate', 'createdUser',
                  'sequence', 'paid', 'printed', 'subtotal', 'itbis',
                  'discount', 'reference', 'serverDate')


class InvoicesHeaderReducedSerializer(serializers.ModelSerializer):
    company_id = serializers.IntegerField(read_only=True)
    customer_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = InvoicesHeader
        fields = ('id', 'company_id', 'customer_id', 'paymentMethod',  'ncf', 'creationDate', 'createdUser',
                  'sequence', 'paid', 'printed', 'subtotal', 'itbis', 'discount', 'reference', 'serverDate')


class InvoicesDetailSerializer(serializers.ModelSerializer):
    """ Invoices detail serializer. """

    invoice = InvoicesHeaderReducedSerializer(many=False, read_only=True)
    invoice_id = serializers.IntegerField(write_only=True)

    product = ProductReducedSerializer(many=False, read_only=True)
    product_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = InvoicesDetail
        fields = ('id', 'invoice', 'invoice_id', 'product', 'product_id',
                  'quantity', 'price', 'itbis', 'cost', 'discount',
                  'creationDate')


class InvoicesSequenceSerializer(serializers.ModelSerializer):
    """ Invoices sequence serializer. """

    company = CompanySerializer(many=False, read_only=True)
    company_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = InvoicesSequence
        fields = ('id', 'company', 'company_id', 'sequence',
                  'creationDate', 'createdUser')


# InvoiceLeadHeader --> Conduces
class InvoicesLeadHeaderSerializer(serializers.ModelSerializer):
    """ Invoices Lead Header serializer. """

    invoice = InvoicesHeaderReducedSerializer(read_only=True)
    invoice_id = serializers.IntegerField(write_only=True)

    company = CompanySerializer(read_only=True)
    company_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = InvoicesLeadHeader
        fields = ('id', 'invoice', 'invoice_id', 'company', 'company_id', 'creationDate')


class InvoicesLeadHeaderReducedSerializer(serializers.ModelSerializer):
    invoice_id = serializers.IntegerField(write_only=True)
    company_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = InvoicesLeadHeader
        fields = ('id', 'invoice_id', 'company_id', 'creationDate')


# InvoiceLeadDetail --> Conduces
class InvoicesLeadDetailSerializer(serializers.ModelSerializer):
    """ Invoices Lead Detail serializer. """

    header = InvoicesLeadHeaderReducedSerializer(many=False, read_only=True)
    header_id = serializers.IntegerField(write_only=True)

    product = ProductReducedSerializer(many=False, read_only=True)
    product_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = InvoicesLeadDetail
        fields = ('id', 'header', 'header_id', 'product', 'product_id', 'quantity', 'creationDate')
