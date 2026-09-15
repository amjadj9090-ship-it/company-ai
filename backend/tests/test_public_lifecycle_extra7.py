def test_public_lifecycle_order_payload():
    from backend.app.public_lifecycle import Order
    assert 'token' in Order.model_fields
