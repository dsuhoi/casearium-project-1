import unittest

from classifier import classify_support_request


class ClassifierTestCase(unittest.TestCase):
    def test_demo_cases(self) -> None:
        cases = [
            (
                "Какая комиссия за перевод между своими счетами?",
                "B2C",
                "consultation",
                "Normal",
                "b2c_consultant_agent",
            ),
            (
                "Как настроить вебхук для получения уведомлений о платежах?",
                "B2B",
                "technical_issue",
                "Normal",
                "b2b_expert_agent",
            ),
            (
                "Мне пришло смс о списании 50 000 руб, но это не я! Взлом!",
                "B2C",
                "security_incident",
                "Critical",
                "security_ops_agent",
            ),
            (
                "Уже третий день не могу войти в приложение, никто не отвечает! Верните деньги!",
                "B2C",
                "complaint",
                "High",
                "complaints_agent",
            ),
            (
                "Хватит ботов, соедините с живым менеджером, вопрос срочный!",
                "B2B",
                "escalation",
                "High",
                "human_agent",
            ),
            (
                "Нужны условия тарифа для юридических лиц по интеграции API",
                "B2B",
                "technical_issue",
                "Normal",
                "b2b_expert_agent",
            ),
        ]

        for message, client_type, category, priority, route_to in cases:
            with self.subTest(message=message):
                payload = {"message": message, "source": "web_chat"}
                result = classify_support_request(payload)
                self.assertEqual(result["client_type"], client_type)
                self.assertEqual(result["category"], category)
                self.assertEqual(result["priority"], priority)
                self.assertEqual(result["route_to"], route_to)
                self.assertIsInstance(result["confidence"], float)
                self.assertTrue(result["summary"])


if __name__ == "__main__":
    unittest.main()
