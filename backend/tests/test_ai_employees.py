from backend.app.ai_employees import EmployeeRequest, execute_employee


def test_standard_website_request_routes_to_digital_employee():
    result = execute_employee(EmployeeRequest(message="Build a company website"))
    assert result.employee["department"] == "digital_services"
    assert result.execution["executed"] is True
    assert result.execution["status"] == "ready_for_execution"


def test_sensitive_request_stays_blocked_until_owner_approval():
    result = execute_employee(EmployeeRequest(message="Sign the customer contract and make the payment"))
    assert result.decision["required_approval"] is True
    assert result.execution["executed"] is False
    assert result.execution["status"] == "approval_required"
