from rest_framework import serializers

from .models import ECF_DOCUMENT_TYPES, ElectronicInvoice, ElectronicInvoiceSequence


class ElectronicInvoiceSerializer(serializers.ModelSerializer):
    invoice_sequence = serializers.IntegerField(source="invoice.sequence", read_only=True)
    invoice_total = serializers.SerializerMethodField()
    certification_attempt = serializers.SerializerMethodField()
    representation_identity_current = serializers.SerializerMethodField()

    class Meta:
        model = ElectronicInvoice
        fields = (
            "id",
            "company_id",
            "environment",
            "certification_attempt",
            "invoice",
            "invoice_sequence",
            "invoice_total",
            "sequence",
            "document_type",
            "encf",
            "status",
            "creation_date",
            "updated_at",
            "xml_hash",
            "has_payload",
            "has_unsigned_xml",
            "has_signed_xml",
            "has_rfce_xml",
            "has_representation_pdf",
            "representation_identity_current",
            "rfce_status",
            "rfce_code",
            "rfce_status_text",
            "rfce_messages",
            "rfce_sequence_used",
            "rfce_sent_at",
            "rfce_resolved_at",
            "track_id",
            "dgii_code",
            "dgii_status",
            "dgii_messages",
            "portal_result",
            "portal_result_at",
            "last_error",
            "sent_at",
            "resolved_at",
        )
        read_only_fields = (
            "company_id",
            "environment",
            "sequence",
            "invoice",
            "document_type",
            "encf",
            "status",
            "creation_date",
            "updated_at",
            "track_id",
            "dgii_code",
            "dgii_status",
            "dgii_messages",
            "portal_result",
            "portal_result_at",
            "last_error",
            "sent_at",
            "resolved_at",
            "xml_hash",
            "has_payload",
            "has_unsigned_xml",
            "has_signed_xml",
            "has_rfce_xml",
            "has_representation_pdf",
            "representation_identity_current",
            "rfce_status",
            "rfce_code",
            "rfce_status_text",
            "rfce_messages",
            "rfce_sequence_used",
            "rfce_sent_at",
            "rfce_resolved_at",
        )

    has_payload = serializers.SerializerMethodField()
    has_unsigned_xml = serializers.SerializerMethodField()
    has_signed_xml = serializers.SerializerMethodField()
    has_rfce_xml = serializers.SerializerMethodField()
    has_representation_pdf = serializers.SerializerMethodField()

    def get_has_payload(self, instance):
        return bool(instance.payload)

    def get_has_unsigned_xml(self, instance):
        return bool(instance.raw_xml)

    def get_has_signed_xml(self, instance):
        return bool(instance.signed_xml)

    def get_has_rfce_xml(self, instance):
        return bool(instance.signed_rfce_xml or instance.rfce_xml)

    def get_has_representation_pdf(self, instance):
        if not instance.representation_pdf:
            return False
        from .workflow import representation_pdf_identity_is_current

        return representation_pdf_identity_is_current(instance)

    def get_representation_identity_current(self, instance):
        from .workflow import representation_pdf_identity_is_current

        return representation_pdf_identity_is_current(instance)

    def get_invoice_total(self, instance):
        if instance.invoice_id is not None:
            return str(instance.invoice.subtotal - instance.invoice.discount)
        if instance.signed_xml or instance.raw_xml:
            try:
                from lxml import etree

                root = etree.fromstring((instance.signed_xml or instance.raw_xml).encode("utf-8"))
                values = root.xpath(".//*[local-name()='MontoTotal']")
                return (values[0].text or "").strip() if values else None
            except (etree.XMLSyntaxError, UnicodeEncodeError):
                return None
        return None

    def get_certification_attempt(self, instance):
        return str((instance.payload or {}).get("certification_attempt") or "")


class ElectronicInvoiceSequenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ElectronicInvoiceSequence
        fields = (
            "id",
            "company_id",
            "environment",
            "document_type",
            "authorized_start",
            "authorized_end",
            "authorization_reference",
            "current",
            "due_date",
            "active",
            "creation_date",
            "created_user",
        )
        read_only_fields = ("company_id", "current", "creation_date", "created_user")

    def validate(self, attrs):
        document_type = attrs.get("document_type", getattr(self.instance, "document_type", ""))
        environment = attrs.get("environment", getattr(self.instance, "environment", "cert"))
        start = attrs.get("authorized_start", getattr(self.instance, "authorized_start", None))
        end = attrs.get("authorized_end", getattr(self.instance, "authorized_end", None))
        current = getattr(self.instance, "current", None)

        if not document_type.isdigit() or len(document_type) != 2:
            raise serializers.ValidationError("El tipo de e-CF debe tener dos dígitos.")
        if document_type not in ECF_DOCUMENT_TYPES:
            raise serializers.ValidationError("El tipo de e-CF no forma parte del set de certificación habilitado.")
        if environment not in {"precert", "cert", "prod"}:
            raise serializers.ValidationError("El ambiente debe ser precert, cert o prod.")
        if self.instance is not None and (
            document_type != self.instance.document_type
            or environment != self.instance.environment
        ):
            raise serializers.ValidationError("No se puede cambiar el tipo ni el ambiente de una secuencia existente.")
        if (start is None) != (end is None):
            raise serializers.ValidationError("Configura ambos límites del rango o deja ambos vacíos.")
        if attrs.get("active", getattr(self.instance, "active", False)) and (start is None or end is None):
            raise serializers.ValidationError("Activa la secuencia solo después de configurar el rango DGII.")
        if start is not None and end is not None and start > end:
            raise serializers.ValidationError("El inicio del rango debe ser menor o igual al final.")
        maximum = 9_999_999_999 if environment == "prod" else 10_000_000
        if start is not None and (start < 1 or end > maximum):
            raise serializers.ValidationError(f"El rango debe estar entre 1 y {maximum:,}.")
        if environment == "prod" and start is not None:
            from types import SimpleNamespace
            from .issuance import validate_sequence
            sequence = SimpleNamespace(
                environment=environment, document_type=document_type,
                authorized_start=start, authorized_end=end, active=True,
                authorization_reference=attrs.get("authorization_reference", getattr(self.instance, "authorization_reference", "")),
                due_date=attrs.get("due_date", getattr(self.instance, "due_date", None)),
            )
            try:
                validate_sequence(sequence)
            except ValueError as exc:
                raise serializers.ValidationError(str(exc)) from exc
        if current is not None and (
            start != getattr(self.instance, "authorized_start")
            or end != getattr(self.instance, "authorized_end")
        ):
            raise serializers.ValidationError(
                "No se puede cambiar un rango después de reservar e-NCF."
            )
        request = self.context.get("request")
        if start is not None and request is not None:
            overlaps = ElectronicInvoiceSequence.objects.filter(
                company_id=request.user.company_id, environment=environment,
                document_type=document_type, authorized_start__lte=end, authorized_end__gte=start,
            )
            if self.instance:
                overlaps = overlaps.exclude(pk=self.instance.pk)
            if overlaps.exists():
                raise serializers.ValidationError("El rango se solapa con otro rango ya registrado para este ambiente y tipo.")
        return attrs
