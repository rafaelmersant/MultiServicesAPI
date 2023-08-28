""" Sales serializers. """

# Django REST framework
from logging import exception
from rest_framework import serializers

from administration.models import Customer

# Models
from .models import InvoicesHeader, InvoicesDetail, InvoicesSequence, \
    InvoicesLeadHeader, InvoicesLeadDetail, QuotationsHeader, QuotationsDetail, Points

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
                  'createdUser', 'sequence', 'paid', 'printed', 'subtotal', 'itbis','discount', 'cost', 'reference',
                  'serverDate', 'invoiceType', 'invoiceStatus', 'amount_points')
   

class InvoicesHeaderCreateSerializer(serializers.ModelSerializer):
    company_id = serializers.IntegerField()
    customer_id = serializers.IntegerField()

    class Meta:
        model = InvoicesHeader
        fields = ('id', 'company_id', 'customer_id', 'paymentMethod',  'ncf', 'creationDate', 'createdUser', 
        'sequence', 'paid', 'printed', 'subtotal', 'itbis','discount', 'cost', 'reference', 'serverDate',
        'invoiceType', 'invoiceStatus', 'amount_points')
        
    def create(self, validated_data):
        superavit_points = 125
        points_type = "E"
        total_points = validated_data['amount_points'] // superavit_points
        invoice = InvoicesHeader.objects.create(**validated_data)
        
        if (invoice.paymentMethod == 'POINTS'):
            points_type = "R"
            total_points = validated_data['discount'] * -1
            invoice.paid = True
            invoice.save()

        if (points_type == "E" and total_points > 0 and invoice.customer_id != 1) or \
            (points_type == "R" and total_points < 0 and invoice.customer_id != 1):
            points = Points()
            points.customer = Customer.objects.get(pk=validated_data['customer_id'])
            points.invoice = InvoicesHeader.objects.get(pk=invoice.id) 
            points.invoice_amount = invoice.subtotal
            points.total_points = total_points 
            points.type = points_type
            points.createdUser = validated_data['createdUser']
            points.save()
            
        return invoice


class InvoicesHeaderUpdateSerializer(serializers.ModelSerializer):
    company_id = serializers.IntegerField()
    customer_id = serializers.IntegerField()

    class Meta:
        model = InvoicesHeader
        fields = ('id', 'company_id', 'customer_id', 'paymentMethod',  'ncf', 'sequence', 'paid', 
        'printed', 'subtotal', 'itbis','discount', 'cost', 'reference', 'invoiceType', 'invoiceStatus',
        'amount_points')
    
    def update(self, instance, validated_data):
        if validated_data['paymentMethod'] != 'POINTS':
            total_points = validated_data['amount_points'] // 125
            points = Points.objects.filter(invoice__id=instance.id)
        
            if points.exists():
                _points = Points.objects.get(id=points[0].id)
                _points.invoice_amount = validated_data['amount_points']
                _points.total_points = total_points
                _points.save()
            else:
                invoice = InvoicesHeader.objects.filter(sequence=validated_data['sequence'])[0]
                
                if total_points > 0 and invoice.customer_id != 1:
                    points = Points()
                    points.customer = Customer.objects.get(pk=validated_data['customer_id'])
                    points.invoice = invoice
                    points.invoice_amount = validated_data['amount_points']
                    points.total_points = total_points
                    points.type = "E"
                    points.createdUser = points.invoice.createdUser
                    points.save()
            
        return super().update(instance, validated_data)


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
    
    created_user_name = serializers.CharField(max_length=255)

    class Meta:
        model = InvoicesHeader
        fields = ('id', 'company_id', 'company_address', 'company_rnc', 'company_phoneNumber', 'company_email',
                  'customer_id', 'customer_firstName', 'customer_lastName', 'customer_email', 'customer_address',
                  'customer_identification', 'paymentMethod', 'sequence', 'ncf', 'paid', 'printed', 'subtotal', 'itbis',
                  'discount', 'cost', 'reference', 'serverDate', 'creationDate', 'createdUser', 'created_user_name',
                  'invoiceType', 'invoiceStatus', 'amount_points')


