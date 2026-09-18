from app.specialist_agents import execute_specialist, get_specialist, SPECIALISTS


def test_all_central_departments_have_specialists():
    expected = {
        "digital_services", "app_development", "sales_crm", "marketing",
        "entrepreneurship", "website_growth", "customer_support",
        "monitoring_operations", "cybersecurity", "finance_legal", "central_brain",
    }
    assert expected.issubset(SPECIALISTS)
    for department in expected:
        assert get_specialist(department) is not None


def test_standard_specialist_execution_completes():
    result = execute_specialist(
        "digital_services",
        "Build a company website",
        ["qualify_need", "match_approved_package", "prepare_quote"],
    )
    assert result["status"] == "completed"
    assert result["agent"] == "web_design"
    assert result["actions_executed"] == ["qualify_need", "match_approved_package", "prepare_quote"]


def test_protected_specialist_execution_is_blocked_without_owner():
    result = execute_specialist(
        "finance_legal",
        "Transfer money to supplier",
        ["verify_request", "prepare_draft", "create_owner_approval"],
    )
    assert result["status"] == "blocked_pending_owner"


def test_authorized_protected_execution_requires_explicit_owner_approval():
    result = execute_specialist(
        "finance_legal",
        "Transfer money to supplier",
        ["verify_request", "prepare_draft", "create_owner_approval"],
        owner_approved=True,
    )
    assert result["status"] == "completed"
