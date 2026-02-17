"""
Ensaf Integration Tests
=======================
Tests for Flask route interactions and API endpoints.
Tests the integration between components (routes + logic + templates).
Uses Flask test client - no external API calls (OpenAI mocked).

Covers:
- US1: Template page rendering
- US2: Contract generation API, PDF export API
- US3: Contract review API (input validation, file handling)
"""

import pytest
import sys
import os
import json
from io import BytesIO
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import app


# ════════════════════════════════════════════════════════════════
#  US1: Contract Templates - Integration Tests
# ════════════════════════════════════════════════════════════════

class TestUS1TemplateRoutes:
    """Integration tests for contract template pages"""

    def test_home_page_loads(self, client):
        """US1: Home page (/) must load successfully"""
        response = client.get('/')
        assert response.status_code == 200
        assert 'إنصاف' in response.data.decode('utf-8')

    def test_app_page_loads(self, client):
        """US1: App page (/app) must load successfully"""
        response = client.get('/app')
        assert response.status_code == 200

    def test_app_page_has_template_section(self, client):
        """US1: App page must contain the templates section"""
        response = client.get('/app')
        html = response.data.decode('utf-8')
        assert 'id="templates"' in html
        assert 'US1' in html

    def test_app_page_has_contract_type_cards(self, client):
        """US1: App page must have employment contract type cards"""
        response = client.get('/app')
        html = response.data.decode('utf-8')
        assert 'محدد المدة' in html
        assert 'غير محدد المدة' in html

    def test_app_page_has_labor_law_info(self, client):
        """US1: App page must reference Saudi Labor Law articles"""
        response = client.get('/app')
        html = response.data.decode('utf-8')
        assert 'المادة' in html or 'نظام العمل' in html

    def test_app_page_no_rental_contracts(self, client):
        """US1: App page must NOT have rental or service contract cards"""
        response = client.get('/app')
        html = response.data.decode('utf-8')
        assert 'عقد إيجار' not in html
        assert 'عقد خدمات' not in html

    def test_contract_fields_api(self, client):
        """US1: GET /api/contract-fields must return all fields"""
        response = client.get('/api/contract-fields')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] == True
        assert "fields" in data
        assert len(data["fields"]) == 10  # 10 sections


# ════════════════════════════════════════════════════════════════
#  US2: Generate Contract - Integration Tests
# ════════════════════════════════════════════════════════════════

class TestUS2GenerateContractAPI:
    """Integration tests for contract generation API"""

    def test_generate_contract_success(self, client, sample_form_data):
        """US2: POST /api/generate-contract with valid data must succeed"""
        response = client.post('/api/generate-contract',
            data=json.dumps({"form_data": sample_form_data}),
            content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] == True
        assert "contract" in data
        assert "generated_at" in data

    def test_generate_contract_has_sections(self, client, sample_form_data):
        """US2: Generated contract must contain all 16 sections"""
        response = client.post('/api/generate-contract',
            data=json.dumps({"form_data": sample_form_data}),
            content_type='application/json')
        data = json.loads(response.data)
        contract = data["contract"]
        assert len(contract["sections"]) == 16

    def test_generate_contract_bilingual(self, client, sample_form_data):
        """US2: Generated contract must have both Arabic and English titles"""
        response = client.post('/api/generate-contract',
            data=json.dumps({"form_data": sample_form_data}),
            content_type='application/json')
        data = json.loads(response.data)
        contract = data["contract"]
        assert contract["title_ar"] == "عقد العمل الموحد"
        assert contract["title_en"] == "Unified Employment Contract"
        # Check sections are bilingual
        for section in contract["sections"]:
            assert "title_ar" in section
            assert "title_en" in section

    def test_generate_contract_salary_in_response(self, client, sample_form_data):
        """US2: Response must include salary calculations"""
        response = client.post('/api/generate-contract',
            data=json.dumps({"form_data": sample_form_data}),
            content_type='application/json')
        data = json.loads(response.data)
        assert "calculations" in data["contract"]
        calcs = data["contract"]["calculations"]
        assert calcs["total"] == 14000.0
        assert calcs["net"] > 0

    def test_generate_contract_with_empty_body(self, client):
        """US2: POST with empty form_data should still return valid structure"""
        response = client.post('/api/generate-contract',
            data=json.dumps({"form_data": {}}),
            content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] == True

    def test_generate_contract_minimal(self, client, minimal_form_data):
        """US2: Generate with minimal required data must succeed"""
        response = client.post('/api/generate-contract',
            data=json.dumps({"form_data": minimal_form_data}),
            content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] == True

    def test_app_page_has_generate_section(self, client):
        """US2: App page must contain the create/generate section"""
        response = client.get('/app')
        html = response.data.decode('utf-8')
        assert 'id="create"' in html
        assert 'US2' in html
        assert 'contractForm' in html

    def test_app_page_has_steps_indicator(self, client):
        """US2: App page must have step indicator for the wizard flow"""
        response = client.get('/app')
        html = response.data.decode('utf-8')
        assert 'steps-indicator' in html


