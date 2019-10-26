from .models import Product, ProductCategory, ProductsStock, ProductsTracking
from administration.models import Company
from administration.serializers import CompanySerializer
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
                  'measure', 'model', 'creationDate', 'createdUser')


class ProductsStockSerializer(serializers.HyperlinkedModelSerializer):
    company = CompanySerializer(many=False, read_only=True)
    company_id = serializers.IntegerField(write_only=True)

    product = ProductSerializer(many=False, read_only=True)
    product_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = ProductsStock
        fields = ('id', 'company', 'company_id', 'product',
                  'product_id', 'quantityAvailable', 'price', 'cost',
                  'provider', 'quantityHold', 'lastUpdated', 'modifiedUser')


class ProductsTrackingSerializer(serializers.HyperlinkedModelSerializer):
    company = CompanySerializer(many=False, read_only=True)
    company_id = serializers.IntegerField(write_only=True)

    product = ProductSerializer(many=False, read_only=True)
    product_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = ProductsTracking
        fields = ('id', 'company', 'company_id', 'product',
                  'product_id', 'typeTracking', 'concept',
                  'quantity', 'creationDate', 'createdUser')
