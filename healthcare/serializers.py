# healthcare/serializers.py
from rest_framework import serializers
from .models import (
    MedicalRecord, Allergy, Medication, Condition, Immunization,
    LabTest, LabResult, VitalSign, FamilyHistory, SurgicalHistory,
    MedicalNote, MedicalImage, HealthDocument
)
from users.serializers import CustomUserSerializer

class MedicalRecordSerializer(serializers.ModelSerializer):
    patient_details = CustomUserSerializer(source='patient', read_only=True)
    primary_physician_details = CustomUserSerializer(source='primary_physician', read_only=True)
    age = serializers.SerializerMethodField()
    
    class Meta:
        model = MedicalRecord
        fields = [
            'id', 'patient', 'medical_record_number', 'primary_physician',
            'date_of_birth', 'gender', 'blood_type', 'height', 'weight',
            'created_at', 'updated_at', 'patient_details', 
            'primary_physician_details', 'age'
        ]
        read_only_fields = ['created_at', 'updated_at', 'age']
    
    def get_age(self, obj):
        return obj.calculate_age()


class AllergySerializer(serializers.ModelSerializer):
    class Meta:
        model = Allergy
        fields = [
            'id', 'medical_record', 'allergen', 'reaction',
            'severity', 'diagnosed_date'
        ]


class MedicationSerializer(serializers.ModelSerializer):
    prescribed_by_details = CustomUserSerializer(source='prescribed_by', read_only=True)
    
    class Meta:
        model = Medication
        fields = [
            'id', 'medical_record', 'name', 'dosage', 'frequency',
            'start_date', 'end_date', 'active', 'prescribed_by',
            'reason', 'prescribed_by_details'
        ]


class ConditionSerializer(serializers.ModelSerializer):
    diagnosed_by_details = CustomUserSerializer(source='diagnosed_by', read_only=True)
    
    class Meta:
        model = Condition
        fields = [
            'id', 'medical_record', 'name', 'icd10_code', 'diagnosis_date',
            'resolved_date', 'active', 'diagnosed_by', 'notes',
            'diagnosed_by_details'
        ]


class ImmunizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Immunization
        fields = [
            'id', 'medical_record', 'vaccine', 'administration_date',
            'administered_by', 'lot_number', 'expiration_date', 'notes'
        ]


class LabResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabResult
        fields = [
            'id', 'lab_test', 'test_component', 'value', 'unit',
            'reference_range', 'is_abnormal', 'notes'
        ]


class LabTestSerializer(serializers.ModelSerializer):
    ordered_by_details = CustomUserSerializer(source='ordered_by', read_only=True)
    results = LabResultSerializer(many=True, read_only=True)
    
    class Meta:
        model = LabTest
        fields = [
            'id', 'medical_record', 'name', 'test_date', 'ordered_by',
            'results_available', 'results_date', 'file', 'ordered_by_details',
            'results'
        ]


class VitalSignSerializer(serializers.ModelSerializer):
    recorded_by_details = CustomUserSerializer(source='recorded_by', read_only=True)
    
    class Meta:
        model = VitalSign
        fields = [
            'id', 'medical_record', 'date_recorded', 'recorded_by',
            'temperature', 'heart_rate', 'blood_pressure_systolic',
            'blood_pressure_diastolic', 'respiratory_rate', 'oxygen_saturation',
            'recorded_by_details'
        ]


class FamilyHistorySerializer(serializers.ModelSerializer):
    relationship_display = serializers.CharField(source='get_relationship_display', read_only=True)
    
    class Meta:
        model = FamilyHistory
        fields = [
            'id', 'medical_record', 'relationship', 'relationship_display',
            'condition', 'notes'
        ]


class SurgicalHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SurgicalHistory
        fields = [
            'id', 'medical_record', 'procedure', 'date',
            'surgeon', 'hospital', 'notes'
        ]


class MedicalNoteSerializer(serializers.ModelSerializer):
    provider_details = CustomUserSerializer(source='provider', read_only=True)
    note_type_display = serializers.CharField(source='get_note_type_display', read_only=True)
    
    class Meta:
        model = MedicalNote
        fields = [
            'id', 'medical_record', 'note_type', 'note_type_display',
            'created_at', 'updated_at', 'provider', 'provider_details',
            'appointment', 'subjective', 'objective', 'assessment',
            'plan', 'content'
        ]
        read_only_fields = ['created_at', 'updated_at']


class MedicalImageSerializer(serializers.ModelSerializer):
    ordered_by_details = CustomUserSerializer(source='ordered_by', read_only=True)
    
    class Meta:
        model = MedicalImage
        fields = [
            'id', 'medical_record', 'image_type', 'body_part',
            'date_taken', 'ordered_by', 'ordered_by_details',
            'image_file', 'findings'
        ]


class HealthDocumentSerializer(serializers.ModelSerializer):
    added_by_details = CustomUserSerializer(source='added_by', read_only=True)
    document_type_display = serializers.CharField(source='get_document_type_display', read_only=True)
    
    class Meta:
        model = HealthDocument
        fields = [
            'id', 'medical_record', 'document_type', 'document_type_display',
            'title', 'file', 'date_added', 'added_by', 'added_by_details',
            'description'
        ]
        read_only_fields = ['date_added']
