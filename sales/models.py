from django.db import models
from administration.models import Company, Customer, User
from products.models import Product


class InvoicesHeader(models.Model):
    sequence = models.IntegerField()
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    paymentMethod = models.CharField(max_length=20)
    ncf = models.CharField(max_length=13, null=True, blank=True)
    paid = models.BooleanField(default=True)
    reference = models.CharField(max_length=50, blank=True)
    subtotal = models.DecimalField(
        max_digits=18, decimal_places=6, default=0)
    discount = models.DecimalField(
        max_digits=18, decimal_places=6, default=0)
    itbis = models.DecimalField(
        max_digits=18, decimal_places=6, default=0)
    creationDate = models.DateTimeField()
    createdUser = models.EmailField(null=True, blank=True)
    serverDate = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    printed = models.BooleanField(default=False)
    objects = models.Manager()


class InvoicesDetail(models.Model):
    invoice = models.ForeignKey(InvoicesHeader, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.DecimalField(
        max_digits=18, decimal_places=6, default=0)
    price = models.DecimalField(
        max_digits=18, decimal_places=6, default=0)
    cost = models.DecimalField(
        max_digits=18, decimal_places=6, default=0)
    itbis = models.DecimalField(
        max_digits=18, decimal_places=6, default=0)
    discount = models.DecimalField(
        max_digits=18, decimal_places=6, default=0)
    creationDate = models.DateTimeField(auto_now_add=True, blank=True)
    objects = models.Manager()


class InvoicesSequence(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    sequence = models.IntegerField()
    creationDate = models.DateTimeField(auto_now_add=True, blank=True)
    createdUser = models.EmailField(null=True, blank=True)
    objects = models.Manager()


class QuotationsHeader(models.Model):
    sequence = models.IntegerField()
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    paymentMethod = models.CharField(max_length=20)
    reference = models.CharField(max_length=50, blank=True)
    subtotal = models.DecimalField(
        max_digits=18, decimal_places=6, default=0)
    discount = models.DecimalField(
        max_digits=18, decimal_places=6, default=0)
    itbis = models.DecimalField(
        max_digits=18, decimal_places=6, default=0)
    creationDate = models.DateTimeField()
    createdUser = models.EmailField(null=True, blank=True)
    serverDate = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    printed = models.BooleanField(default=False)
    objects = models.Manager()


class QuotationsDetail(models.Model):
    invoice = models.ForeignKey(QuotationsHeader, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.DecimalField(
        max_digits=18, decimal_places=6, default=0)
    price = models.DecimalField(
        max_digits=18, decimal_places=6, default=0)
    cost = models.DecimalField(
        max_digits=18, decimal_places=6, default=0)
    itbis = models.DecimalField(
        max_digits=18, decimal_places=6, default=0)
    discount = models.DecimalField(
        max_digits=18, decimal_places=6, default=0)
    creationDate = models.DateTimeField(auto_now_add=True, blank=True)
    objects = models.Manager()


class QuotationsSequence(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    sequence = models.IntegerField()
    creationDate = models.DateTimeField(auto_now_add=True, blank=True)
    createdUser = models.EmailField(null=True, blank=True)
    objects = models.Manager()


class InvoicesLeadHeader(models.Model):
    invoice = models.ForeignKey(
        InvoicesHeader, null=True, on_delete=models.SET_NULL)
    subtotal = models.DecimalField(
        max_digits=18, decimal_places=6, default=0)
    discount = models.DecimalField(
        max_digits=18, decimal_places=6, default=0)
    itbis = models.DecimalField(
        max_digits=18, decimal_places=6, default=0)
    creationDate = models.DateTimeField()
    createdUser = models.EmailField(null=True, blank=True)
    serverDate = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    printed = models.BooleanField(default=False)
    objects = models.Manager()


class InvoicesLeadDetail(models.Model):
    invoiceLeadHeader = models.ForeignKey(
        InvoicesLeadHeader, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.DecimalField(
        max_digits=18, decimal_places=6, default=0)
    price = models.DecimalField(
        max_digits=18, decimal_places=6, default=0)
    cost = models.DecimalField(
        max_digits=18, decimal_places=6, default=0)
    itbis = models.DecimalField(
        max_digits=18, decimal_places=6, default=0)
    discount = models.DecimalField(
        max_digits=18, decimal_places=6, default=0)
    creationDate = models.DateTimeField(auto_now_add=True, blank=True)
    objects = models.Manager()
