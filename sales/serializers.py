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


class InvoicesHeaderUpdateSerializer(serializers.ModelSerializer):
    company_id = serializers.IntegerField()
    customer_id = serializers.IntegerField()

    class Meta:
        model = InvoicesHeader
        fields = ('id', 'company_id', 'customer_id', 'paymentMethod',  'ncf', 'creationDate', 
                  'createdUser', 'sequence', 'paid', 'printed', 'subtotal', 'itbis','discount', 'reference', 'serverDate')


class InvoicesHeaderReducedSerializer(serializers.ModelSerializer):    
    company_id = serializers.IntegerField()
    company_address = serializers.CharField(max_length=255)
    company_rnc = serializers.CharField(max_length=20)
    company_phoneNumber = serializers.CharField(max_length=50)
    company_email = serializers.EmailField()
    
    customer_id = serializers.IntegerField()
    customer_firstName = serializers.CharField(max_length=100)
    customer_lastName = serializers.CharField(max_length=100)
    customer_email = serializers.EmailField()
    customer_address = serializers.CharField(max_length=200)
    customer_identification = serializers.CharField(max_length=20)

    class Meta:
        model = InvoicesHeader
        fields = ('id', 'company_id', 'company_address', 'company_rnc', 'company_phoneNumber', 'company_email',
                  'customer_id', 'customer_firstName', 'customer_lastName', 'customer_email', 'customer_address',
                  'customer_identification', 'paymentMethod', 'sequence', 'ncf', 'paid', 'printed', 'subtotal', 'itbis',
                  'discount', 'reference', 'serverDate', 'creationDate')


class InvoicesDetailSerializer(serializers.ModelSerializer):
    invoice = InvoicesHeaderReducedSerializer(many=False, read_only=True)
    invoice_id = serializers.IntegerField(write_only=True)

    product = ProductReducedSerializer(many=False, read_only=True)
    product_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = InvoicesDetail
        fields = ('id', 'invoice', 'invoice_id', 'product', 'product_id', 'quantity', 'price', 
                  'itbis', 'cost', 'discount', 'creationDate')


class InvoicesDetailSimpleSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    invoice_id = serializers.IntegerField()
    product_id = serializers.IntegerField()
    product_description = serializers.CharField(max_length=255)
    quantity = serializers.DecimalField(max_digits=18,decimal_places=6)
    price = serializers.DecimalField(max_digits=18,decimal_places=6)
    cost = serializers.DecimalField(max_digits=18,decimal_places=6)
    itbis = serializers.DecimalField(max_digits=18,decimal_places=6)
    discount = serializers.DecimalField(max_digits=18,decimal_places=6)


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


class InvoicesLeadHeaderListSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    customer = serializers.CharField(max_length=200)
    customer_identification = serializers.CharField(max_length=20)
    customer_identification_type = serializers.CharField(max_length=1)
    invoice_no = serializers.IntegerField()
    creationDate = serializers.DateTimeField()
    company_id = serializers.IntegerField()
    # createdByUser = serializers.CharField(max_length=255)


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