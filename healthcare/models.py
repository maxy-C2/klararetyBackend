# healthcare/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone

class MedicalRecord(models.Model):
    """Master medical record for a patient"""
    patient = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='medical_record',
        limit_choices_to={'role': 'patient'}
    )
    medical_record_number = models.CharField(max_length=50, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Primary physician
    primary_physician = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='primary_patients',
        limit_choices_to={'role': 'provider'}
    )
    
    # Key patient information
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=20)
    blood_type = models.CharField(max_length=10, blank=True, null=True)
    height = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)  # in cm
    weight = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)  # in kg
    
    def get_active_medications(self):
        """Get all active medications for this patient"""
        return self.medications.filter(active=True).order_by('-start_date')

    def get_active_conditions(self):
        """Get all active conditions for this patient"""
        return self.conditions.filter(active=True).order_by('-diagnosis_date')

    def get_allergies(self):
        """Get all allergies for this patient"""
        return self.allergies.all().order_by('allergen')

    def get_latest_vitals(self):
        """Get the most recent vital signs"""
        return self.vital_signs.order_by('-date_recorded').first()

    def get_recent_lab_tests(self, limit=5):
        """Get the most recent lab tests with results"""
        return self.lab_tests.filter(results_available=True).order_by('-test_date')[:limit]

    def get_immunization_history(self):
        """Get immunization history ordered by date"""
        return self.immunizations.all().order_by('-administration_date')

    def get_surgical_history(self):
        """Get surgical history ordered by date"""
        return self.surgical_history.all().order_by('-date')

    def get_recent_notes(self, limit=5):
        """Get recent medical notes"""
        return self.medical_notes.all().order_by('-created_at')[:limit]

    def get_family_health_summary(self):
        """Get a summary of family health history by relationship"""
        from django.db.models import Count
        return self.family_history.values('relationship').annotate(
            condition_count=Count('id')
        ).order_by('relationship')

    def __str__(self):
        return f"Medical Record: {self.patient.get_full_name()} ({self.medical_record_number})"
    
    def calculate_age(self):
        today = timezone.now().date()
        return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))


class Allergy(models.Model):
    """Patient allergies"""
    medical_record = models.ForeignKey(MedicalRecord, on_delete=models.CASCADE, related_name='allergies')
    allergen = models.CharField(max_length=100)
    reaction = models.TextField()
    severity = models.CharField(max_length=20)
    diagnosed_date = models.DateField(blank=True, null=True)
    
    class Meta:
        verbose_name_plural = "Allergies"
    
    def __str__(self):
        return f"{self.allergen} - {self.medical_record.patient.get_full_name()}"


class Medication(models.Model):
    """Current and past medications"""
    medical_record = models.ForeignKey(MedicalRecord, on_delete=models.CASCADE, related_name='medications')
    name = models.CharField(max_length=100)
    dosage = models.CharField(max_length=50)
    frequency = models.CharField(max_length=50)
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    active = models.BooleanField(default=True)
    prescribed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='prescribed_medications',
        limit_choices_to={'role': 'provider'}
    )
    reason = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.name} - {self.medical_record.patient.get_full_name()}"


class Condition(models.Model):
    """Medical conditions and diagnoses"""
    medical_record = models.ForeignKey(MedicalRecord, on_delete=models.CASCADE, related_name='conditions')
    name = models.CharField(max_length=100)
    icd10_code = models.CharField(max_length=10, blank=True, null=True)  # International Classification of Diseases code
    diagnosis_date = models.DateField()
    resolved_date = models.DateField(blank=True, null=True)
    active = models.BooleanField(default=True)
    diagnosed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='diagnoses',
        limit_choices_to={'role': 'provider'}
    )
    notes = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.name} - {self.medical_record.patient.get_full_name()}"


