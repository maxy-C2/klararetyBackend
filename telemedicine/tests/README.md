# Telemedicine Application Test Suite

This directory contains the test suite for the Telemedicine application.

## Test Structure

The tests are organized into three categories:

- **Unit Tests** (`tests/unit/`): These test individual components in isolation.
- **Integration Tests** (`tests/integration/`): These test how components interact with each other.
- **Functional Tests** (`tests/functional/`): These test complete user flows and scenarios.

## Running the Tests

### Running All Tests

```bash
python manage.py test telemedicine
```

### Running with pytest

For more flexibility and features, we recommend using pytest:

```bash
pytest telemedicine/tests/
```

### Running Specific Test Categories

```bash
# Unit tests only
pytest telemedicine/tests/unit/

# Integration tests only
pytest telemedicine/tests/integration/

# Functional tests only
pytest telemedicine/tests/functional/
```

### Running Specific Test Files

```bash
pytest telemedicine/tests/unit/test_models.py
```

### Running Specific Test Classes or Methods

```bash
# Run a specific test class
pytest telemedicine/tests/unit/test_models.py::AppointmentModelTests

# Run a specific test method
pytest telemedicine/tests/unit/test_models.py::AppointmentModelTests::test_appointment_creation
```

## Test Coverage

To generate a test coverage report:

```bash
coverage run --source='telemedicine' manage.py test telemedicine
coverage report
```

For an HTML report:

```bash
coverage html
```

Then open `htmlcov/index.html` in your browser.

## Common Fixtures

Common test fixtures are available in `tests/conftest.py`. These include:

- User fixtures: `patient_user`, `provider_user`, `admin_user`, `pharmco_user`
- API Client fixtures: `api_client`, `patient_client`, `provider_client`, `admin_client`
- Model fixtures: `appointment`, `consultation`, `prescription`, `message`, etc.

## Mocking External Services

For tests that involve external services like Zoom, email, etc., use the provided mocks:

```python
@patch('telemedicine.services.zoom_service.ZoomService')
def test_example(self, mock_zoom_service):
    # Configure the mock
    mock_instance = mock_zoom_service.return_value
    mock_instance.create_meeting.return_value = {...}
    
    # Test code here
```

## Writing New Tests

When writing new tests:

1. Place them in the appropriate category directory
2. Use existing fixtures when possible
3. Use meaningful names for test methods (e.g., `test_user_can_reschedule_appointment`)
4. Include docstrings explaining what the test verifies
5. Ensure proper cleanup of test data
