import logging

from app.main import MaskToken, configure_logging

RAW = "eyJhbGciOi.payload.assinatura"


def record(msg, args):
    return logging.LogRecord("uvicorn.access", logging.INFO, __file__, 1, msg, args, None)


def test_the_filter_hides_the_token_but_keeps_the_rest_of_the_line():
    rec = record('%s - "%s %s HTTP/%s" %d', ("127.0.0.1:5000", "GET", f"/ws/telemetry?token={RAW}&x=1", "1.1", 101))
    assert MaskToken().filter(rec) is True
    line = rec.getMessage()
    assert RAW not in line
    assert '/ws/telemetry?token=***&x=1' in line and "127.0.0.1:5000" in line and line.endswith("101")


def test_the_filter_also_cleans_a_token_written_in_the_message_itself():
    rec = record('%s - "WebSocket /ws/telemetry?token=' + RAW + '" [accepted]', ("127.0.0.1:5000",))
    MaskToken().filter(rec)
    assert RAW not in rec.getMessage() and rec.getMessage().endswith('token=***" [accepted]')


def test_lines_without_a_token_are_untouched():
    rec = record("%s %s", ("GET", "/health"))
    MaskToken().filter(rec)
    assert rec.getMessage() == "GET /health"


def test_uvicorn_access_and_error_loggers_use_the_filter():
    configure_logging()
    for name in ("uvicorn.access", "uvicorn.error"):  # o access log do HTTP e a linha "WebSocket ... [accepted]"
        assert any(isinstance(f, MaskToken) for f in logging.getLogger(name).filters), name