class Immunization(models.Model):
    """Vaccination records"""
    medical_record = models.ForeignKey(MedicalRecord, on_delete=models.CASCADE, related_name='immunizations')
    vaccine = models.CharField(max_length=100)
    administration_date = models.DateField()
    administered_by = models.CharField(max_length=100, blank=True, null=True)
    lot_number = models.CharField(max_length=50, blank=True, null=True)
    expiration_date = models.DateField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.vaccine} - {self.medical_record.patient.get_full_name()}"


class LabTest(models.Model):
    """Laboratory test results"""
    medical_record = models.ForeignKey(MedicalRecord, on_delete=models.CASCADE, related_name='lab_tests')
    name = models.CharField(max_length=100)
    test_date = models.DateField()
    ordered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ordered_lab_tests',
        limit_choices_to={'role': 'provider'}
    )
    results_available = models.BooleanField(default=False)
    results_date = models.DateField(blank=True, null=True)
    file = models.FileField(upload_to='lab_results/%Y/%m/%d/', blank=True, null=True)
    
    def get_abnormal_results(self):
        """Get all abnormal results for this lab test"""
        return self.results.filter(is_abnormal=True)

    def __str__(self):
        return f"{self.name} - {self.medical_record.patient.get_full_name()} ({self.test_date})"


class LabResult(models.Model):
    """Individual lab test result values"""
    lab_test = models.ForeignKey(LabTest, on_delete=models.CASCADE, related_name='results')
    test_component = models.CharField(max_length=100)
    value = models.CharField(max_length=50)
    unit = models.CharField(max_length=20, blank=True, null=True)
    reference_range = models.CharField(max_length=50, blank=True, null=True)
    is_abnormal = models.BooleanField(default=False)
    notes = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.test_component}: {self.value} {self.unit or ''}"


class VitalSign(models.Model):
    """Patient vital signs"""
    medical_record = models.ForeignKey(MedicalRecord, on_delete=models.CASCADE, related_name='vital_signs')
    date_recorded = models.DateTimeField()
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recorded_vitals',
        limit_choices_to={'role': 'provider'}
    )
    
    # Common vital signs
    temperature = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True)  # in Celsius
    heart_rate = models.PositiveIntegerField(blank=True, null=True)  # in BPM
    blood_pressure_systolic = models.PositiveIntegerField(blank=True, null=True)  # in mmHg
    blood_pressure_diastolic = models.PositiveIntegerField(blank=True, null=True)  # in mmHg
    respiratory_rate = models.PositiveIntegerField(blank=True, null=True)  # breaths per minute
    oxygen_saturation = models.PositiveIntegerField(blank=True, null=True)  # in percentage
    
    def __str__(self):
        return f"Vitals for {self.medical_record.patient.get_full_name()} ({self.date_recorded})"


class FamilyHistory(models.Model):
    """Patient's family medical history"""
    RELATIONSHIP_CHOICES = [
        ('mother', 'Mother'),
        ('father', 'Father'),
        ('sister', 'Sister'),
        ('brother', 'Brother'),
        ('grandmother_maternal', 'Maternal Grandmother'),
        ('grandfather_maternal', 'Maternal Grandfather'),
        ('grandmother_paternal', 'Paternal Grandmother'),
        ('grandfather_paternal', 'Paternal Grandfather'),
        ('aunt', 'Aunt'),
        ('uncle', 'Uncle'),
        ('cousin', 'Cousin'),
        ('other', 'Other'),
    ]
    
    medical_record = models.ForeignKey(MedicalRecord, on_delete=models.CASCADE, related_name='family_history')
    relationship = models.CharField(max_length=30, choices=RELATIONSHIP_CHOICES)
    condition = models.CharField(max_length=100)
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        verbose_name_plural = "Family histories"
    
    def __str__(self):
        return f"{self.relationship}: {self.condition} - {self.medical_record.patient.get_full_name()}"


