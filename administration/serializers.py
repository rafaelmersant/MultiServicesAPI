""" Administration serializers. """

# Django REST framework
from rest_framework import serializers

# Models
from .models import Company, User, Customer, FiscalGov, Provider


class CompanySerializer(serializers.ModelSerializer):

    class Meta:
        model = Company
        fields = ('id', 'name', 'email', 'phoneNumber', 'rnc',
                  'address', 'creationDate', 'createdUser')


class UserSerializer(serializers.ModelSerializer):
    company = CompanySerializer(many=False, read_only=True)
    company_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = User
        fields = ('id', 'company', 'company_id', 'email',
                  'name', 'creationDate', 'createdUser',
                  'userHash', 'userRole', 'password')


class CustomerSerializer(serializers.ModelSerializer):
    company = CompanySerializer(many=False, read_only=True)
    company_id = serializers.IntegerField()

    class Meta:
        model = Customer
        fields = ('id', 'company', 'company_id', 'firstName', 'lastName', 'email', 'phoneNumber', 'address',
                  'identification', 'identificationType', 'creationDate', 'createdUser')


class CustomerReducedSerializer(serializers.ModelSerializer):
    company_id = serializers.IntegerField()

    class Meta:
        model = Customer
        fields = ('id', 'company_id', 'firstName', 'lastName', 'email', 'phoneNumber', 'address',
                  'identification', 'identificationType', 'creationDate', 'createdUser')


class ProviderSerializer(serializers.ModelSerializer):
    company = CompanySerializer(many=False, read_only=True)
    company_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Provider
        fields = ('id', 'company', 'company_id', 'firstName',
                  'lastName', 'email', 'phoneNumber', 'address',
                  'rnc', 'creationDate', 'createdUser', 'name')


class ProviderReducedSerializer(serializers.ModelSerializer):
    company_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Provider
        fields = ('id', 'company_id', 'firstName',
                  'lastName', 'email', 'phoneNumber', 'address',
                  'rnc', 'creationDate', 'createdUser', 'name')


class FiscalGovSerializer(serializers.ModelSerializer):
    company = CompanySerializer(many=False, read_only=True)
    company_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = FiscalGov
        fields = ('id', 'company', 'company_id', 'typeDoc', 'start',
                  'end', 'current', 'dueDate', 'active', 'usedInInvoice',
                  'creationDate', 'createdUser')
