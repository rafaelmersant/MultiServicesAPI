""" Sales models. """

# Django
from django.db import models

# Models
from administration.models import Company, Customer, User
from products.models import Product


class InvoicesHeader(models.Model):
    """ Invoices Header model. """

    sequence = models.IntegerField(unique=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    paymentMethod = models.CharField(max_length=20, null=True, blank=True) # Transferencia / Credito / Puntos Superavit
    invoiceType = models.CharField(max_length=20, null=True, blank=True) # Credito / Contado
    invoiceStatus = models.CharField(max_length=10, blank=True, default="") # Anulada or Empty
    ncf = models.CharField(
        max_length=13,
        null=True,
        blank=True
    )
    paid = models.BooleanField(default=True)
    reference = models.CharField(max_length=50, blank=True)
    subtotal = models.DecimalField(
        max_digits=18,
        decimal_places=6,
        default=0
    )
    discount = models.DecimalField(
        max_digits=18,
        decimal_places=6,
        default=0
    )
    itbis = models.DecimalField(
        max_digits=18,
        decimal_places=6,
        default=0
    )
    cost = models.DecimalField(
        max_digits=18,
        decimal_places=6,
        default=0
    )
    creationDate = models.DateTimeField()
    createdUser = models.EmailField(null=True, blank=True)
    serverDate = models.DateTimeField(
        auto_now_add=True,
        blank=True,
        null=True
    )
    printed = models.BooleanField(default=False)
    objects = models.Manager()


class InvoicesDetail(models.Model):
    """ Invoices detail model. """

    invoice = models.ForeignKey(InvoicesHeader, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.DecimalField(
        max_digits=18,
        decimal_places=6,
        default=0
    )
    price = models.DecimalField(
        max_digits=18,
        decimal_places=6,
        default=0
    )
    cost = models.DecimalField(
        max_digits=18,
        decimal_places=6,
        default=0
    )
    itbis = models.DecimalField(
        max_digits=18,
        decimal_places=6,
        default=0
    )
    discount = models.DecimalField(
        max_digits=18,
        decimal_places=6,
        default=0
    )
    creationDate = models.DateTimeField(auto_now_add=True, blank=True)
    objects = models.Manager()


class InvoicesSequence(models.Model):
    """ Invoices sequence model. """

    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    sequence = models.IntegerField()
    creationDate = models.DateTimeField(auto_now_add=True, blank=True)
    createdUser = models.EmailField(null=True, blank=True)
    objects = models.Manager()


class QuotationsHeader(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    reference = models.CharField(
        max_length=50,
        blank=True
    )
    subtotal = models.DecimalField(
        max_digits=18,
        decimal_places=6,
        default=0
    )
    discount = models.DecimalField(
        max_digits=18,
        decimal_places=6,
        default=0
    )
    itbis = models.DecimalField(
        max_digits=18,
        decimal_places=6,
        default=0
    )
    creationDate = models.DateTimeField()
    createdUser = models.EmailField(null=True, blank=True)
    serverDate = models.DateTimeField(
        auto_now_add=True,
        blank=True,
        null=True
    )
    printed = models.BooleanField(default=False)
    objects = models.Manager()


class QuotationsDetail(models.Model):
    header = models.ForeignKey(QuotationsHeader, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.DecimalField(
        max_digits=18,
        decimal_places=6,
        default=0
    )
    price = models.DecimalField(
        max_digits=18,
        decimal_places=6,
        default=0
    )
    cost = models.DecimalField(
        max_digits=18,
        decimal_places=6,
        default=0
    )
    itbis = models.DecimalField(
        max_digits=18,
        decimal_places=6,
        default=0
    )
    discount = models.DecimalField(
        max_digits=18,
        decimal_places=6,
        default=0
    )
    creationDate = models.DateTimeField(auto_now_add=True, blank=True)
    objects = models.Manager()


class InvoicesLeadHeader(models.Model):
    """ Invoices Lead header (Conduce) model.

    All invoiceLead (Conduce) will be saved here only header info.
    Their relationship with the invoiceNo.
    """

    invoice = models.ForeignKey(
        InvoicesHeader,
        on_delete=models.SET_NULL,
        null=True
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.SET_NULL,
        null=True
    )
    creationDate = models.DateTimeField(auto_now_add=True, blank=True)
    objects = models.Manager()


class InvoicesLeadDetail(models.Model):
    """ Invoices Lead detail (Conduce) model.

    All invoiceLead (Conduce) will be saved here with all details.
    Their relationship with the invoiceNo.
    """

    header = models.ForeignKey(
        InvoicesLeadHeader,
        on_delete=models.CASCADE,
        null=True
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE
    )
    quantity = models.DecimalField(
        max_digits=18,
        decimal_places=6,
        default=0
    )
    creationDate = models.DateTimeField(auto_now_add=True, blank=True)
    objects = models.Manager()


class Points(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    invoice = models.ForeignKey(InvoicesHeader, on_delete=models.CASCADE)
    invoice_amount = models.DecimalField(
        max_digits=18, decimal_places=6, null=True, blank=True)
    total_points = models.DecimalField(
        max_digits=18, decimal_places=6, null=True, blank=True)
    type = models.CharField(max_length=1) #E = Entry / R = Redeemed
    reference = models.CharField(max_length=200)
    creationDate = models.DateTimeField(
        auto_now_add=True,
        blank=True,
        null=True
    )
    createdUser = models.EmailField(null=True, blank=True)
    objects = models.Manager()

    def __str__(self) -> str:
        return f'Total Points: {self.total_points}'