class TestUS2ExportPDF:
    """Integration tests for PDF export"""

    def test_export_pdf_with_form_data(self, client, sample_form_data):
        """US2: POST /api/export-pdf with form_data must return PDF"""
        response = client.post('/api/export-pdf',
            data=json.dumps({"form_data": sample_form_data}),
            content_type='application/json')
        assert response.status_code == 200
        assert response.content_type == 'application/pdf'
        assert len(response.data) > 1000  # PDF should have reasonable size

    def test_export_pdf_starts_with_pdf_header(self, client, sample_form_data):
        """US2: Exported file must be a valid PDF (starts with %PDF)"""
        response = client.post('/api/export-pdf',
            data=json.dumps({"form_data": sample_form_data}),
            content_type='application/json')
        assert response.data[:5] == b'%PDF-'

    def test_export_pdf_with_empty_data(self, client):
        """US2: PDF export with empty data should still generate"""
        response = client.post('/api/export-pdf',
            data=json.dumps({"form_data": {}}),
            content_type='application/json')
        assert response.status_code == 200


# ════════════════════════════════════════════════════════════════
#  US3: Review Contract - Integration Tests
# ════════════════════════════════════════════════════════════════

class TestUS3ReviewContractAPI:
    """Integration tests for contract review API"""

    def test_review_page_exists(self, client):
        """US3: App page must contain the review section"""
        response = client.get('/app')
        html = response.data.decode('utf-8')
        assert 'id="review"' in html
        assert 'US3' in html

    def test_review_has_upload_zone(self, client):
        """US3: Review section must have file upload zone"""
        response = client.get('/app')
        html = response.data.decode('utf-8')
        assert 'uploadZone' in html
        assert 'contractFile' in html

    def test_review_has_text_input(self, client):
        """US3: Review section must have text paste area"""
        response = client.get('/app')
        html = response.data.decode('utf-8')
        assert 'review_contract_text' in html

    def test_review_empty_request_fails(self, client):
        """US3: POST /api/review-contract with no data must fail"""
        response = client.post('/api/review-contract',
            data=json.dumps({"contract_text": ""}),
            content_type='application/json')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["success"] == False

    def test_review_short_text_fails(self, client):
        """US3: POST with text < 50 chars must fail"""
        response = client.post('/api/review-contract',
            data=json.dumps({"contract_text": "نص قصير جداً"}),
            content_type='application/json')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["success"] == False

    @patch('app.review_contract')
    def test_review_with_valid_text(self, mock_review, client, sample_contract_text_ar):
        """US3: POST with valid Arabic text must call review_contract"""
        mock_review.return_value = {
            "success": True,
            "content": "تقرير المراجعة: العقد يحتوي على البنود الأساسية..."
        }
        response = client.post('/api/review-contract',
            data=json.dumps({
                "contract_text": sample_contract_text_ar,
                "language": "arabic"
            }),
            content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] == True
        assert "review" in data
        assert "text_length" in data
        assert "reviewed_at" in data
        mock_review.assert_called_once()

    @patch('app.review_contract')
    def test_review_english_language(self, mock_review, client, sample_contract_text_en):
        """US3: Review must support English language option"""
        mock_review.return_value = {
            "success": True,
            "content": "Review Report: The contract contains basic clauses..."
        }
        response = client.post('/api/review-contract',
            data=json.dumps({
                "contract_text": sample_contract_text_en,
                "language": "english"
            }),
            content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] == True

    @patch('app.review_contract')
    def test_review_returns_text_length(self, mock_review, client, sample_contract_text_ar):
        """US3: Review response must include text_length"""
        mock_review.return_value = {"success": True, "content": "OK"}
        response = client.post('/api/review-contract',
            data=json.dumps({"contract_text": sample_contract_text_ar}),
            content_type='application/json')
        data = json.loads(response.data)
        assert data["text_length"] == len(sample_contract_text_ar)

    def test_review_unsupported_file_type(self, client):
        """US3: Uploading unsupported file type must fail"""
        data = {
            'contract_file': (BytesIO(b'test content'), 'contract.docx'),
            'language': 'arabic'
        }
        response = client.post('/api/review-contract',
            data=data, content_type='multipart/form-data')
        assert response.status_code == 400

    @patch('app.extract_text_from_pdf')
    @patch('app.review_contract')
    def test_review_with_txt_upload(self, mock_review, mock_extract, client):
        """US3: Uploading a .txt file must extract text and review"""
        mock_review.return_value = {"success": True, "content": "Review done"}
        txt_content = "عقد عمل بين الطرف الأول والطرف الثاني يتضمن البنود التالية والشروط والأحكام الكاملة"
        data = {
            'contract_file': (BytesIO(txt_content.encode('utf-8')), 'contract.txt'),
            'language': 'arabic'
        }
        response = client.post('/api/review-contract',
            data=data, content_type='multipart/form-data')
        assert response.status_code == 200

    @patch('app.review_contract')
    def test_review_ai_failure_returns_500(self, mock_review, client, sample_contract_text_ar):
        """US3: If AI review fails, API must return 500"""
        mock_review.return_value = {
            "success": False,
            "error": "OpenAI API error"
        }
        response = client.post('/api/review-contract',
            data=json.dumps({"contract_text": sample_contract_text_ar}),
            content_type='application/json')
        assert response.status_code == 500


