from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.fees.models import FeeCollection, Session
from apps.school.models import Category, SchoolClass, Student

User = get_user_model()


@override_settings(ROOT_URLCONF="config.api_urls")
class FeeApiErrorHandlingTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.bursar = User.objects.create_user(username="bursar", password="pass12345", role=User.Role.BURSAR)
        self.headteacher = User.objects.create_user(username="head", password="pass12345", role=User.Role.HEADTEACHER)
        self.client.force_authenticate(self.bursar)
        self.school_class = SchoolClass.objects.create(
            code="B8",
            name="JHS 2",
            category=Category.JHS,
            daily_fee=Decimal("10.00"),
            jhs_extra_fee=Decimal("5.00"),
        )
        self.student = Student.objects.create(
            student_id="STU001",
            first_name="Ama",
            last_name="Mensah",
            gender=Student.Gender.FEMALE,
            school_class=self.school_class,
            admission_date=date.today(),
            parent_name="Parent",
            parent_phone="0200000000",
        )
    def make_collection(self, session, pool_type, expected_amount):
        return FeeCollection.objects.create(
            session=session,
            school_class=self.school_class,
            student=self.student,
            pool_type=pool_type,
            expected_amount=expected_amount,
            amount_paid=expected_amount,
            recorded_by=self.bursar,
        )

    def test_distribution_missing_inputs_returns_insufficient_data(self):
        session = Session.objects.create(date=date.today(), session_type=Session.SessionType.REGULAR, status=Session.Status.APPROVED)
        self.make_collection(session, "JHS_EXTRA", Decimal("5.00"))
        response = self.client.post(f"/sessions/{session.id}/distribute/", {"headteacher_id": self.headteacher.id}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"]["code"], "insufficient_data")

    def test_distribution_invalid_state_returns_normalized_error(self):
        session = Session.objects.create(date=date.today(), session_type=Session.SessionType.REGULAR, status=Session.Status.OPEN)
        self.make_collection(session, "GEN_STUDIES", Decimal("10.00"))
        response = self.client.post(f"/sessions/{session.id}/distribute/", {"headteacher_id": self.headteacher.id}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data["success"])
        self.assertEqual(response.data["error"]["code"], "distribution_invalid_state")
        self.assertEqual(response.data["context"]["method"], "POST")
