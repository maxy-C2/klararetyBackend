# healthcare/tests/test_services/test_audit_service.py
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from healthcare.models import MedicalRecord, MedicalHistoryAudit
from healthcare.services.audit_service import AuditService

User = get_user_model()

class AuditServiceTest(TestCase):
    """Test suite for the AuditService"""
    
    def setUp(self):
        """Set up test data"""
        # Create test users
        self.patient = User.objects.create_user(
            username='testpatient',
            email='patient@example.com',
            password='testpass123',
            role='patient',
            first_name='Test',
            last_name='Patient'
        )
        
        self.provider = User.objects.create_user(
            username='testprovider',
            email='provider@example.com',
            password='testpass123',
            role='provider',
            first_name='Test',
            last_name='Provider'
        )
        
        # Create medical record
        self.medical_record = MedicalRecord.objects.create(
            patient=self.patient,
            medical_record_number='AB12345678',
            date_of_birth=timezone.now().date() - timezone.timedelta(days=365*30),
            gender='Male',
            primary_physician=self.provider
        )
        
        # Create a few audit logs
        self.view_log = MedicalHistoryAudit.objects.create(
            medical_record=self.medical_record,
            user=self.provider,
            action="Viewed",
            model_name="MedicalRecord",
            record_id=self.medical_record.id,
            ip_address="127.0.0.1"
        )
        
        self.update_log = MedicalHistoryAudit.objects.create(
            medical_record=self.medical_record,
            user=self.provider,
            action="Updated",
            model_name="MedicalRecord",
            record_id=self.medical_record.id,
            details="Updated weight and height",
            ip_address="127.0.0.1"
        )
    
    def test_log_action(self):
        """Test creating an audit log entry"""
        # Log a new action
        audit_log = AuditService.log_action(
            medical_record=self.medical_record,
            user=self.provider,
            action="Created",
            model_name="Medication",
            record_id=123,
            ip_address="192.168.1.1",
            details="Added new medication"
        )
        
        # Verify the log was created
        self.assertIsNotNone(audit_log)
        self.assertEqual(audit_log.medical_record, self.medical_record)
        self.assertEqual(audit_log.user, self.provider)
        self.assertEqual(audit_log.action, "Created")
        self.assertEqual(audit_log.model_name, "Medication")
        self.assertEqual(audit_log.record_id, 123)
        self.assertEqual(audit_log.ip_address, "192.168.1.1")
        self.assertEqual(audit_log.details, "Added new medication")
        
        # Verify it was saved to the database
        self.assertEqual(MedicalHistoryAudit.objects.count(), 3)
    
    def test_get_audit_logs_for_record(self):
        """Test retrieving audit logs for a medical record"""
        logs = AuditService.get_audit_logs_for_record(self.medical_record.id)
        
        # Should get our two logs in reverse chronological order
        self.assertEqual(logs.count(), 2)
        self.assertEqual(logs[0], self.update_log)  # Most recent first
        self.assertEqual(logs[1], self.view_log)
    
    def test_get_user_access_logs(self):
        """Test retrieving audit logs for a specific user"""
        # Create a second provider with logs
        provider2 = User.objects.create_user(
            username='provider2',
            email='provider2@example.com',
            password='testpass123',
            role='provider'
        )
        
        # Create a log for the second provider
        MedicalHistoryAudit.objects.create(
            medical_record=self.medical_record,
            user=provider2,
            action="Viewed",
            model_name="MedicalRecord",
            record_id=self.medical_record.id
        )
        
        # Get logs for the original provider
        logs = AuditService.get_user_access_logs(self.provider.id)
        
        # Should only get logs for the original provider
        self.assertEqual(logs.count(), 2)
        for log in logs:
            self.assertEqual(log.user, self.provider)
    
    def test_get_record_access_history(self):
        """Test getting a summary of record access history"""
        # Create additional test data with various timestamps
        one_week_ago = timezone.now() - timezone.timedelta(days=7)
        two_weeks_ago = timezone.now() - timezone.timedelta(days=14)
        
        # Add some older logs
        MedicalHistoryAudit.objects.create(
            medical_record=self.medical_record,
            user=self.provider,
            action="Created",
            model_name="Allergy",
            record_id=1,
            timestamp=two_weeks_ago
        )
        
        MedicalHistoryAudit.objects.create(
            medical_record=self.medical_record,
            user=self.patient,
            action="Viewed",
            model_name="MedicalRecord",
            record_id=self.medical_record.id,
            timestamp=one_week_ago
        )
        
        # Get the access summary for the last 30 days
        summary = AuditService.get_record_access_history(self.medical_record.id, days=30)
        
        # Verify the summary structure
        self.assertIn('total_access_count', summary)
        self.assertIn('access_by_user', summary)
        self.assertIn('access_by_action', summary)
        self.assertIn('period_days', summary)
        
        # Should have 4 total accesses
        self.assertEqual(summary['total_access_count'], 4)
        self.assertEqual(summary['period_days'], 30)
        
        # Check access by user
        self.assertEqual(len(summary['access_by_user']), 2)  # 2 different users
        
        # Provider should have 3 accesses, patient 1
        provider_access = next(item for item in summary['access_by_user'] if item['user__username'] == 'testprovider')
        patient_access = next(item for item in summary['access_by_user'] if item['user__username'] == 'testpatient')
        self.assertEqual(provider_access['access_count'], 3)
        self.assertEqual(patient_access['access_count'], 1)
        
        # Check access by action
        self.assertEqual(len(summary['access_by_action']), 3)  # 3 different actions
        
        # Verify distribution of actions
        view_actions = next(item for item in summary['access_by_action'] if item['action'] == 'Viewed')
        update_actions = next(item for item in summary['access_by_action'] if item['action'] == 'Updated')
        create_actions = next(item for item in summary['access_by_action'] if item['action'] == 'Created')
        
        self.assertEqual(view_actions['count'], 2)
        self.assertEqual(update_actions['count'], 1)
        self.assertEqual(create_actions['count'], 1)
