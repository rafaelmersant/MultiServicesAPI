""" Products serializers. """

# Models
from .models import Product, ProductCategory, ProductsStock, \
    ProductsTracking, ProductsTrackingHeader, PurchaseOrder
from administration.models import Company

# Serializers
from administration.serializers import CompanySerializer, ProviderSerializer

# Django REST framework
from rest_framework import serializers


class ProductCategorySerializer(serializers.HyperlinkedModelSerializer):
    company = CompanySerializer(many=False, read_only=True)
    company_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = ProductCategory
        fields = ('id', 'description', 'company', 'company_id', 'creationDate')


class ProductSerializer(serializers.HyperlinkedModelSerializer):
    company = CompanySerializer(many=False, read_only=True)
    company_id = serializers.IntegerField(write_only=True)

    category = ProductCategorySerializer(many=False, read_only=True)
    category_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Product
        fields = ('id', 'company', 'company_id',
                  'description', 'descriptionLong', 'price',
                  'cost', 'itbis', 'category', 'category_id', 'barcode',
                  'measure', 'model', 'creationDate', 'createdUser',
                  'minimumStock', 'quantity', 'ocurrences', 'updated')


class ProductsStockSerializer(serializers.HyperlinkedModelSerializer):
    company = CompanySerializer(many=False, read_only=True)
    company_id = serializers.IntegerField(write_only=True)

    product = ProductSerializer(many=False, read_only=True)
    product_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = ProductsStock
        fields = ('id', 'company', 'company_id', 'product',
                  'product_id', 'quantityAvailable',
                  'quantityHold', 'lastUpdated', 'modifiedUser')


class ProductsTrackingHeaderSerializer(serializers.HyperlinkedModelSerializer):
    company = CompanySerializer(many=False, read_only=True)
    company_id = serializers.IntegerField(write_only=True)

    provider = ProviderSerializer(many=False, read_only=True)
    provider_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = ProductsTrackingHeader
        fields = ('id', 'company', 'company_id', 'provider',
                  'provider_id', 'docDate', 'totalAmount',
                  'itbis', 'ncf', 'serverDate',
                  'creationDate', 'createdUser',
                  'reference', 'paid')


class ProductsTrackingSerializer(serializers.HyperlinkedModelSerializer):
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


class ProductsProviderSerializer(serializers.HyperlinkedModelSerializer):
    product = ProductSerializer(many=False, read_only=True)
    product_id = serializers.IntegerField(write_only=True)

    header = ProductsTrackingHeaderSerializer(many=False, read_only=True)
    header_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = ProductsTracking
        fields = ('id', 'product', 'product_id', 'creationDate',
                  'price', 'cost', 'header',
                  'header_id',)


class PurchaseOrderSerializer(serializers.HyperlinkedModelSerializer):
    company = CompanySerializer(many=False, read_only=True)
    company_id = serializers.IntegerField(write_only=True)

    product = ProductSerializer(many=False, read_only=True)
    product_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = PurchaseOrder
        fields = ('id', 'company', 'company_id', 'product',
                  'product_id', 'quantity', 'pending', 'creationDate')
