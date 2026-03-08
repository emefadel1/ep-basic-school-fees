# apps/fees/api/serializers.py

from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.fees.models import Distribution, FeeCollection, Session

User = get_user_model()


class UserLiteSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "full_name"]

    def get_full_name(self, obj):
        return obj.get_full_name() if hasattr(obj, "get_full_name") else obj.username


class SessionListSerializer(serializers.ModelSerializer):
    opened_by = UserLiteSerializer(read_only=True)
    approved_by = UserLiteSerializer(read_only=True)

    class Meta:
        model = Session
        fields = [
            "id",
            "date",
            "session_type",
            "status",
            "opened_by",
            "approved_by",
            "created_at",
            "updated_at",
        ]


class SessionDetailSerializer(SessionListSerializer):
    collection_summary = serializers.SerializerMethodField()

    class Meta(SessionListSerializer.Meta):
        fields = SessionListSerializer.Meta.fields + [
            "submitted_at",
            "approved_at",
            "approval_notes",
            "rejected_at",
            "rejection_reason",
            "distributed_at",
            "locked_at",
            "unlock_count",
            "collection_summary",
        ]

    def get_collection_summary(self, obj):
        from apps.fees.services.collection import CollectionService
        return CollectionService().get_session_totals(obj.id)


class SessionCreateSerializer(serializers.Serializer):
    date = serializers.DateField()
    session_type = serializers.ChoiceField(
        choices=Session.SessionType.choices,
        default=Session.SessionType.REGULAR,
    )


class SessionApproveSerializer(serializers.Serializer):
    notes = serializers.CharField(required=False, allow_blank=True)


class SessionRejectSerializer(serializers.Serializer):
    reason = serializers.CharField(required=True)


class SessionUnlockSerializer(serializers.Serializer):
    reason = serializers.CharField(required=True, min_length=20)


class SessionDistributeSerializer(serializers.Serializer):
    headteacher_id = serializers.IntegerField(required=True)
    jhs_class_teachers = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True,
    )
    all_jhs_staff = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True,
    )
    saturday_attendees = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True,
    )


class FeeCollectionSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    class_code = serializers.CharField(source="school_class.code", read_only=True)

    class Meta:
        model = FeeCollection
        fields = [
            "id",
            "session",
            "school_class",
            "class_code",
            "student",
            "student_name",
            "pool_type",
            "expected_amount",
            "amount_paid",
            "status",
            "unpaid_reason",
            "unpaid_notes",
            "receipt_number",
            "recorded_by",
            "created_at",
            "updated_at",
        ]

    def get_student_name(self, obj):
        if hasattr(obj.student, "get_full_name"):
            return obj.student.get_full_name()
        full_name = f"{getattr(obj.student, 'first_name', '')} {getattr(obj.student, 'last_name', '')}".strip()
        return full_name or str(obj.student)


class CollectionCreateSerializer(serializers.Serializer):
    session_id = serializers.IntegerField()
    student_id = serializers.IntegerField()
    pool_type = serializers.ChoiceField(choices=FeeCollection._meta.get_field("pool_type").choices)
    amount_paid = serializers.DecimalField(max_digits=10, decimal_places=2)
    unpaid_reason = serializers.ChoiceField(
        choices=FeeCollection.UnpaidReason.choices,
        required=False,
        allow_blank=True,
    )
    unpaid_notes = serializers.CharField(required=False, allow_blank=True)


class BulkCollectionItemSerializer(serializers.Serializer):
    student_id = serializers.IntegerField()
    pool_type = serializers.ChoiceField(choices=FeeCollection._meta.get_field("pool_type").choices)
    amount_paid = serializers.DecimalField(max_digits=10, decimal_places=2)
    status = serializers.ChoiceField(
        choices=FeeCollection.PaymentStatus.choices,
        required=False,
        allow_blank=True,
    )
    unpaid_reason = serializers.ChoiceField(
        choices=FeeCollection.UnpaidReason.choices,
        required=False,
        allow_blank=True,
    )
    unpaid_notes = serializers.CharField(required=False, allow_blank=True)


class BulkCollectionSerializer(serializers.Serializer):
    session_id = serializers.IntegerField()
    class_id = serializers.IntegerField()
    collections = BulkCollectionItemSerializer(many=True)


class CollectionPatchSerializer(serializers.Serializer):
    amount_paid = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    unpaid_reason = serializers.ChoiceField(
        choices=FeeCollection.UnpaidReason.choices,
        required=False,
        allow_blank=True,
    )
    unpaid_notes = serializers.CharField(required=False, allow_blank=True)


class DistributionSerializer(serializers.ModelSerializer):
    staff_name = serializers.SerializerMethodField()

    class Meta:
        model = Distribution
        fields = [
            "id",
            "session",
            "pool_type",
            "staff",
            "staff_name",
            "base_share",
            "adjusted_share",
            "attendance_status",
            "attendance_weight",
            "special_share_type",
            "special_share_amount",
            "is_paid",
            "paid_at",
            "payment_reference",
            "created_at",
        ]

    def get_staff_name(self, obj):
        return obj.staff.get_full_name() if hasattr(obj.staff, "get_full_name") else obj.staff.username


class DistributionMarkPaidSerializer(serializers.Serializer):
    payment_reference = serializers.CharField(required=False, allow_blank=True)


class DistributionBulkPaySerializer(serializers.Serializer):
    distribution_ids = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)
    payment_reference = serializers.CharField(required=False, allow_blank=True)