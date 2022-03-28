""" Products serializers. """

# Models
from .models import Product, ProductCategory, ProductsStock, \
    ProductsTracking, ProductsTrackingHeader, PurchaseOrder

# Serializers
from administration.serializers import CompanySerializer, ProviderSerializer

# Django REST framework
from rest_framework import serializers


class ProductCategorySerializer(serializers.ModelSerializer):
    company = CompanySerializer(many=False, read_only=True)
    company_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = ProductCategory
        fields = ('id', 'description', 'company', 'company_id', 'creationDate')


class ProductSerializer(serializers.ModelSerializer):
    company = CompanySerializer(many=False, read_only=True)
    company_id = serializers.IntegerField(write_only=True)

    category = ProductCategorySerializer(many=False, read_only=True)
    category_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Product
        fields = ('id', 'company', 'company_id', 'description', 'descriptionLong', 'price', 'cost', 
                  'itbis', 'category', 'category_id', 'barcode', 'measure', 'model', 'creationDate', 
                  'createdUser', 'minimumStock', 'quantity', 'updated', 'ocurrences')


class ProductReducedSerializer(serializers.ModelSerializer):
    company_id = serializers.IntegerField(write_only=True)
    category_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Product
        fields = ('id', 'company_id', 'description', 'descriptionLong', 'price', 'cost', 
                  'itbis', 'category_id', 'barcode', 'measure', 'model', 'creationDate', 
                  'createdUser', 'minimumStock', 'updated')
    
   
class ProductsStockSerializer(serializers.ModelSerializer):
    company = CompanySerializer(many=False, read_only=True)
    company_id = serializers.IntegerField(write_only=True)

    product = ProductReducedSerializer(many=False, read_only=True)
    product_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = ProductsStock
        fields = ('company', 'company_id', 'product', 'product_id', 'quantityAvailable',
                  'quantityHold', 'lastUpdated', 'modifiedUser')


class ProductsTrackingHeaderSerializer(serializers.ModelSerializer):
    company = CompanySerializer(many=False, read_only=True)
    company_id = serializers.IntegerField(write_only=True)

    provider = ProviderSerializer(many=False, read_only=True)
    provider_id = serializers.IntegerField(write_only=True)
    provider_name = serializers.SerializerMethodField()
        
    class Meta:
        model = ProductsTrackingHeader
        fields = ('id', 'company', 'company_id', 'provider', 'provider_id', 'provider_name', 'docDate', 
                  'totalAmount', 'itbis', 'ncf', 'serverDate', 'creationDate', 'createdUser', 'reference', 'paid')
    
    def get_provider_name(self, tracking: ProductsTrackingHeader):
        return tracking.provider.firstName


class ProductsTrackingSerializer(serializers.ModelSerializer):
    company = CompanySerializer(many=False, read_only=True)
    company_id = serializers.IntegerField(write_only=True)

    product = ProductSerializer(many=False, read_only=True)
    product_id = serializers.IntegerField(write_only=True)

    header = ProductsTrackingHeaderSerializer(many=False, read_only=True)
    header_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = ProductsTracking
        fields = ('id', 'company', 'company_id', 'product',
                  'product_id', 'typeTracking', 'concept',
                  'quantity', 'price', 'cost', 'header',
                  'header_id', 'creationDate', 'createdUser')


class ProductsProviderSerializer(serializers.ModelSerializer):
    product = ProductSerializer(many=False, read_only=True)
    product_id = serializers.IntegerField(write_only=True)

    header = ProductsTrackingHeaderSerializer(many=False, read_only=True)
    header_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = ProductsTracking
        fields = ('id', 'product', 'product_id', 'creationDate',
                  'price', 'cost', 'header','header_id',)


class PurchaseOrderSerializer(serializers.ModelSerializer):
    company = CompanySerializer(many=False, read_only=True)
    company_id = serializers.IntegerField(write_only=True)

    product = ProductSerializer(many=False, read_only=True)
    product_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = PurchaseOrder
        fields = ('id', 'company', 'company_id', 'product',
                  'product_id', 'quantity', 'pending', 'creationDate')
