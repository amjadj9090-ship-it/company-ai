def test_public_lifecycle_token_record_missing_is_safe():
    from backend.app.public_lifecycle import _token_record
    from backend.app import main
    s = main.Session(main.engine)
    try:
        assert _token_record(s, 'definitely-missing-token') is None
    finally:
        s.close()
