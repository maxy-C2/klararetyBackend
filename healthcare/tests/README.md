# Healthcare App Testing Guide

This directory contains test cases for the healthcare application. The test structure follows Django best practices for organizing tests for a complex application.

## Test Structure

```
tests/
├── __init__.py
├── fixtures/
│   ├── users.json              # Test users with different roles
│   └── medical_records.json    # Test medical records and related data
├── test_models/                # Tests for Django models
│   ├── __init__.py
│   ├── test_medical_record.py
│   ├── test_medication.py
│   ├── test_condition.py
│   ├── test_lab_test.py
│   └── test_vital_sign.py
├── test_services/              # Tests for service layer
│   ├── __init__.py
│   ├── test_medical_record_service.py
│   ├── test_audit_service.py
│   └── test_document_service.py
├── test_views/                 # Tests for API endpoints
│   ├── __init__.py
│   ├── test_medical_record_api.py
│   ├── test_medication_api.py
│   └── test_condition_api.py
└── test_integration/           # Integration tests
    ├── __init__.py
    ├── test_patient_workflow.py
    └── test_audit_trail.py
```

## Running Tests

You can run the entire test suite with:

```bash
python manage.py test healthcare
```

To run specific test files or test cases:

```bash
# Run all model tests
python manage.py test healthcare.tests.test_models

# Run a specific test file
python manage.py test healthcare.tests.test_models.test_medical_record

# Run a specific test case
python manage.py test healthcare.tests.test_models.test_medical_record.MedicalRecordModelTest

# Run a specific test method
python manage.py test healthcare.tests.test_models.test_medical_record.MedicalRecordModelTest.test_get_active_medications
```

## Test Coverage

To generate a test coverage report, install and run coverage:

```bash
pip install coverage
coverage run --source='healthcare' manage.py test healthcare
coverage report
```

For a more detailed HTML report:

```bash
coverage html
```

Then open `htmlcov/index.html` in your browser.

## Test Types

### Model Tests

These tests verify that Django models work correctly, ensuring:
- Fields are properly defined
- Methods return expected results
- Querysets filter data correctly
- String representations are correct

### Service Tests

These tests focus on the service layer which contains business logic:
- Medical record service operations
- Audit logging functionality
- Document handling

### View/API Tests

These tests ensure that API endpoints:
- Return correct HTTP status codes
- Apply permissions properly
- Return expected data formats
- Process input correctly
- Apply filters correctly

### Integration Tests

These tests verify that components work together correctly:
- Complete patient workflows
- Audit trail generation
- Data consistency across components

## Test Fixtures

The `fixtures` directory contains JSON data used for testing. You can load these fixtures for your tests or when setting up a development environment:

```bash
python manage.py loaddata tests/fixtures/users.json
python manage.py loaddata tests/fixtures/medical_records.json
```
