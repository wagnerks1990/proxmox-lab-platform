def test_request_id_middleware_importable():
    from app.middleware.request_id import RequestIdMiddleware

    assert RequestIdMiddleware is not None
