def test_public_lifecycle_router_prefix():
    from backend.app.public_lifecycle import router
    assert router.prefix == '/api/public-lifecycle'
