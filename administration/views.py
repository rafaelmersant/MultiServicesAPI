from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from rest_framework import generics
from .models import Company, User, Customer, FiscalGov
from .serializers import CompanySerializer, UserSerializer, \
    CustomerSerializer, FiscalGovSerializer


class CompanyList(generics.ListCreateAPIView):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['id', 'name', 'rnc']

    def get_object(self):
        data = Company.objects.all()

        obj = get_object_or_404(
            data,
            pk=self.kwargs['pk'],
        )
        return obj


class UserList(generics.ListCreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['id', 'userName', 'email', 'fullName']

    def get_object(self):
        data = User.objects.all()

        obj = get_object_or_404(
            data,
            pk=self.kwargs['pk'],
        )
        return obj


class CustomerList(generics.ListCreateAPIView):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['id', 'firstName', 'lastName',
                        'email', 'company_id', 'phoneNumber']

    def get_object(self):
        data = Customer.objects.all()

        obj = get_object_or_404(
            data,
            pk=self.kwargs['pk'],
        )
        return obj


class FiscalGovList(generics.ListCreateAPIView):
    queryset = FiscalGov.objects.all()
    serializer_class = FiscalGovSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['id', 'start', 'end',
                        'company_id', 'createdByUser']

    def get_object(self):
        data = FiscalGov.objects.all()

        obj = get_object_or_404(
            data,
            pk=self.kwargs['pk'],
        )
        return obj
