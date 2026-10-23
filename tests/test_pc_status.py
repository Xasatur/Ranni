import asyncio
import os
import unittest
from unittest.mock import patch
from ranni_assistant.pc_status import get_pc_status, format_pc_status


class PCStatusTests(unittest.TestCase):
    def test_missing_configuration(self):
        with patch.dict(os.environ, {}, clear=True):
            result = asyncio.run(get_pc_status())
        self.assertEqual(result["state"], "NICHT KONFIGURIERT")

    def test_ping_online(self):
        env = {
            "RANNI_PC_NAME": "Gaming Desktop",
            "HOME_ASSISTANT_URL": "http://example.invalid:8123",
            "HOME_ASSISTANT_TOKEN": "fake-token",
            "HOME_ASSISTANT_PC_ENTITY": "binary_sensor.gaming_pc",
        }
        with patch.dict(os.environ, env, clear=True):
            with patch("ranni_assistant.pc_status._fetch_state", return_value={"state": "on"}):
                result = asyncio.run(get_pc_status())
        self.assertEqual(result["state"], "ONLINE")
        self.assertIn("Gaming Desktop", format_pc_status(result))

    def test_ping_offline(self):
        env = {
            "HOME_ASSISTANT_URL": "http://example.invalid:8123",
            "HOME_ASSISTANT_TOKEN": "fake-token",
            "HOME_ASSISTANT_PC_ENTITY": "binary_sensor.gaming_pc",
        }
        with patch.dict(os.environ, env, clear=True):
            with patch("ranni_assistant.pc_status._fetch_state", return_value={"state": "off"}):
                result = asyncio.run(get_pc_status())
        self.assertEqual(result["state"], "OFFLINE")


if __name__ == "__main__":
    unittest.main()
