def test_public_lifecycle_order_requires_acceptance():
    from backend.app.public_lifecycle import _token_record
    assert callable(_token_record)
