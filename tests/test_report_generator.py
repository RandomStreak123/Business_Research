import os
import unittest
from core.report_generator import slugify, save_report


class TestReportGenerator(unittest.TestCase):
    def test_slugify(self):
        self.assertEqual(slugify("Hello World! 123"), "hello_world_123")
        self.assertEqual(slugify("---special-chars---"), "special_chars")
        self.assertEqual(slugify(""), "business_research_report")

    def test_save_report_docx(self):
        idea = "Autonomous Contract Review AI"
        sections = {
            "executive_summary": "Executive summary paragraph.\n\n- Bullet point 1\n- Bullet point 2",
            "product_idea": "Product vision details.",
            "market_and_competitor_research": "| Competitor | Market Share |\n| --- | --- |\n| CompA | 25% |\n| CompB | 15% |",
            "comparative_analysis": "### Technical Moat\nStrong defensibility.",
            "risk_factors": "Regulatory risks under GDPR.",
            "recommendation": "Initiate sandbox pilot test.",
        }
        run_id = "test_doc_run_999"

        report_path = save_report(idea, sections, run_id, output_format="docx")
        self.assertTrue(os.path.exists(report_path))
        self.assertTrue(report_path.endswith(".docx"))

        # Clean up generated test report
        if os.path.exists(report_path):
            os.remove(report_path)


if __name__ == "__main__":
    unittest.main()
