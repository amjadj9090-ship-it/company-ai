def test_public_lifecycle_contract_is_present():
    from backend.app.public_lifecycle import router
    paths = {r.path for r in router.routes}
    assert '/api/public-lifecycle/proposal/view' in paths
    assert '/api/public-lifecycle/proposal/accept' in paths
    assert '/api/public-lifecycle/proposal/order' in paths
