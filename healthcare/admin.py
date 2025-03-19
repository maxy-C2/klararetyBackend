# healthcare/admin.py
from django.contrib import admin
from .models import (
    MedicalRecord, Allergy, Medication, Condition, Immunization,
    LabTest, LabResult, VitalSign, FamilyHistory, SurgicalHistory,
    MedicalNote, MedicalImage, HealthDocument, MedicalHistoryAudit
)

class AllergyInline(admin.TabularInline):
    model = Allergy
    extra = 0

class MedicationInline(admin.TabularInline):
    model = Medication
    extra = 0
    fields = ('name', 'dosage', 'frequency', 'start_date', 'end_date', 'active')

class ConditionInline(admin.TabularInline):
    model = Condition
    extra = 0
    fields = ('name', 'diagnosis_date', 'active')

class VitalSignInline(admin.TabularInline):
    model = VitalSign
    extra = 0
    fields = ('date_recorded', 'temperature', 'heart_rate', 'blood_pressure_systolic', 'blood_pressure_diastolic', 'oxygen_saturation')

@admin.register(MedicalRecord)
class MedicalRecordAdmin(admin.ModelAdmin):
    list_display = ('medical_record_number', 'patient', 'date_of_birth', 'gender', 'primary_physician')
    search_fields = ('medical_record_number', 'patient__first_name', 'patient__last_name')
    list_filter = ('gender',)
    raw_id_fields = ('patient', 'primary_physician')
    inlines = [AllergyInline, MedicationInline, ConditionInline, VitalSignInline]
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Patient Information', {
            'fields': ('patient', 'medical_record_number', 'date_of_birth', 'gender', 'primary_physician')
        }),
        ('Physical Information', {
            'fields': ('blood_type', 'height', 'weight')
        }),
        ('Meta Information', {
            'fields': ('created_at', 'updated_at')
        }),
    )

@admin.register(Allergy)
class AllergyAdmin(admin.ModelAdmin):
    list_display = ('medical_record', 'allergen', 'severity', 'diagnosed_date')
    search_fields = ('allergen', 'medical_record__medical_record_number', 'medical_record__patient__first_name', 'medical_record__patient__last_name')
    list_filter = ('severity',)
    raw_id_fields = ('medical_record',)

@admin.register(Medication)
class MedicationAdmin(admin.ModelAdmin):
    list_display = ('medical_record', 'name', 'dosage', 'frequency', 'active')
    search_fields = ('name', 'medical_record__medical_record_number', 'medical_record__patient__first_name', 'medical_record__patient__last_name')
    list_filter = ('active',)
    raw_id_fields = ('medical_record', 'prescribed_by')

@admin.register(Condition)
class ConditionAdmin(admin.ModelAdmin):
    list_display = ('medical_record', 'name', 'icd10_code', 'diagnosis_date', 'active')
    search_fields = ('name', 'icd10_code', 'medical_record__medical_record_number', 'medical_record__patient__first_name', 'medical_record__patient__last_name')
    list_filter = ('active',)
    raw_id_fields = ('medical_record', 'diagnosed_by')

@admin.register(Immunization)
class ImmunizationAdmin(admin.ModelAdmin):
    list_display = ('medical_record', 'vaccine', 'administration_date')
    search_fields = ('vaccine', 'medical_record__medical_record_number', 'medical_record__patient__first_name', 'medical_record__patient__last_name')
    raw_id_fields = ('medical_record',)

class LabResultInline(admin.TabularInline):
    model = LabResult
    extra = 0

@admin.register(LabTest)
class LabTestAdmin(admin.ModelAdmin):
    list_display = ('medical_record', 'name', 'test_date', 'results_available')
    search_fields = ('name', 'medical_record__medical_record_number', 'medical_record__patient__first_name', 'medical_record__patient__last_name')
    list_filter = ('results_available',)
    raw_id_fields = ('medical_record', 'ordered_by')
    inlines = [LabResultInline]

