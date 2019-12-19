from django.db import models


class Company(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(null=True, blank=True)
    phoneNumber = models.CharField(max_length=50, null=True, blank=True)
    rnc = models.CharField(max_length=20, null=True, blank=True)
    address = models.CharField(max_length=255, null=True, blank=True)
    creationDate = models.DateTimeField(auto_now_add=True, blank=True)
    createdUser = models.EmailField(null=True, blank=True)
    objects = models.Manager()

    def __str__(self):
        return f'{self.id}'


class User(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    email = models.EmailField()
    password = models.CharField(max_length=150)
    name = models.CharField(max_length=255)
    userHash = models.CharField(max_length=255, blank=True)
    userRole = models.CharField(max_length=20, blank=True)
    creationDate = models.DateTimeField(auto_now_add=True, blank=True)
    createdUser = models.EmailField()
    objects = models.Manager()

    def __str__(self):
        return f'{self.id}'


class Customer(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    firstName = models.CharField(max_length=100)
    lastName = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    address = models.CharField(max_length=200, null=True, blank=True)
    phoneNumber = models.CharField(max_length=50, null=True, blank=True)
    identification = models.CharField(max_length=20, blank=True)
    identificationType = models.CharField(max_length=1, blank=True)
    creationDate = models.DateTimeField(
        auto_now_add=True, blank=True, null=True)
    createdUser = models.EmailField(null=True, blank=True)
    objects = models.Manager()

    def __str__(self):
        return f'{self.id}'


class Provider(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    firstName = models.CharField(max_length=100)
    lastName = models.CharField(max_length=100, null=True, blank=True)
    email = models.EmailField(blank=True)
    address = models.CharField(max_length=200, null=True, blank=True)
    phoneNumber = models.CharField(max_length=50, null=True, blank=True)
    rnc = models.CharField(max_length=13, blank=True)
    creationDate = models.DateTimeField(
        auto_now_add=True, blank=True, null=True)
    createdUser = models.EmailField(null=True, blank=True)
    objects = models.Manager()

    def name(self):
        return self.firstName + ' ' + self.lastName

    def __str__(self):
        return f'{self.id}'


class FiscalGov(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    typeDoc = models.CharField(max_length=4)  # BC01
    start = models.IntegerField()
    end = models.IntegerField()
    current = models.IntegerField(null=True, blank=True)
    dueDate = models.DateTimeField(blank=True)
    active = models.BooleanField()
    usedInInvoice = models.IntegerField(default=0)
    creationDate = models.DateTimeField(auto_now_add=True, blank=True)
    createdUser = models.EmailField(null=True, blank=True)
    objects = models.Manager()
