from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from .models import Company, User, Customer, FiscalGov
from .serializers import CompanySerializer, UserSerializer, \
    CustomerSerializer, FiscalGovSerializer
import json


class CompanyList(generics.ListCreateAPIView):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['id', 'name', 'rnc', 'creationDate']

    def delete(self, request, pk=None):
        try:
            company = Company.objects.get(pk=pk)
            company.delete()
        except Company.DoesNotExist:
            return Response("company does not exist",
                            status=status.HTTP_404_NOT_FOUND)
        except:
            return Response("Internal Server Error",
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response("deleted", status=status.HTTP_200_OK)

    def put(self, request, pk, format=None):
        company = Company.objects.get(pk=pk)
        serializer = CompanySerializer(company, data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserList(generics.ListCreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['id', 'email', 'name',
                        'userRole', 'userHash', 'creationDate']

    def delete(self, request, pk=None):
        try:
            user = User.objects.get(pk=pk)
            user.delete()
        except User.DoesNotExist:
            return Response("user does not exist",
                            status=status.HTTP_404_NOT_FOUND)
        except:
            return Response("the user was not found",
                            status=status.HTTP_400_BAD_REQUEST)

        return Response("deleted", status=status.HTTP_200_OK)

    def put(self, request, pk, format=None):
        user = User.objects.get(pk=pk)
        serializer = UserSerializer(user, data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserLogin(generics.ListCreateAPIView):
    serializer_class = UserSerializer

    def post(self, request):
        try:
            body_unicode = request.body.decode('utf-8')
            body = json.loads(body_unicode)
            email = body['email']
            password = body['password']

            user = User.objects.filter(email=email, password=password)

            if user.count() > 0:
                return Response({"id": user[0].id,
                                 "email": user[0].email,
                                 "name": user[0].name,
                                 "role": user[0].userRole,
                                 "companyId": user[0].company.id},
                                status=status.HTTP_200_OK)

            return Response("null", status=status.HTTP_404_NOT_FOUND)

        except User.DoesNotExist:
            return Response("Not Found", status=status.HTTP_404_NOT_FOUND)
        except:
            return Response("Bad Request",
                            status=status.HTTP_400_BAD_REQUEST)


class CustomerList(generics.ListCreateAPIView):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['id', 'firstName', 'lastName',
                        'email', 'company_id', 'phoneNumber', 'creationDate']

    def delete(self, request, pk=None):
        try:
            customer = Customer.objects.get(pk=pk)
            customer.delete()
        except Customer.DoesNotExist:
            return Response("customer does not exist",
                            status=status.HTTP_404_NOT_FOUND)
        except:
            return Response("Internal Server Error",
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response("deleted", status=status.HTTP_200_OK)

    def put(self, request, pk, format=None):
        customer = Customer.objects.get(pk=pk)
        serializer = CustomerSerializer(customer, data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FiscalGovList(generics.ListCreateAPIView):
    queryset = FiscalGov.objects.all()
    serializer_class = FiscalGovSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['id', 'start', 'end',
                        'company_id', 'createdUser', 'creationDate']

    def delete(self, request, pk=None):
        fiscalgov = FiscalGov.objects.get(pk=pk)
        fiscalgov.delete()
        return Response("deleted", status=status.HTTP_200_OK)

    def put(self, request, pk, format=None):
        fiscalgov = FiscalGov.objects.get(pk=pk)
        serializer = FiscalGovSerializer(fiscalgov, data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
