""" Administration serializers. """

# Django REST framework
from rest_framework import serializers

# Models
from .models import Company, User, Customer, FiscalGov, Provider


class CompanySerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = Company
        fields = ('id', 'name', 'email', 'phoneNumber', 'rnc',
                  'address', 'creationDate', 'createdUser')


class UserSerializer(serializers.HyperlinkedModelSerializer):
    company = CompanySerializer(many=False, read_only=True)
    company_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = User
        fields = ('id', 'company', 'company_id', 'email',
                  'name', 'creationDate', 'createdUser',
                  'userHash', 'userRole', 'password')


class CustomerSerializer(serializers.HyperlinkedModelSerializer):
    company = CompanySerializer(many=False, read_only=True)
    company_id = serializers.IntegerField()

    class Meta:
        model = Customer
        fields = ('id', 'company', 'company_id', 'firstName',
                  'lastName', 'email', 'phoneNumber', 'address',
                  'identification', 'identificationType',
                  'creationDate', 'createdUser')


class ProviderSerializer(serializers.HyperlinkedModelSerializer):
    company = CompanySerializer(many=False, read_only=True)
    company_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Provider
        fields = ('id', 'company', 'company_id', 'firstName',
                  'lastName', 'email', 'phoneNumber', 'address',
                  'rnc', 'creationDate', 'createdUser', 'name')


class FiscalGovSerializer(serializers.HyperlinkedModelSerializer):
    company = CompanySerializer(many=False, read_only=True)
    company_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = FiscalGov
        fields = ('id', 'company', 'company_id', 'typeDoc', 'start',
                  'end', 'current', 'dueDate', 'active', 'usedInInvoice',
                  'creationDate', 'createdUser')
