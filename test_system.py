"""
Ensaf System Tests
==================
End-to-end tests simulating complete user flows.
Tests the full journey from template selection to contract output.

Covers:
- US1 → US2: Full flow from template selection to contract generation
- US2 → PDF: Full flow from generation to PDF export
- US3: Full flow from contract upload/paste to review output
- Cross-feature: Navigation, sidebar, all sections accessible
"""

import pytest
import sys
import os
import json
from io import BytesIO
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import app, generate_contract_data


# ════════════════════════════════════════════════════════════════
#  Full Application Structure Tests
# ════════════════════════════════════════════════════════════════

class TestApplicationStructure:
    """System tests verifying the full application structure"""

    def test_all_pages_accessible(self, client):
        """All main pages must return 200"""
        pages = ['/', '/app']
        for page in pages:
            response = client.get(page)
            assert response.status_code == 200, f"Page {page} returned {response.status_code}"

    def test_all_api_endpoints_exist(self, client):
        """All API endpoints must respond (not 404)"""
        # GET endpoints
        response = client.get('/api/contract-fields')
        assert response.status_code == 200

        # POST endpoints - even with empty body should not be 404
        post_endpoints = ['/api/generate-contract', '/api/explain-clause',
                          '/api/export-pdf', '/api/review-contract']
        for endpoint in post_endpoints:
            response = client.post(endpoint,
                data=json.dumps({}), content_type='application/json')
            assert response.status_code != 404, f"Endpoint {endpoint} returned 404"

    def test_app_has_all_four_nav_sections(self, client):
        """App page must have all 4 sidebar navigation items"""
        response = client.get('/app')
        html = response.data.decode('utf-8')
        assert 'data-section="templates"' in html
        assert 'data-section="create"' in html
        assert 'data-section="review"' in html
        assert 'data-section="explain"' in html

    def test_app_has_all_content_sections(self, client):
        """App page must have all 4 content sections"""
        response = client.get('/app')
        html = response.data.decode('utf-8')
        assert 'id="templates"' in html
        assert 'id="create"' in html
        assert 'id="review"' in html
        assert 'id="explain"' in html

    def test_app_templates_is_default_active(self, client):
        """US1 Templates section must be the default active section"""
        response = client.get('/app')
        html = response.data.decode('utf-8')
        # The templates section should have 'active' class
        assert 'id="templates" class="content-section active"' in html

    def test_app_has_disclaimer(self, client):
        """App must contain legal disclaimer"""
        response = client.get('/app')
        html = response.data.decode('utf-8')
        assert 'استشارة قانونية' in html or 'legal advice' in html.lower()

    def test_home_page_links_to_app(self, client):
        """Home page must have link to /app"""
        response = client.get('/')
        html = response.data.decode('utf-8')
        assert '/app' in html


# ════════════════════════════════════════════════════════════════
#  US1 → US2: Template Selection to Contract Generation Flow
# ════════════════════════════════════════════════════════════════

class TestUS1ToUS2Flow:
    """System tests for the complete flow from template to contract"""

    def test_full_fixed_term_contract_flow(self, client, sample_form_data):
        """E2E: Select fixed-term template → fill data → generate contract"""
        # Step 1: Verify templates page is accessible
        response = client.get('/app')
        assert response.status_code == 200
        html = response.data.decode('utf-8')
        assert 'محدد المدة' in html

        # Step 2: Verify contract fields are available
        response = client.get('/api/contract-fields')
        data = json.loads(response.data)
        assert data["success"] == True

        # Step 3: Generate contract with fixed-term type
        sample_form_data["contract_type"] = "محدد المدة / Fixed-term"
        response = client.post('/api/generate-contract',
            data=json.dumps({"form_data": sample_form_data}),
            content_type='application/json')
        data = json.loads(response.data)
        assert data["success"] == True
        contract = data["contract"]

        # Step 4: Verify contract has correct type
        section_1 = contract["sections"][0]
        type_row = next(r for r in section_1["rows"] if "نوع العقد" in r["ar"])
        assert "محدد المدة" in type_row["val"]

    def test_full_open_ended_contract_flow(self, client, sample_form_data):
        """E2E: Select open-ended template → fill data → generate contract"""
        sample_form_data["contract_type"] = "غير محدد المدة / Open-ended"
        sample_form_data["end_date"] = ""  # Open-ended has no end date

        response = client.post('/api/generate-contract',
            data=json.dumps({"form_data": sample_form_data}),
            content_type='application/json')
        data = json.loads(response.data)
        assert data["success"] == True
        contract = data["contract"]

        section_1 = contract["sections"][0]
        type_row = next(r for r in section_1["rows"] if "نوع العقد" in r["ar"])
        assert "غير محدد" in type_row["val"]

    def test_contract_data_consistency(self, client, sample_form_data):
        """E2E: All input data must appear correctly in generated contract"""
        response = client.post('/api/generate-contract',
            data=json.dumps({"form_data": sample_form_data}),
            content_type='application/json')
        data = json.loads(response.data)
        contract = data["contract"]

        # Flatten all row values from all sections
        all_values = []
        for section in contract["sections"]:
            if "rows" in section:
                for row in section["rows"]:
                    all_values.append(str(row.get("val", "")))

        # Check key data appears
        assert any("شركة التقنية المتقدمة" in v for v in all_values)
        assert any("سعد عبدالله" in v for v in all_values)
        assert any("مهندس برمجيات" in v for v in all_values)
        assert any("الرياض" in v for v in all_values)
        assert any("10,000.00" in v or "10000" in v for v in all_values)


