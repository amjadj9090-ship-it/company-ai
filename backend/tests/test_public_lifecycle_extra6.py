def test_public_lifecycle_accept_payload():
    from backend.app.public_lifecycle import Accept
    assert 'token' in Accept.model_fields