@admin.register(LabResult)
class LabResultAdmin(admin.ModelAdmin):
    list_display = ('lab_test', 'test_component', 'value', 'unit', 'is_abnormal')
    search_fields = ('test_component', 'lab_test__name', 'lab_test__medical_record__medical_record_number')
    list_filter = ('is_abnormal',)
    raw_id_fields = ('lab_test',)

@admin.register(VitalSign)
class VitalSignAdmin(admin.ModelAdmin):
    list_display = ('medical_record', 'date_recorded', 'temperature', 'heart_rate', 'blood_pressure_systolic', 'blood_pressure_diastolic')
    search_fields = ('medical_record__medical_record_number', 'medical_record__patient__first_name', 'medical_record__patient__last_name')
    raw_id_fields = ('medical_record', 'recorded_by')

@admin.register(FamilyHistory)
class FamilyHistoryAdmin(admin.ModelAdmin):
    list_display = ('medical_record', 'relationship', 'condition')
    search_fields = ('condition', 'medical_record__medical_record_number', 'medical_record__patient__first_name', 'medical_record__patient__last_name')
    list_filter = ('relationship',)
    raw_id_fields = ('medical_record',)

@admin.register(SurgicalHistory)
class SurgicalHistoryAdmin(admin.ModelAdmin):
    list_display = ('medical_record', 'procedure', 'date', 'surgeon', 'hospital')
    search_fields = ('procedure', 'surgeon', 'hospital', 'medical_record__medical_record_number', 'medical_record__patient__first_name', 'medical_record__patient__last_name')
    raw_id_fields = ('medical_record',)

@admin.register(MedicalNote)
class MedicalNoteAdmin(admin.ModelAdmin):
    list_display = ('medical_record', 'note_type', 'created_at', 'provider')
    search_fields = ('medical_record__medical_record_number', 'medical_record__patient__first_name', 'medical_record__patient__last_name', 'subjective', 'objective', 'assessment', 'plan', 'content')
    list_filter = ('note_type',)
    raw_id_fields = ('medical_record', 'provider', 'appointment')
    fieldsets = (
        ('Basic Information', {
            'fields': ('medical_record', 'note_type', 'provider', 'appointment')
        }),
        ('SOAP Note', {
            'fields': ('subjective', 'objective', 'assessment', 'plan'),
            'classes': ('collapse',),
            'description': 'Fields for SOAP note type'
        }),
        ('Other Note', {
            'fields': ('content',),
            'classes': ('collapse',),
            'description': 'Content for non-SOAP notes'
        }),
    )
    readonly_fields = ('created_at', 'updated_at')

@admin.register(MedicalImage)
class MedicalImageAdmin(admin.ModelAdmin):
    list_display = ('medical_record', 'image_type', 'body_part', 'date_taken')
    search_fields = ('image_type', 'body_part', 'findings', 'medical_record__medical_record_number', 'medical_record__patient__first_name', 'medical_record__patient__last_name')
    list_filter = ('image_type',)
    raw_id_fields = ('medical_record', 'ordered_by')

@admin.register(HealthDocument)
class HealthDocumentAdmin(admin.ModelAdmin):
    list_display = ('medical_record', 'document_type', 'title', 'date_added', 'added_by')
    search_fields = ('title', 'description', 'medical_record__medical_record_number', 'medical_record__patient__first_name', 'medical_record__patient__last_name')
    list_filter = ('document_type',)
    raw_id_fields = ('medical_record', 'added_by')
    readonly_fields = ('date_added',)

@admin.register(MedicalHistoryAudit)
class MedicalHistoryAuditAdmin(admin.ModelAdmin):
    list_display = ('medical_record', 'user', 'action', 'model_name', 'timestamp', 'ip_address')
    search_fields = ('medical_record__medical_record_number', 'user__username', 'action', 'model_name', 'details')
    list_filter = ('action', 'model_name')
    readonly_fields = ('medical_record', 'user', 'action', 'model_name', 'record_id', 'timestamp', 'details', 'ip_address')
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
