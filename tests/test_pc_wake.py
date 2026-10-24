import asyncio
import io
import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from urllib.error import HTTPError, URLError

from ranni_assistant.commands import install
from ranni_assistant.home_assistant import request_json, valid_url, _NoRedirect
from ranni_assistant.pc_wake import wake_pc


ENV = {"HOME_ASSISTANT_URL": "http://example.invalid:8123",
       "HOME_ASSISTANT_TOKEN": "fake-secret",
       "HOME_ASSISTANT_WAKE_ENTITY": "script.wake_gaming_pc"}


class WakeTests(unittest.IsolatedAsyncioTestCase):
    async def test_fixed_request_and_accepted_wording(self):
        with patch.dict(os.environ, ENV, clear=True), patch(
                "ranni_assistant.pc_wake.request_json", return_value=[]) as request:
            result = await wake_pc()
        request.assert_called_once_with(ENV["HOME_ASSISTANT_URL"], "fake-secret",
                                       "/api/services/script/turn_on",
                                       {"entity_id": "script.wake_gaming_pc"})
        self.assertIn("angenommen", result)
        self.assertIn("noch keinen PC-Start", result)

    async def test_invalid_or_missing_configuration_never_calls_api(self):
        cases = [{}, *[dict(ENV, HOME_ASSISTANT_WAKE_ENTITY=value) for value in
                 ("", "switch.pc", "script.", "script.pc,script.other", "script.pc/../other")],
                 dict(ENV, HOME_ASSISTANT_URL="http://user:secret@example.invalid"),
                 dict(ENV, HOME_ASSISTANT_TOKEN="bad\nheader")]
        for env in cases:
            with self.subTest(env_keys=list(env)), patch.dict(os.environ, env, clear=True), patch(
                    "ranni_assistant.pc_wake.request_json") as request:
                result = await wake_pc()
                request.assert_not_called()
                self.assertNotIn("angenommen", result)

    async def test_failures_are_sanitized_and_not_retried(self):
        for error in (TimeoutError("fake-secret"), URLError("fake-secret"),
                      HTTPError("secret-url", 401, "fake-secret", {}, None),
                      HTTPError("secret-url", 404, "fake-secret", {}, None),
                      HTTPError("secret-url", 500, "fake-secret", {}, None),
                      ValueError("fake-secret"), OSError("fake-secret")):
            with self.subTest(error=type(error).__name__), patch.dict(os.environ, ENV, clear=True), patch(
                    "ranni_assistant.pc_wake.request_json", side_effect=error) as request:
                result = await wake_pc()
                request.assert_called_once()
                self.assertNotIn("fake-secret", result)
                self.assertNotIn("secret-url", result)
                self.assertNotIn("angenommen", result)

    async def test_outer_deadline(self):
        async def expire(awaitable, timeout):
            self.assertEqual(timeout, 8)
            awaitable.close()
            raise TimeoutError
        with patch.dict(os.environ, ENV, clear=True), patch(
                "ranni_assistant.pc_wake.asyncio.wait_for", side_effect=expire):
            self.assertIn("Zeitüberschreitung", await wake_pc())

    async def test_transport_runs_off_event_loop(self):
        import threading
        main_thread = threading.get_ident()
        def request(*args):
            self.assertNotEqual(main_thread, threading.get_ident())
            return []
        with patch.dict(os.environ, ENV, clear=True), patch(
                "ranni_assistant.pc_wake.request_json", side_effect=request):
            await wake_pc()


class TransportTests(unittest.TestCase):
    def test_post_wire_format_and_timeout(self):
        with patch("ranni_assistant.home_assistant.build_opener") as opener:
            opener.return_value.open.return_value.__enter__.return_value = io.BytesIO(b"[]")
            self.assertEqual(request_json(ENV["HOME_ASSISTANT_URL"], "fake-secret",
                             "/api/services/script/turn_on", {"entity_id": "script.pc"}), [])
            args, kwargs = opener.return_value.open.call_args
            request = args[0]
            self.assertEqual(request.get_method(), "POST")
            self.assertEqual(request.full_url, ENV["HOME_ASSISTANT_URL"] + "/api/services/script/turn_on")
            self.assertEqual(json.loads(request.data), {"entity_id": "script.pc"})
            self.assertEqual(request.get_header("Authorization"), "Bearer fake-secret")
            self.assertEqual(request.get_header("Content-type"), "application/json")
            self.assertEqual(kwargs["timeout"], 6)

    def test_url_validation_and_redirect_rejection(self):
        self.assertTrue(valid_url(ENV["HOME_ASSISTANT_URL"]))
        for value in ("ftp://host", "http://", "http://host:bad", "http://host/path",
                      "http://host?token=secret", "http://host#fragment", "http://user:pass@host"):
            self.assertFalse(valid_url(value))
        self.assertIsNone(_NoRedirect().redirect_request(None, None, 302, "", {}, "http://other"))


class CommandTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Lightweight decorator harness avoids importing/starting the legacy bot.
        self.callbacks = {}
        def command(**options):
            def decorate(callback):
                self.callbacks[options["name"]] = callback
                callback.command = command
                return callback
            return decorate
        install(SimpleNamespace(group=command))
        self.ctx = SimpleNamespace(author=SimpleNamespace(id=123), send=AsyncMock())

    async def test_owner_only_and_fail_closed(self):
        for owner in ("", "456", "invalid"):
            with patch.dict(os.environ, {"RANNI_OWNER_DISCORD_ID": owner}, clear=True), patch(
                    "ranni_assistant.commands.wake_pc", new_callable=AsyncMock) as wake:
                await self.callbacks["wake"](self.ctx)
                wake.assert_not_awaited()

    async def test_owner_and_reject_arguments(self):
        with patch.dict(os.environ, {"RANNI_OWNER_DISCORD_ID": "123"}, clear=True), patch(
                "ranni_assistant.commands.wake_pc", new_callable=AsyncMock, return_value="accepted") as wake:
            await self.callbacks["wake"](self.ctx, arguments="script.other")
            wake.assert_not_awaited()
            await self.callbacks["wake"](self.ctx)
            wake.assert_awaited_once_with()
            self.ctx.send.assert_awaited_with("accepted")

    async def test_status_preserved(self):
        with patch.dict(os.environ, {"RANNI_OWNER_DISCORD_ID": "123"}, clear=True), patch(
                "ranni_assistant.commands.get_pc_status", new_callable=AsyncMock,
                return_value={"name": "PC", "state": "ONLINE", "detail": "Ping"}) as status:
            await self.callbacks["status"](self.ctx)
            status.assert_awaited_once()
            self.assertIn("ONLINE", self.ctx.send.call_args.args[0])
