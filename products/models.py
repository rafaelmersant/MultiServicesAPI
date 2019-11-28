from django.db import models
from administration.models import Company, User, Provider


class ProductCategory(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    description = models.CharField(max_length=50)
    creationDate = models.DateTimeField(auto_now_add=True, blank=True)
    createdUser = models.EmailField(null=True, blank=True)
    objects = models.Manager()

    def __str__(self):
        return self.description


class Product(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    description = models.CharField(max_length=100)
    descriptionLong = models.CharField(max_length=255, null=True, blank=True)
    price = models.DecimalField(
        max_digits=18, decimal_places=2, null=True, blank=True)
    cost = models.DecimalField(
        max_digits=18, decimal_places=2, null=True, blank=True)
    itbis = models.DecimalField(
        max_digits=18, decimal_places=2, null=True, blank=True)
    category = models.ForeignKey(ProductCategory, on_delete=models.CASCADE)
    measure = models.CharField(max_length=15, null=True, blank=True)
    model = models.CharField(max_length=50, null=True, blank=True)
    barcode = models.CharField(max_length=20, null=True, blank=True)
    creationDate = models.DateTimeField(auto_now_add=True, blank=True)
    createdUser = models.EmailField(null=True, blank=True)
    objects = models.Manager()

    def __str__(self):
        return self.description


class ProductsTrackingHeader(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True)
    provider = models.ForeignKey(Provider, on_delete=models.CASCADE)
    docDate = models.DateTimeField(blank=True)
    ncf = models.CharField(max_length=13, null=True, blank=True)
    totalAmount = models.DecimalField(
        max_digits=18, decimal_places=2, null=True)
    itbis = models.DecimalField(
        max_digits=18, decimal_places=2, null=True, blank=True)
    creationDate = models.DateTimeField(blank=True)
    serverDate = models.DateTimeField(auto_now_add=True, blank=True)
    createdUser = models.EmailField(null=True, blank=True)
    objects = models.Manager()


class ProductsTracking(models.Model):
    header = models.ForeignKey(
        ProductsTrackingHeader, on_delete=models.SET_NULL,
        null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    typeTracking = models.CharField(max_length=3)
    # INVE=INVENTORY, INVO=INVOICE
    concept = models.CharField(max_length=4, default='INVE')
    quantity = models.DecimalField(
        max_digits=18, decimal_places=2, null=True, blank=True)
    price = models.DecimalField(
        max_digits=18, decimal_places=2, null=True, blank=True)
    cost = models.DecimalField(
        max_digits=18, decimal_places=2, null=True, blank=True)
    itbis = models.DecimalField(
        max_digits=18, decimal_places=2, null=True, blank=True)
    creationDate = models.DateTimeField(auto_now_add=True, blank=True)
    createdUser = models.EmailField(null=True, blank=True)
    objects = models.Manager()


class ProductsStock(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    quantityAvailable = models.DecimalField(
        max_digits=18, decimal_places=2, null=True, blank=True)
    quantityHold = models.DecimalField(
        max_digits=18, decimal_places=2, null=True, blank=True)
    lastUpdated = models.DateTimeField(auto_now_add=True, blank=True)
    modifiedUser = models.EmailField(null=True, blank=True)
    objects = models.Manager()
