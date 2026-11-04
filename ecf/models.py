from django.db import models
from django.db import transaction

from administration.models import Company
from sales.models import InvoicesHeader

ECF_DOCUMENT_TYPES = frozenset({"31", "32", "33", "34", "41", "43", "44", "45", "46", "47"})


class ECFEnvironment(models.TextChoices):
    PRECERT = "precert", "Pre-certification"
    CERT = "cert", "Certification"
    PROD = "prod", "Production"


class RFCEStatus(models.TextChoices):
    DRAFT = "draft", "Borrador"
    READY = "ready", "Firmado"
    SENDING = "sending", "Enviando"
    ACCEPTED = "accepted", "Aceptado"
    ACCEPTED_CONDITIONAL = "accepted_conditional", "Aceptado condicional"
    REJECTED = "rejected", "Rechazado"
    UNCERTAIN = "uncertain", "Incierto"


class ElectronicInvoiceSequence(models.Model):
    """Company-specific e-CF authorization data, when configured."""

    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    environment = models.CharField(
        max_length=10,
        choices=ECFEnvironment.choices,
        default=ECFEnvironment.CERT,
    )
    document_type = models.CharField(max_length=3)
    authorized_start = models.PositiveIntegerField(null=True, blank=True)
    authorized_end = models.PositiveIntegerField(null=True, blank=True)
    current = models.PositiveIntegerField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    active = models.BooleanField(default=False)
    creation_date = models.DateTimeField(auto_now_add=True)
    created_user = models.EmailField(null=True, blank=True)

    objects = models.Manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("company", "environment", "document_type"),
                name="ecf_unique_company_env_type_sequence",
            ),
        ]

    def allocate_encf(self) -> str:
        """Atomically reserve the next number in a configured DGII range.

        ``current`` is the last reserved sequence number. No range is supplied
        by default; the company must first enter an authorization received
        from DGII.
        """
        if not self.document_type.isdigit() or len(self.document_type) != 2:
            raise ValueError("El tipo e-CF debe tener dos dígitos.")

        with transaction.atomic():
            sequence = type(self).objects.select_for_update().get(pk=self.pk)
            if not sequence.active:
                raise ValueError("La secuencia e-CF no está activa.")
            if sequence.authorized_start is None or sequence.authorized_end is None:
                raise ValueError("La secuencia no tiene un rango autorizado configurado.")
            if sequence.authorized_start > sequence.authorized_end:
                raise ValueError("El rango autorizado de la secuencia no es válido.")

            next_value = (
                sequence.authorized_start
                if sequence.current is None
                else max(sequence.authorized_start, sequence.current + 1)
            )
            if next_value > sequence.authorized_end:
                raise ValueError("La secuencia e-CF autorizada está agotada.")

            previous_value = sequence.current
            updates = type(self).objects.filter(pk=sequence.pk, active=True)
            updates = (
                updates.filter(current__isnull=True)
                if previous_value is None
                else updates.filter(current=previous_value)
            )
            if updates.update(current=next_value) != 1:
                raise RuntimeError(
                    "La secuencia cambió mientras se reservaba; vuelve a intentarlo."
                )

        self.current = next_value
        return f"E{sequence.document_type}{next_value:010d}"

    def __str__(self) -> str:
        return f'{self.company_id}: {self.document_type}'


class ElectronicInvoice(models.Model):
    """Electronic invoice record associated with a traditional invoice."""

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        READY = 'ready', 'Ready'
        SUBMITTED = 'submitted', 'Submitted'
        PROCESSING = 'processing', 'Processing'
        ACCEPTED = 'accepted', 'Accepted'
        ACCEPTED_CONDITIONAL = 'accepted_conditional', 'Accepted conditional'
        REJECTED = 'rejected', 'Rejected'
        UNCERTAIN = 'uncertain', 'Uncertain'

    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    environment = models.CharField(
        max_length=10,
        choices=ECFEnvironment.choices,
        default=ECFEnvironment.CERT,
    )
    invoice = models.OneToOneField(
        InvoicesHeader,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='electronic_invoice',
    )
    sequence = models.ForeignKey(
        ElectronicInvoiceSequence,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='electronic_invoices',
    )
    document_type = models.CharField(max_length=3)
    encf = models.CharField(max_length=13, null=True, blank=True, unique=True)
    status = models.CharField(
        max_length=24,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    creation_date = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    payload = models.JSONField(default=dict, blank=True)
    raw_xml = models.TextField(blank=True)
    signed_xml = models.TextField(blank=True)
    representation_pdf = models.FileField(upload_to="ecf/representations/", blank=True)
    rfce_xml = models.TextField(blank=True)
    signed_rfce_xml = models.TextField(blank=True)
    rfce_status = models.CharField(
        max_length=24,
        choices=RFCEStatus.choices,
        default=RFCEStatus.DRAFT,
    )
    rfce_code = models.PositiveSmallIntegerField(null=True, blank=True)
    rfce_status_text = models.CharField(max_length=32, blank=True)
    rfce_messages = models.JSONField(default=list, blank=True)
    rfce_sequence_used = models.BooleanField(null=True, blank=True)
    rfce_sent_at = models.DateTimeField(null=True, blank=True)
    rfce_resolved_at = models.DateTimeField(null=True, blank=True)
    xml_hash = models.CharField(max_length=64, blank=True)
    track_id = models.CharField(max_length=64, null=True, blank=True, unique=True)
    dgii_code = models.PositiveSmallIntegerField(null=True, blank=True)
    dgii_status = models.CharField(max_length=32, blank=True)
    dgii_messages = models.JSONField(default=list, blank=True)
    portal_result = models.CharField(max_length=16, blank=True)
    portal_result_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    objects = models.Manager()

    def __str__(self) -> str:
        return self.encf or f'{self.company_id}: {self.document_type}'


class ReceivedElectronicDocument(models.Model):
    """e-CF or commercial response received through the public DGII routes."""

    class Kind(models.TextChoices):
        ECF = "ecf", "e-CF"
        COMMERCIAL_APPROVAL = "approval", "Aprobación comercial"

    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    kind = models.CharField(max_length=12, choices=Kind.choices)
    issuer_rnc = models.CharField(max_length=11)
    buyer_rnc = models.CharField(max_length=11)
    encf = models.CharField(max_length=13)
    xml_sha256 = models.CharField(max_length=64)
    signed_xml = models.TextField()
    receipt_xml = models.TextField(blank=True)
    received_at = models.DateTimeField(auto_now_add=True)

    objects = models.Manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("company", "kind", "issuer_rnc", "encf"),
                name="ecf_unique_received_document",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.kind}: {self.encf}"


class ECFAuthenticationChallenge(models.Model):
    """One-time seeds issued by the optional public e-CF authentication API."""

    seed_sha256 = models.CharField(max_length=64, unique=True)
    issued_at = models.DateTimeField()
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True, blank=True)

    objects = models.Manager()

    class Meta:
        indexes = [models.Index(fields=("expires_at", "consumed_at"))]

    def __str__(self) -> str:
        return f"e-CF auth seed issued {self.issued_at:%Y-%m-%d %H:%M:%S}"
