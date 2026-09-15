def test_public_lifecycle_order_status_contract():
    from backend.app.public_lifecycle import router
    assert router.prefix.startswith('/api/')
