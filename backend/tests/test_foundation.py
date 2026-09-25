from app.foundation import CompanyAIRequest


def test_company_ai_request_normalizes_message_and_context():
    request = CompanyAIRequest(
        message="  Create a lead  ",
        channel="website",
        language="ar",
        context={"source": "landing"},
    )

    assert request.as_context() == {
        "message": "Create a lead",
        "channel": "website",
        "language": "ar",
        "context": {"source": "landing"},
    }


def test_company_ai_request_rejects_empty_message():
    try:
        CompanyAIRequest(message="   ")
    except ValueError as exc:
        assert "message" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_company_ai_request_rejects_oversized_message():
    try:
        CompanyAIRequest(message="x" * 12001)
    except ValueError as exc:
        assert "12000" in str(exc)
    else:
        raise AssertionError("Expected ValueError")