class InvoicesHeaderMinimumSerializer(serializers.ModelSerializer):    
    company_id = serializers.IntegerField()
    customer_id = serializers.IntegerField()
    
    class Meta:
        model = InvoicesHeader
        fields = ('id', 'company_id', 'customer_id', 'paymentMethod', 'sequence', 'ncf', 'paid', 'printed',
                  'subtotal', 'itbis', 'discount', 'cost', 'reference', 'serverDate', 'creationDate', 'createdUser',
                  'invoiceType', 'invoiceStatus', 'amount_points')


class InvoicesEmployeeSalesSerializer(serializers.Serializer):
    subtotal = serializers.DecimalField(max_digits=18, decimal_places=6, default=0)
    itbis = serializers.DecimalField(max_digits=18, decimal_places=6, default=0)
    cost = serializers.DecimalField(max_digits=18, decimal_places=6, default=0)
    discount = serializers.DecimalField(max_digits=18, decimal_places=6, default=0)
    createdUser = serializers.CharField(max_length=255)


class InvoicesDetailSerializer(serializers.ModelSerializer):
    invoice = InvoicesHeaderUpdateSerializer(many=False, read_only=True)
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


# QuotationsHeader --> Cotizaciones
class QuotationsHeaderSerializer(serializers.ModelSerializer):
    company = CompanySerializer(read_only=True)
    customer = CustomerReducedSerializer(read_only=True)

    class Meta:
        model = QuotationsHeader
        fields = ('id', 'company', 'company_id', 'customer', 'customer_id', 'reference', 'printed',
                  'subtotal', 'discount', 'itbis', 'creationDate', 'createdUser', 'serverDate')


class QuotationsHeaderReducedSerializer(serializers.ModelSerializer):
    company_id = serializers.IntegerField()
    customer_id = serializers.IntegerField()

    class Meta:
        model = QuotationsHeader
        fields = ('id', 'company_id', 'customer_id', 'reference', 'printed', 'subtotal', 'discount',
                  'itbis', 'creationDate', 'createdUser', 'serverDate')


# QuotationsDetail --> Cotizaciones
class QuotationsDetailSerializer(serializers.ModelSerializer):
    header = QuotationsHeaderReducedSerializer(read_only=True)
    header_id = serializers.IntegerField(write_only=True)
    product = ProductReducedSerializer(read_only=True)
    product_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = QuotationsDetail
        fields = ('id', 'header', 'header_id', 'product', 'product_id', 'quantity', 'price',
                  'cost', 'discount', 'itbis', 'creationDate')


class QuotationsDetailReducedSerializer(serializers.ModelSerializer):
    header_id = serializers.IntegerField()
    product_id = serializers.IntegerField()

    class Meta:
        model = QuotationsDetail
        fields = ('id', 'header_id', 'product_id', 'quantity', 'price',
                  'cost', 'discount', 'itbis', 'creationDate')



class InvoicesCustomerSerializer(serializers.Serializer):
    subtotal = serializers.DecimalField(max_digits=18, decimal_places=6, default=0)
    itbis = serializers.DecimalField(max_digits=18, decimal_places=6, default=0)
    cost = serializers.DecimalField(max_digits=18, decimal_places=6, default=0)
    discount = serializers.DecimalField(max_digits=18, decimal_places=6, default=0)
    customer_name = serializers.CharField(max_length=255)


class PointsSerializer(serializers.ModelSerializer):
    customer = CustomerReducedSerializer(many=False, read_only=True)
    invoice = InvoicesHeaderMinimumSerializer(many=False, read_only=True)

    class Meta:
        model = Points
        fields = ('id', 'customer', 'invoice', 'invoice_amount', 'total_points', 'type',
                  'reference', 'creationDate', 'createdUser')