# apps/fees/api/views.py

from decimal import Decimal

from django.shortcuts import get_object_or_404
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.audit.models import AuditLog
from apps.school.models import SchoolClass, Student
from apps.fees.models import Distribution, FeeCollection, Session
from apps.fees.services.collection import CollectionService
from apps.fees.services.distribution import FeeDistributionEngine
from apps.fees.services.payment_service import PaymentService
from apps.fees.services.session_service import SessionService

from .permissions import (
    IsBursar,
    IsHeadteacherOrBursar,
    IsSelfOrBursar,
    IsTeacherContactHeadteacherBursarBoard,
    IsTeacherHeadteacherBursar,
)
from .serializers import (
    BulkCollectionSerializer,
    CollectionCreateSerializer,
    CollectionPatchSerializer,
    DistributionBulkPaySerializer,
    DistributionMarkPaidSerializer,
    DistributionSerializer,
    FeeCollectionSerializer,
    SessionApproveSerializer,
    SessionCreateSerializer,
    SessionDetailSerializer,
    SessionDistributeSerializer,
    SessionListSerializer,
    SessionRejectSerializer,
    SessionUnlockSerializer,
)


def request_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def fee_field_for_pool(pool_type: str) -> str:
    mapping = {
        "GEN_STUDIES": "daily_fee",
        "JHS_EXTRA": "jhs_extra_fee",
        "JHS3_EXTRA": "jhs3_extra_fee",
        "SATURDAY": "saturday_fee",
    }
    return mapping[pool_type]


