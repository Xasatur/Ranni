import unittest
from unittest.mock import patch
from ranni_assistant.pc_status import get_pc_status, format_pc_status

class PCStatusTests(unittest.TestCase):
    def test_demo_never_claims_online(self):
        with patch.dict("os.environ", {}, clear=True):
            status = get_pc_status()
        self.assertEqual(status["state"], "DEMO")
        self.assertIn("Kein echter PC-Status", format_pc_status(status))

    def test_custom_display_name(self):
        with patch.dict("os.environ", {"RANNI_PC_NAME": "Desktop"}, clear=True):
            self.assertEqual(get_pc_status()["name"], "Desktop")

if __name__ == "__main__":
    unittest.main()
