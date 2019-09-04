from django.db import models
from administration.models import Company, User


class ProductCategory(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    description = models.CharField(max_length=50)
    creationDate = models.DateTimeField(auto_now_add=True, blank=True)
    createdByUser = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True)
    objects = models.Manager()

    def __str__(self):
        return self.description


class Product(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    description = models.CharField(max_length=100)
    descriptionLong = models.CharField(max_length=255, null=True, blank=True)
    price = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True)
    cost = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True)
    itbis = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True)
    category = models.ForeignKey(ProductCategory, on_delete=models.CASCADE)
    measure = models.CharField(max_length=15, null=True, blank=True)
    model = models.CharField(max_length=50, null=True, blank=True)
    creationDate = models.DateTimeField(auto_now_add=True, blank=True)
    createdByUser = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True)
    objects = models.Manager()

    def __str__(self):
        return self.description


class ProductsTracking(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    typeTracking = models.CharField(max_length=3)
    quantity = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True)
    creationDate = models.DateTimeField(auto_now_add=True, blank=True)
    createdByUser = models.ForeignKey(User, on_delete=models.CASCADE)
    objects = models.Manager()


class ProductsStock(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    quantityAvailable = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True)
    quantityHold = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True)
    lastUpdated = models.DateTimeField(auto_now_add=True, blank=True)
    modifiedByUser = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True)
    objects = models.Manager()