class SurgicalHistory(models.Model):
    """Patient's surgical history"""
    medical_record = models.ForeignKey(MedicalRecord, on_delete=models.CASCADE, related_name='surgical_history')
    procedure = models.CharField(max_length=100)
    date = models.DateField()
    surgeon = models.CharField(max_length=100, blank=True, null=True)
    hospital = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        verbose_name_plural = "Surgical histories"
    
    def __str__(self):
        return f"{self.procedure} ({self.date}) - {self.medical_record.patient.get_full_name()}"


class MedicalNote(models.Model):
    """Clinical notes for patient encounters"""
    NOTE_TYPES = [
        ('progress', 'Progress Note'),
        ('soap', 'SOAP Note'),
        ('consultation', 'Consultation Note'),
        ('discharge', 'Discharge Summary'),
        ('procedure', 'Procedure Note'),
        ('other', 'Other'),
    ]
    
    medical_record = models.ForeignKey(MedicalRecord, on_delete=models.CASCADE, related_name='medical_notes')
    note_type = models.CharField(max_length=20, choices=NOTE_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    provider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='authored_notes',
        limit_choices_to={'role': 'provider'}
    )
    appointment = models.ForeignKey(
        'telemedicine.Appointment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notes'
    )
    
    # SOAP format fields
    subjective = models.TextField(blank=True, null=True)
    objective = models.TextField(blank=True, null=True)
    assessment = models.TextField(blank=True, null=True)
    plan = models.TextField(blank=True, null=True)
    
    # For non-SOAP notes
    content = models.TextField(blank=True, null=True)
    
    def is_soap_note(self):
        """Check if this is a SOAP formatted note"""
        return self.note_type == 'soap'

    def has_required_soap_fields(self):
        """Check if all required SOAP fields are present"""
        if not self.is_soap_note():
            return True
        
        return all([
            bool(self.subjective),
            bool(self.objective),
            bool(self.assessment),
            bool(self.plan)
        ])

    def __str__(self):
        return f"{self.get_note_type_display()} - {self.medical_record.patient.get_full_name()} ({self.created_at})"

class MedicalImage(models.Model):
    """Medical imaging studies (X-rays, MRIs, CT scans, etc.)"""
    medical_record = models.ForeignKey(MedicalRecord, on_delete=models.CASCADE, related_name='medical_images')
    image_type = models.CharField(max_length=50)  # e.g., X-ray, MRI, CT, Ultrasound
    body_part = models.CharField(max_length=50)
    date_taken = models.DateField()
    ordered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ordered_images',
        limit_choices_to={'role': 'provider'}
    )
    image_file = models.FileField(upload_to='medical_images/%Y/%m/%d/')
    findings = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.image_type} - {self.body_part} - {self.medical_record.patient.get_full_name()}"


class HealthDocument(models.Model):
    """General health documents (referrals, consent forms, etc.)"""
    DOCUMENT_TYPES = [
        ('referral', 'Referral'),
        ('consent', 'Consent Form'),
        ('advance_directive', 'Advance Directive'),
        ('insurance', 'Insurance Document'),
        ('medical_record', 'External Medical Record'),
        ('other', 'Other'),
    ]
    
    medical_record = models.ForeignKey(MedicalRecord, on_delete=models.CASCADE, related_name='health_documents')
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES)
    title = models.CharField(max_length=100)
    file = models.FileField(upload_to='health_documents/%Y/%m/%d/')
    date_added = models.DateField(auto_now_add=True)
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_health_documents'
    )
    description = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.title} - {self.medical_record.patient.get_full_name()}"


class MedicalHistoryAudit(models.Model):
    """Track changes to medical records for HIPAA compliance"""
    medical_record = models.ForeignKey(MedicalRecord, on_delete=models.CASCADE, related_name='audit_logs')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='medical_record_actions')
    action = models.CharField(max_length=50)  # e.g., "Created", "Updated", "Viewed"
    model_name = models.CharField(max_length=50)  # e.g., "Medication", "LabTest"
    record_id = models.PositiveIntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.TextField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.action} {self.model_name} for {self.medical_record.patient.get_full_name()}"
