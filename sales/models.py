from django.db import models
from administration.models import Company, Customer, User
from products.models import Product


class InvoicesHeader(models.Model):
    companyId = models.ForeignKey(Company, on_delete=models.CASCADE)
    customerId = models.ForeignKey(Customer, on_delete=models.CASCADE)
    paymentMethod = models.CharField(max_length=20)
    creationDate = models.DateTimeField(auto_now_add=True, blank=True)
    createdByUser = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True)
    ncf = models.CharField(max_length=13, null=True, blank=True)
    objects = models.Manager()


class InvoicesDetail(models.Model):
    invoiceId = models.ForeignKey(InvoicesHeader, on_delete=models.CASCADE)
    productId = models.ForeignKey(Product, on_delete=models.CASCADE)
    price = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True)
    cost = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True)
    discount = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True)
    creationDate = models.DateTimeField(auto_now_add=True, blank=True)
    objects = models.Manager()