# ════════════════════════════════════════════════════════════════
#  Explain Clause - Integration Tests
# ════════════════════════════════════════════════════════════════

class TestExplainClauseAPI:
    """Integration tests for clause explanation API"""

    def test_explain_empty_clause_fails(self, client):
        """Explain with empty clause text must fail"""
        response = client.post('/api/explain-clause',
            data=json.dumps({"clause_text": "", "language": "arabic"}),
            content_type='application/json')
        assert response.status_code == 400

    def test_explain_short_clause_fails(self, client):
        """Explain with very short text must fail"""
        response = client.post('/api/explain-clause',
            data=json.dumps({"clause_text": "قصير", "language": "arabic"}),
            content_type='application/json')
        assert response.status_code == 400

    @patch('app.call_openai')
    def test_explain_valid_clause(self, mock_openai, client):
        """Explain with valid clause text must call OpenAI"""
        mock_openai.return_value = {
            "success": True,
            "content": "شرح البند: هذا البند يعني أن..."
        }
        response = client.post('/api/explain-clause',
            data=json.dumps({
                "clause_text": "يلتزم الطرف الثاني بعدم إفشاء أسرار العمل خلال فترة العقد وبعد انتهائه",
                "language": "arabic"
            }),
            content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] == True
        assert "explanation" in data

    def test_explain_page_exists(self, client):
        """Explain section must exist in app page"""
        response = client.get('/app')
        html = response.data.decode('utf-8')
        assert 'id="explain"' in html
        assert 'clause_text' in html
