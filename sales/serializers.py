from .models import InvoicesHeader, InvoicesDetail, InvoicesSequence, \
    InvoicesLeadHeader, InvoicesLeadDetail, QuotationsHeader, \
    QuotationsDetail, QuotationsSequence
from products.serializers import CompanySerializer, ProductSerializer
from administration.serializers import CustomerSerializer
from rest_framework import serializers


class InvoicesHeaderSerializer(serializers.HyperlinkedModelSerializer):
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


class InvoicesDetailSerializer(serializers.HyperlinkedModelSerializer):
    invoice = InvoicesHeaderSerializer(many=False, read_only=True)
    invoice_id = serializers.IntegerField(write_only=True)

    product = ProductSerializer(many=False, read_only=True)
    product_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = InvoicesDetail
        fields = ('id', 'invoice', 'invoice_id', 'product', 'product_id',
                  'quantity', 'price', 'itbis', 'cost', 'discount',
                  'creationDate')


class InvoicesSequenceSerializer(serializers.HyperlinkedModelSerializer):
    company = CompanySerializer(many=False, read_only=True)
    company_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = InvoicesSequence
        fields = ('id', 'company', 'company_id', 'sequence',
                  'creationDate', 'createdUser')


# InvoiceLead --> Conduces
class InvoicesLeadHeaderSerializer(serializers.HyperlinkedModelSerializer):
    company = CompanySerializer(many=False, read_only=True)
    company_id = serializers.IntegerField(write_only=True)

    customer = CustomerSerializer(many=False, read_only=True)
    customer_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = InvoicesLeadHeader
        fields = ('id', 'company', 'company_id', 'customer', 'customer_id',
                  'paymentMethod',  'ncf', 'creationDate', 'createdUser',
                  'sequence', 'paid', 'printed', 'subtotal', 'itbis',
                  'discount', 'reference', 'serverDate')


class InvoicesLeadDetailSerializer(serializers.HyperlinkedModelSerializer):
    invoice = InvoicesLeadHeaderSerializer(many=False, read_only=True)
    invoice_id = serializers.IntegerField(write_only=True)

    product = ProductSerializer(many=False, read_only=True)
    product_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = InvoicesLeadDetail
        fields = ('id', 'invoice', 'invoice_id', 'product', 'product_id',
                  'quantity', 'price', 'itbis', 'cost', 'discount',
                  'creationDate')