# ════════════════════════════════════════════════════════════════
#  US2 → PDF: Contract Generation to PDF Export Flow
# ════════════════════════════════════════════════════════════════

class TestUS2ToPDFFlow:
    """System tests for the complete generation to PDF flow"""

    def test_generate_then_export_pdf(self, client, sample_form_data):
        """E2E: Generate contract → Export as PDF"""
        # Step 1: Generate the contract
        gen_response = client.post('/api/generate-contract',
            data=json.dumps({"form_data": sample_form_data}),
            content_type='application/json')
        gen_data = json.loads(gen_response.data)
        assert gen_data["success"] == True
        contract_data = gen_data["contract"]

        # Step 2: Export as PDF using the generated contract data
        pdf_response = client.post('/api/export-pdf',
            data=json.dumps({
                "contract_data": contract_data,
                "form_data": sample_form_data
            }),
            content_type='application/json')

        assert pdf_response.status_code == 200
        assert pdf_response.content_type == 'application/pdf'
        assert pdf_response.data[:5] == b'%PDF-'
        assert len(pdf_response.data) > 5000  # PDF should be substantial

    def test_pdf_export_without_prior_generation(self, client, sample_form_data):
        """E2E: PDF export with form_data only (no prior generation)"""
        response = client.post('/api/export-pdf',
            data=json.dumps({"form_data": sample_form_data}),
            content_type='application/json')
        assert response.status_code == 200
        assert response.data[:5] == b'%PDF-'

    def test_pdf_varies_by_salary(self, client):
        """E2E: Different salaries must produce different PDFs"""
        data1 = {"form_data": {"basic_salary": "5000", "employer_name": "شركة أ", "employee_name": "أحمد"}}
        data2 = {"form_data": {"basic_salary": "15000", "employer_name": "شركة ب", "employee_name": "محمد"}}

        pdf1 = client.post('/api/export-pdf', data=json.dumps(data1), content_type='application/json')
        pdf2 = client.post('/api/export-pdf', data=json.dumps(data2), content_type='application/json')

        assert pdf1.status_code == 200
        assert pdf2.status_code == 200
        # Different data should produce different PDF content
        assert pdf1.data != pdf2.data


# ════════════════════════════════════════════════════════════════
#  US3: Full Review Contract Flow
# ════════════════════════════════════════════════════════════════

