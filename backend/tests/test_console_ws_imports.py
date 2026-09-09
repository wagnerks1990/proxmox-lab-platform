def test_console_ws_router_importable():
    from app.api.routers.console_ws import router

    assert router is not None
