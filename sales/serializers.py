""" Sales serializers. """

# Django REST framework
from rest_framework import serializers

from administration.models import Company

# Models
from .models import InvoicesHeader, InvoicesDetail, InvoicesSequence, \
    InvoicesLeadHeader, InvoicesLeadDetail, QuotationsHeader, QuotationsDetail

# Serializers
from products.serializers import CompanySerializer, ProductReducedSerializer, ProductSerializer
from administration.serializers import CustomerReducedSerializer, CustomerSerializer


class InvoicesHeaderSerializer(serializers.ModelSerializer):
    company = CompanySerializer(many=False, read_only=True)
    company_id = serializers.IntegerField(write_only=True)

    customer = CustomerReducedSerializer(many=False, read_only=True)
    customer_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = InvoicesHeader
        fields = ('id', 'company', 'company_id', 'customer', 'customer_id', 'paymentMethod',  'ncf', 'creationDate', 
                  'createdUser', 'sequence', 'paid', 'printed', 'subtotal', 'itbis','discount', 'reference', 'serverDate')


class InvoicesHeaderReducedSerializer(serializers.ModelSerializer):
    company_id = serializers.IntegerField()
    customer_id = serializers.IntegerField()

    class Meta:
        model = InvoicesHeader
        fields = ('id', 'company_id', 'customer_id', 'paymentMethod',  'ncf', 'creationDate', 'createdUser',
                  'sequence', 'paid', 'printed', 'subtotal', 'itbis','discount', 'reference', 'serverDate')


class InvoicesDetailSerializer(serializers.ModelSerializer):
    invoice = InvoicesHeaderReducedSerializer(many=False, read_only=True)
    invoice_id = serializers.IntegerField(write_only=True)

    product = ProductReducedSerializer(many=False, read_only=True)
    product_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = InvoicesDetail
        fields = ('id', 'invoice', 'invoice_id', 'product', 'product_id', 'quantity', 'price', 
                  'itbis', 'cost', 'discount', 'creationDate')


class InvoicesDetailReducedSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField()

    class Meta:
        model = InvoicesDetail
        fields = ('id', 'product_id', 'quantity', 'price', 'itbis', 'cost', 'discount',
                  'creationDate')


class InvoicesSequenceSerializer(serializers.ModelSerializer):
    company = CompanySerializer(many=False, read_only=True)
    company_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = InvoicesSequence
        fields = ('id', 'company', 'company_id', 'sequence', 'creationDate', 'createdUser')

    def save(self, **kwargs):
        try:
            company_id = self.validated_data['company_id']            
            sequence = InvoicesSequence.objects.get(company__id=company_id)
            return sequence
            # raise serializers.ValidationError("This company already has a sequence.")
        except InvoicesSequence.DoesNotExist:
            return super().save(**kwargs)


class InvoicesSequenceReducedSerializer(serializers.ModelSerializer):
    company_id = serializers.IntegerField()

    class Meta:
        model = InvoicesSequence
        fields = ('id', 'company_id', 'sequence', 'creationDate', 'createdUser')


# InvoiceLeadHeader --> Conduces
class InvoicesLeadHeaderSerializer(serializers.ModelSerializer):
    invoice = InvoicesHeaderReducedSerializer(read_only=True)
    invoice_id = serializers.IntegerField(write_only=True)

    company = CompanySerializer(read_only=True)
    company_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = InvoicesLeadHeader
        fields = ('id', 'invoice', 'invoice_id', 'company', 'company_id', 'creationDate')


class InvoicesLeadHeaderReducedSerializer(serializers.ModelSerializer):
    invoice_id = serializers.IntegerField()
    company_id = serializers.IntegerField()

    class Meta:
        model = InvoicesLeadHeader
        fields = ('id', 'invoice_id', 'company_id', 'creationDate')


# InvoiceLeadDetail --> Conduces
class InvoicesLeadDetailSerializer(serializers.ModelSerializer):
    header = InvoicesLeadHeaderReducedSerializer(many=False, read_only=True)
    header_id = serializers.IntegerField(write_only=True)

    product = ProductReducedSerializer(many=False, read_only=True)
    product_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = InvoicesLeadDetail
        fields = ('id', 'header', 'header_id', 'product', 'product_id', 'quantity', 'creationDate')


class InvoicesLeadDetailReducedSerializer(serializers.ModelSerializer):
    header_id = serializers.IntegerField()
    product_id = serializers.IntegerField()

    class Meta:
        model = InvoicesLeadDetail
        fields = ('id', 'header_id', 'product_id', 'quantity', 'creationDate')