class TestUS3ReviewFlow:
    """System tests for the complete contract review flow"""

    @patch('app.review_contract')
    def test_full_review_with_pasted_text(self, mock_review, client, sample_contract_text_ar):
        """E2E: Paste contract text → Get review with comparison results"""
        mock_review.return_value = {
            "success": True,
            "content": """
            نظرة عامة: العقد يحتوي على بنود أساسية لعقد عمل.
            
            ✅ البنود الموجودة:
            - بيانات الطرف الأول والثاني
            - مدة العقد
            - الأجر
            
            ❌ البنود المفقودة:
            - معلومات الحساب البنكي
            - التزامات الطرف الأول
            - تسوية النزاعات
            
            ⚠️ بنود تحتاج مراجعة:
            - فترة التجربة غير محددة بدقة
            
            توصيات:
            1. إضافة بند تسوية النزاعات
            2. تحديد بدلات السكن والنقل
            """
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
        assert len(data["review"]) > 50
        assert data["text_length"] > 0
        assert "reviewed_at" in data

    @patch('app.review_contract')
    def test_review_flow_english(self, mock_review, client, sample_contract_text_en):
        """E2E: Paste English contract → Get English review"""
        mock_review.return_value = {
            "success": True,
            "content": "Review: The contract covers basic employment terms..."
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
        mock_review.assert_called_with(sample_contract_text_en, "english")

    @patch('app.extract_text_from_pdf')
    @patch('app.review_contract')
    def test_review_flow_with_pdf_upload(self, mock_review, mock_extract, client):
        """E2E: Upload PDF → Extract text → Review"""
        mock_extract.return_value = {
            "success": True,
            "text": "عقد عمل موحد بين الطرف الأول شركة التقنية والطرف الثاني الموظف يتضمن جميع البنود والشروط المطلوبة"
        }
        mock_review.return_value = {
            "success": True,
            "content": "تمت مراجعة العقد بنجاح"
        }

        data = {
            'contract_file': (BytesIO(b'%PDF-fake'), 'contract.pdf'),
            'language': 'arabic'
        }
        response = client.post('/api/review-contract',
            data=data, content_type='multipart/form-data')

        assert response.status_code == 200
        result = json.loads(response.data)
        assert result["success"] == True
        mock_extract.assert_called_once()
        mock_review.assert_called_once()

    def test_review_validation_boundary(self, client):
        """E2E: Text with exactly 50 chars should be accepted"""
        text_50 = "ع" * 50  # Exactly 50 Arabic characters
        with patch('app.review_contract') as mock_review:
            mock_review.return_value = {"success": True, "content": "OK"}
            response = client.post('/api/review-contract',
                data=json.dumps({"contract_text": text_50}),
                content_type='application/json')
            assert response.status_code == 200

    def test_review_validation_below_boundary(self, client):
        """E2E: Text with 49 chars should be rejected"""
        text_49 = "ع" * 49
        response = client.post('/api/review-contract',
            data=json.dumps({"contract_text": text_49}),
            content_type='application/json')
        assert response.status_code == 400


# ════════════════════════════════════════════════════════════════
#  Cross-Feature System Tests
# ════════════════════════════════════════════════════════════════

class TestCrossFeature:
    """System tests spanning multiple features"""

    @patch('app.call_openai')
    def test_generate_then_explain_clause(self, mock_openai, client, sample_form_data):
        """E2E: Generate contract → Pick a clause → Explain it"""
        # Step 1: Generate
        gen_response = client.post('/api/generate-contract',
            data=json.dumps({"form_data": sample_form_data}),
            content_type='application/json')
        contract = json.loads(gen_response.data)["contract"]

        # Step 2: Get a clause from section 5 (contract duration)
        section_5 = contract["sections"][4]
        clause_text = section_5.get("text_ar", "")
        assert len(clause_text) > 10

        # Step 3: Explain the clause
        mock_openai.return_value = {
            "success": True,
            "content": "هذا البند يحدد مدة العقد..."
        }
        explain_response = client.post('/api/explain-clause',
            data=json.dumps({"clause_text": clause_text, "language": "arabic"}),
            content_type='application/json')
        assert explain_response.status_code == 200
        data = json.loads(explain_response.data)
        assert data["success"] == True

    @patch('app.review_contract')
    def test_generate_then_review_own_contract(self, mock_review, client, sample_form_data):
        """E2E: Generate contract → Use its text to review → Comparison"""
        # Step 1: Generate contract
        gen_response = client.post('/api/generate-contract',
            data=json.dumps({"form_data": sample_form_data}),
            content_type='application/json')
        contract = json.loads(gen_response.data)["contract"]

        # Step 2: Build contract text from generated data
        contract_text = ""
        for section in contract["sections"]:
            contract_text += f"{section['title_ar']} - {section['title_en']}\n"
            if "rows" in section:
                for row in section["rows"]:
                    contract_text += f"{row['ar']}: {row['val']}\n"
            if section.get("text_ar"):
                contract_text += section["text_ar"] + "\n"
            if section.get("multi_clauses"):
                for mc in section["multi_clauses"]:
                    contract_text += mc["ar"] + "\n"

        assert len(contract_text) > 100

        # Step 3: Review the generated contract
        mock_review.return_value = {
            "success": True,
            "content": "العقد مطابق للنموذج الموحد بنسبة عالية"
        }
        review_response = client.post('/api/review-contract',
            data=json.dumps({"contract_text": contract_text, "language": "arabic"}),
            content_type='application/json')
        assert review_response.status_code == 200
        assert json.loads(review_response.data)["success"] == True

    def test_all_features_independent(self, client, sample_form_data):
        """E2E: All features must work independently without affecting each other"""
        # Feature 1: Get fields
        r1 = client.get('/api/contract-fields')
        assert r1.status_code == 200

        # Feature 2: Generate contract
        r2 = client.post('/api/generate-contract',
            data=json.dumps({"form_data": sample_form_data}),
            content_type='application/json')
        assert r2.status_code == 200

        # Feature 3: Get fields again (should be same)
        r3 = client.get('/api/contract-fields')
        assert json.loads(r1.data) == json.loads(r3.data)

        # Feature 4: Generate with different data
        sample_form_data["employee_name"] = "خالد عمر"
        r4 = client.post('/api/generate-contract',
            data=json.dumps({"form_data": sample_form_data}),
            content_type='application/json')
        assert r4.status_code == 200
        # Original generate should be different
        assert json.loads(r2.data)["contract"] != json.loads(r4.data)["contract"]
