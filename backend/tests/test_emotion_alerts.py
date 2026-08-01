import unittest
from decimal import Decimal

from ai.chat_tools import EXTREME_EMOTION_THRESHOLD, _emotion_alerts


class EmotionAlertThresholdTests(unittest.TestCase):
    def test_threshold_is_high_enough_to_only_flag_extreme_emotions(self):
        self.assertEqual(EXTREME_EMOTION_THRESHOLD, Decimal("0.65"))

    def test_flags_only_extreme_negative_or_overconfident_states(self):
        averages = {
            "confianza": 0.9,
            "euforia": 0.2,
            "miedo": 0.2,
            "duda": 0.4,
            "neutral": 0.1,
        }
        peaks = {
            "confianza": 0.9,
            "euforia": 0.72,
            "miedo": 0.2,
            "duda": 0.65,
            "neutral": 0.1,
        }
        alerts = _emotion_alerts(averages, peaks)

        self.assertEqual([alert["emotion"] for alert in alerts], ["euforia", "duda"])


if __name__ == "__main__":
    unittest.main()
