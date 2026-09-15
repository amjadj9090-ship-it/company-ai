def test_public_lifecycle_module_prefix():
    from backend.app.public_lifecycle import router
    assert router.tags == ['public-customer-lifecycle']