class SessionViewSet(viewsets.ModelViewSet):
    queryset = Session.objects.all().select_related("opened_by", "approved_by", "locked_by")
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return SessionDetailSerializer
        if self.action == "create":
            return SessionCreateSerializer
        if self.action == "approve":
            return SessionApproveSerializer
        if self.action == "reject":
            return SessionRejectSerializer
        if self.action == "unlock":
            return SessionUnlockSerializer
        if self.action == "distribute":
            return SessionDistributeSerializer
        return SessionListSerializer

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [IsTeacherContactHeadteacherBursarBoard()]
        if self.action in ["create", "open", "submit"]:
            return [IsHeadteacherOrBursar()]
        if self.action in ["approve", "reject", "distribute", "lock", "unlock"]:
            return [IsBursar()]
        return super().get_permissions()

    def get_queryset(self):
        qs = self.queryset
        params = self.request.query_params

        if params.get("status"):
            qs = qs.filter(status=params["status"])
        if params.get("date_from"):
            qs = qs.filter(date__gte=params["date_from"])
        if params.get("date_to"):
            qs = qs.filter(date__lte=params["date_to"])

        return qs.order_by("-date")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        session = Session.objects.create(
            date=serializer.validated_data["date"],
            session_type=serializer.validated_data.get("session_type", Session.SessionType.REGULAR),
            status=Session.Status.DRAFT,
        )

        AuditLog.log_action(
            action=AuditLog.Action.CREATE,
            table_name="sessions",
            record_id=session.id,
            user=request.user,
            new_value={"status": session.status, "date": str(session.date)},
            notes="Session created from API",
            ip_address=request_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

        return Response(SessionDetailSerializer(session).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def open(self, request, pk=None):
        session = self.get_object()
        service = SessionService(session=session)
        service.open_session(
            user=request.user,
            ip_address=request_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )
        session.refresh_from_db()
        return Response(SessionDetailSerializer(session).data)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        session = self.get_object()
        service = SessionService(session=session)
        service.submit_for_approval(
            user=request.user,
            ip_address=request_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )
        session.refresh_from_db()
        return Response(SessionDetailSerializer(session).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        session = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = SessionService(session=session)
        service.approve(
            user=request.user,
            notes=serializer.validated_data.get("notes", ""),
            ip_address=request_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )
        session.refresh_from_db()
        return Response(SessionDetailSerializer(session).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        session = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = SessionService(session=session)
        service.reject(
            user=request.user,
            reason=serializer.validated_data["reason"],
            ip_address=request_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )
        session.refresh_from_db()
        return Response(SessionDetailSerializer(session).data)

    @action(detail=True, methods=["post"])
    def distribute(self, request, pk=None):
        session = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        engine = FeeDistributionEngine(session=session)
        payload = serializer.validated_data

        pool_codes = list(
            FeeCollection.objects.filter(session=session)
            .values_list("pool_type", flat=True)
            .distinct()
        )

        results = []
        for pool_code in pool_codes:
            result = engine.calculate_and_save(
                pool_code=pool_code,
                headteacher_id=payload["headteacher_id"],
                jhs_class_teachers=payload.get("jhs_class_teachers"),
                all_jhs_staff=payload.get("all_jhs_staff"),
                saturday_attendees=payload.get("saturday_attendees"),
                user=request.user,
                ip_address=request_ip(request),
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
            )
            results.append(result.to_dict())

        SessionService(session=session).mark_distributed(
            user=request.user,
            ip_address=request_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )
        session.refresh_from_db()

        return Response({
            "id": session.id,
            "status": session.status,
            "distributions": results,
        })

    @action(detail=True, methods=["post"])
    def lock(self, request, pk=None):
        session = self.get_object()
        service = SessionService(session=session)
        service.lock(
            user=request.user,
            ip_address=request_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )
        session.refresh_from_db()
        return Response(SessionDetailSerializer(session).data)

    @action(detail=True, methods=["post"])
    def unlock(self, request, pk=None):
        session = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = SessionService(session=session)
        service.unlock(
            user=request.user,
            reason=serializer.validated_data["reason"],
            ip_address=request_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )
        session.refresh_from_db()
        return Response(SessionDetailSerializer(session).data)


class CollectionViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = FeeCollection.objects.all().select_related("student", "school_class", "session")
    serializer_class = FeeCollectionSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ["list", "summary"]:
            return [IsAuthenticated()]
        if self.action in ["create", "bulk", "partial_update"]:
            return [IsTeacherHeadteacherBursar()]
        return super().get_permissions()

    def get_queryset(self):
        qs = self.queryset
        params = self.request.query_params

        if params.get("session_id"):
            qs = qs.filter(session_id=params["session_id"])
        if params.get("class_id"):
            qs = qs.filter(school_class_id=params["class_id"])
        if params.get("pool_type"):
            qs = qs.filter(pool_type=params["pool_type"])
        if params.get("status"):
            qs = qs.filter(status=params["status"])

        role = str(getattr(self.request.user, "role", "")).upper()
        assigned_class_id = getattr(self.request.user, "assigned_class_id", None)
        if role == "TEACHER" and assigned_class_id:
            qs = qs.filter(school_class_id=assigned_class_id)

        return qs.order_by("school_class_id", "student_id", "pool_type")

    def create(self, request, *args, **kwargs):
        serializer = CollectionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        session = get_object_or_404(Session, id=serializer.validated_data["session_id"])
        student = get_object_or_404(Student, id=serializer.validated_data["student_id"])
        school_class = student.school_class

        expected_amount = getattr(school_class, fee_field_for_pool(serializer.validated_data["pool_type"]))

        service = PaymentService(session=session)
        collection = service.record_collection(
            school_class=school_class,
            student=student,
            pool_type=serializer.validated_data["pool_type"],
            expected_amount=expected_amount,
            amount_paid=serializer.validated_data["amount_paid"],
            recorded_by=request.user,
            unpaid_reason=serializer.validated_data.get("unpaid_reason", ""),
            unpaid_notes=serializer.validated_data.get("unpaid_notes", ""),
            ip_address=request_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

        if collection.amount_paid > Decimal("0.00") and not collection.receipt_number:
            try:
                service.generate_receipt(
                    collection=collection,
                    user=request.user,
                    ip_address=request_ip(request),
                    user_agent=request.META.get("HTTP_USER_AGENT", ""),
                )
                collection.refresh_from_db()
            except Exception:
                pass

        return Response(FeeCollectionSerializer(collection).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"])
    def bulk(self, request):
        serializer = BulkCollectionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        session = get_object_or_404(Session, id=serializer.validated_data["session_id"])
        school_class = get_object_or_404(SchoolClass, id=serializer.validated_data["class_id"])
        service = PaymentService(session=session)

        created = 0
        updated = 0
        errors = []

        for item in serializer.validated_data["collections"]:
            try:
                student = Student.objects.get(id=item["student_id"], school_class=school_class)
                expected_amount = getattr(school_class, fee_field_for_pool(item["pool_type"]))

                existing = FeeCollection.objects.filter(
                    session=session,
                    student=student,
                    pool_type=item["pool_type"],
                ).first()

                service.record_collection(
                    school_class=school_class,
                    student=student,
                    pool_type=item["pool_type"],
                    expected_amount=expected_amount,
                    amount_paid=item["amount_paid"],
                    recorded_by=request.user,
                    unpaid_reason=item.get("unpaid_reason", ""),
                    unpaid_notes=item.get("unpaid_notes", ""),
                    ip_address=request_ip(request),
                    user_agent=request.META.get("HTTP_USER_AGENT", ""),
                )

                if existing:
                    updated += 1
                else:
                    created += 1

            except Exception as exc:
                errors.append(f"student_id={item.get('student_id')}: {exc}")

        return Response({
            "created": created,
            "updated": updated,
            "errors": errors,
        })

    def partial_update(self, request, *args, **kwargs):
        collection = self.get_object()
        serializer = CollectionPatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if collection.session.status != Session.Status.OPEN:
            return Response(
                {"detail": "Session must be OPEN to update collections."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        role = str(getattr(request.user, "role", "")).upper()
        assigned_class_id = getattr(request.user, "assigned_class_id", None)
        if role == "TEACHER":
            if assigned_class_id and collection.school_class_id != assigned_class_id:
                return Response({"detail": "Teacher can only update own class."}, status=status.HTTP_403_FORBIDDEN)
            if collection.session.date != request._request.GET.get("today", collection.session.date.isoformat()):
                pass

        if "amount_paid" in serializer.validated_data:
            collection.amount_paid = serializer.validated_data["amount_paid"]
        if "unpaid_reason" in serializer.validated_data:
            collection.unpaid_reason = serializer.validated_data["unpaid_reason"]
        if "unpaid_notes" in serializer.validated_data:
            collection.unpaid_notes = serializer.validated_data["unpaid_notes"]
        collection.recorded_by = request.user
        collection.save()

        AuditLog.log_action(
            action=AuditLog.Action.UPDATE,
            table_name="fee_collections",
            record_id=collection.id,
            user=request.user,
            new_value={"status": collection.status, "amount_paid": str(collection.amount_paid)},
            notes="Collection updated from API",
            ip_address=request_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

        return Response(FeeCollectionSerializer(collection).data)

    @action(detail=False, methods=["get"])
    def summary(self, request):
        session_id = request.query_params.get("session_id")
        class_id = request.query_params.get("class_id")

        if not session_id:
            return Response({"detail": "session_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        service = CollectionService()

        if class_id:
            data = service.get_class_summary(
                session_id=int(session_id),
                class_id=int(class_id),
                pool_type=request.query_params.get("pool_type"),
            )
            return Response({
                "by_class": [item.__dict__ for item in data],
            })

        return Response(service.get_session_totals(int(session_id)))


class DistributionViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = Distribution.objects.all().select_related("staff", "session")
    serializer_class = DistributionSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ["list"]:
            return [IsAuthenticated()]
        if self.action in ["my"]:
            return [IsAuthenticated()]
        if self.action in ["mark_paid", "bulk_pay"]:
            return [IsBursar()]
        return super().get_permissions()

    def get_queryset(self):
        qs = self.queryset
        params = self.request.query_params
        role = str(getattr(self.request.user, "role", "")).upper()

        if params.get("session_id"):
            qs = qs.filter(session_id=params["session_id"])
        if params.get("pool_type"):
            qs = qs.filter(pool_type=params["pool_type"])
        if params.get("is_paid") in ["true", "false"]:
            qs = qs.filter(is_paid=params["is_paid"] == "true")

        if params.get("staff_id") and role == "BURSAR":
            qs = qs.filter(staff_id=params["staff_id"])
        elif role != "BURSAR":
            qs = qs.filter(staff=self.request.user)

        return qs.order_by("-session__date", "pool_type")

    @action(detail=False, methods=["get"])
    def my(self, request):
        qs = Distribution.objects.filter(staff=request.user).select_related("session")

        if request.query_params.get("date_from"):
            qs = qs.filter(session__date__gte=request.query_params["date_from"])
        if request.query_params.get("date_to"):
            qs = qs.filter(session__date__lte=request.query_params["date_to"])

        total_earned = sum((d.total_share for d in qs), Decimal("0.00"))
        total_paid = sum((d.total_share for d in qs if d.is_paid), Decimal("0.00"))
        total_pending = total_earned - total_paid

        return Response({
            "total_earned": total_earned,
            "total_paid": total_paid,
            "total_pending": total_pending,
            "distributions": DistributionSerializer(qs, many=True).data,
        })

    @action(detail=True, methods=["post"])
    def mark_paid(self, request, pk=None):
        distribution = self.get_object()
        serializer = DistributionMarkPaidSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        distribution.mark_as_paid(
            user=request.user,
            reference=serializer.validated_data.get("payment_reference", ""),
        )

        AuditLog.log_action(
            action=AuditLog.Action.UPDATE,
            table_name="distributions",
            record_id=distribution.id,
            user=request.user,
            new_value={
                "is_paid": distribution.is_paid,
                "payment_reference": distribution.payment_reference,
            },
            notes="Distribution marked paid",
            ip_address=request_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

        return Response(DistributionSerializer(distribution).data)

    @action(detail=False, methods=["post"])
    def bulk_pay(self, request):
        serializer = DistributionBulkPaySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        qs = Distribution.objects.filter(id__in=serializer.validated_data["distribution_ids"])
        updated = 0

        for distribution in qs:
            distribution.mark_as_paid(
                user=request.user,
                reference=serializer.validated_data.get("payment_reference", ""),
            )
            updated += 1

        AuditLog.log_action(
            action=AuditLog.Action.UPDATE,
            table_name="distributions",
            record_id=None,
            user=request.user,
            new_value={
                "updated": updated,
                "payment_reference": serializer.validated_data.get("payment_reference", ""),
            },
            notes="Bulk distribution payment update",
            ip_address=request_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

        return Response({"updated": updated})