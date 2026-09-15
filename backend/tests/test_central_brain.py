from app.central_brain import plan


def test_brain_routes_website_to_digital_services():
    d = plan("We need a multilingual company website")
    assert d.department == "digital_services"
    assert d.intent == "service_request"
    assert d.approval_mode == "auto_standard"
    assert d.required_approval is False
    assert "prepare_quote" in d.next_actions


def test_brain_routes_customer_to_sales_crm():
    d = plan("A new customer wants a quote")
    assert d.department == "sales_crm"
    assert d.intent == "lead_or_customer"
    assert d.required_approval is False


def test_brain_owner_gates_sensitive_commitment():
    d = plan("I want to transfer money to this supplier")
    assert d.department == "finance_legal"
    assert d.intent == "sensitive_commitment"
    assert d.approval_mode == "owner"
    assert d.required_approval is True
    assert "create_owner_approval" in d.next_actions


def test_brain_gates_paid_marketing_spend():
    d = plan("Launch a marketing campaign", {"paid_spend": True})
    assert d.department == "marketing"
    assert d.required_approval is True


def test_brain_standard_marketing_can_run_automatically():
    d = plan("Prepare an SEO campaign")
    assert d.department == "marketing"
    assert d.required_approval is False
