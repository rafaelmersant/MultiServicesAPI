from django.db import models


class Company(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(null=True)
    phoneNumber = models.CharField(max_length=50, null=True, blank=True)
    rnc = models.CharField(max_length=20, null=True, blank=True)
    address = models.CharField(max_length=255, null=True, blank=True)
    creationDate = models.DateTimeField(auto_now_add=True, blank=True)
    createdByUser = models.EmailField(null=True)
    objects = models.Manager()

    def __str__(self):
        return f'{self.id}'


class User(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    userName = models.CharField(max_length=50)
    email = models.EmailField()
    password = models.CharField(max_length=150)
    fullName = models.CharField(max_length=255)
    userHash = models.CharField(max_length=255, blank=True)
    userRole = models.CharField(max_length=20, blank=True)
    creationDate = models.DateTimeField(auto_now_add=True, blank=True)
    createdByUser = models.EmailField()
    objects = models.Manager()

    def __str__(self):
        return f'{self.id}'


class Customer(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    firstName = models.CharField(max_length=100)
    lastName = models.CharField(max_length=100)
    email = models.EmailField()
    address = models.CharField(max_length=200, null=True, blank=True)
    phoneNumber = models.CharField(max_length=50, null=True, blank=True)
    creationDate = models.DateTimeField(auto_now_add=True, blank=True)
    createdByUser = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True)
    objects = models.Manager()

    def __str__(self):
        return f'{self.id}'


class FiscalGov(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    typeDoc = models.CharField(max_length=15)
    start = models.IntegerField()
    end = models.IntegerField()
    current = models.IntegerField(null=True, blank=True)
    dueDate = models.DateField()
    active = models.BooleanField()
    creationDate = models.DateTimeField(auto_now_add=True, blank=True)
    createdByUser = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True)
    objects = models.Manager()
