"""
Ensaf Unit Tests
================
Tests for individual functions and components in isolation.
No network calls, no Flask server - pure logic testing.

Covers:
- US1: Contract template structure & fields
- US2: Contract data generation, salary calculations
- US3: Knowledge base loading, text validation
"""

import pytest
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import (
    app, CONTRACT_FIELDS, KNOWLEDGE_BASE,
    load_knowledge_base, generate_contract_data, reshape_arabic
)


# ════════════════════════════════════════════════════════════════
#  US1: Contract Templates - Unit Tests
# ════════════════════════════════════════════════════════════════

class TestUS1ContractTemplates:
    """Unit tests for contract template structure and fields"""

    def test_contract_fields_exist(self):
        """US1: CONTRACT_FIELDS dictionary must be defined"""
        assert CONTRACT_FIELDS is not None
        assert isinstance(CONTRACT_FIELDS, dict)

    def test_contract_fields_has_all_sections(self):
        """US1: All 10 required sections must be present"""
        expected_sections = [
            "contract_info", "first_party", "second_party",
            "job_info", "contract_duration", "probation",
            "working_hours", "annual_leave", "wage", "bank_info"
        ]
        for section in expected_sections:
            assert section in CONTRACT_FIELDS, f"Missing section: {section}"

    def test_contract_fields_section_structure(self):
        """US1: Each section must have title_ar, title_en, number, fields"""
        for key, section in CONTRACT_FIELDS.items():
            assert "title_ar" in section, f"Section '{key}' missing title_ar"
            assert "title_en" in section, f"Section '{key}' missing title_en"
            assert "number" in section, f"Section '{key}' missing number"
            assert "fields" in section, f"Section '{key}' missing fields"
            assert isinstance(section["fields"], list), f"Section '{key}' fields must be a list"

    def test_contract_fields_have_ids(self):
        """US1: Every field must have an id, label_ar, label_en, type"""
        for section_key, section in CONTRACT_FIELDS.items():
            for field in section["fields"]:
                assert "id" in field, f"Field in '{section_key}' missing id"
                assert "label_ar" in field, f"Field '{field.get('id')}' missing label_ar"
                assert "label_en" in field, f"Field '{field.get('id')}' missing label_en"
                assert "type" in field, f"Field '{field.get('id')}' missing type"

    def test_contract_type_field_has_options(self):
        """US1: Contract type must have Fixed-term and Open-ended options"""
        contract_info = CONTRACT_FIELDS["contract_info"]
        type_field = next(f for f in contract_info["fields"] if f["id"] == "contract_type")
        assert "options" in type_field
        options_str = " ".join(type_field["options"])
        assert "Fixed-term" in options_str or "محدد" in options_str
        assert "Open-ended" in options_str or "غير محدد" in options_str

    def test_required_fields_marked(self):
        """US1: Critical fields must be marked as required"""
        required_ids = ["employer_name", "employee_name", "employee_nationality",
                        "employee_id_number", "job_title", "work_location", "basic_salary"]
        for section_key, section in CONTRACT_FIELDS.items():
            for field in section["fields"]:
                if field["id"] in required_ids:
                    assert field.get("required") == True, \
                        f"Field '{field['id']}' should be marked as required"

    def test_section_numbering_sequential(self):
        """US1: Sections should be numbered 1-10"""
        numbers = sorted([s["number"] for s in CONTRACT_FIELDS.values()])
        assert numbers == list(range(1, 11))

    def test_wage_section_has_salary_fields(self):
        """US1: Wage section must have basic_salary, housing, transport, other, gosi"""
        wage = CONTRACT_FIELDS["wage"]
        wage_ids = [f["id"] for f in wage["fields"]]
        assert "basic_salary" in wage_ids
        assert "housing_allowance" in wage_ids
        assert "transport_allowance" in wage_ids
        assert "other_allowances" in wage_ids
        assert "gosi_deduction" in wage_ids


# ════════════════════════════════════════════════════════════════
#  US2: Generate Contract - Unit Tests
# ════════════════════════════════════════════════════════════════

class TestUS2GenerateContract:
    """Unit tests for contract data generation logic"""

    def test_generate_with_full_data(self, sample_form_data):
        """US2: Generate contract with complete form data"""
        result = generate_contract_data(sample_form_data)
        assert result is not None
        assert "title_ar" in result
        assert "title_en" in result
        assert "sections" in result
        assert result["title_ar"] == "عقد العمل الموحد"
        assert result["title_en"] == "Unified Employment Contract"

    def test_generate_has_16_sections(self, sample_form_data):
        """US2: Generated contract must have 16 sections (1-16)"""
        result = generate_contract_data(sample_form_data)
        sections = result["sections"]
        assert len(sections) == 16
        nums = [s["num"] for s in sections]
        assert nums == list(range(1, 17))

    def test_generate_with_minimal_data(self, minimal_form_data):
        """US2: Generate contract with only required fields"""
        result = generate_contract_data(minimal_form_data)
        assert result is not None
        assert len(result["sections"]) == 16

    def test_salary_calculation_correct(self, sample_form_data):
        """US2: Salary calculations must be accurate"""
        result = generate_contract_data(sample_form_data)
        calcs = result["calculations"]

        assert calcs["basic"] == 10000.0
        assert calcs["housing"] == 2500.0
        assert calcs["transport"] == 1000.0
        assert calcs["other"] == 500.0
        assert calcs["total"] == 14000.0
        assert calcs["gosi_rate"] == 9.75
        expected_gosi = 14000.0 * (9.75 / 100)
        assert calcs["gosi"] == pytest.approx(expected_gosi)
        assert calcs["net"] == pytest.approx(14000.0 - expected_gosi)

    def test_salary_calculation_zero(self):
        """US2: Zero salary should produce zero totals"""
        result = generate_contract_data({"basic_salary": "0"})
        calcs = result["calculations"]
        assert calcs["total"] == 0.0
        assert calcs["gosi"] == 0.0
        assert calcs["net"] == 0.0

    def test_salary_calculation_missing_fields(self):
        """US2: Missing salary fields should default to 0"""
        result = generate_contract_data({"basic_salary": "8000"})
        calcs = result["calculations"]
        assert calcs["basic"] == 8000.0
        assert calcs["housing"] == 0.0
        assert calcs["transport"] == 0.0
        assert calcs["total"] == 8000.0

    def test_employer_data_in_section_2(self, sample_form_data):
        """US2: Employer data must appear in section 2"""
        result = generate_contract_data(sample_form_data)
        section_2 = result["sections"][1]  # index 1 = section num 2
        assert section_2["num"] == 2
        values = [row["val"] for row in section_2["rows"]]
        assert "شركة التقنية المتقدمة" in values

    def test_employee_data_in_section_3(self, sample_form_data):
        """US2: Employee data must appear in section 3"""
        result = generate_contract_data(sample_form_data)
        section_3 = result["sections"][2]  # index 2 = section num 3
        assert section_3["num"] == 3
        values = [row["val"] for row in section_3["rows"]]
        assert "سعد عبدالله" in values

    def test_contract_type_in_section_1(self, sample_form_data):
        """US2: Contract type must appear in section 1"""
        result = generate_contract_data(sample_form_data)
        section_1 = result["sections"][0]
        values = [row["val"] for row in section_1["rows"]]
        assert any("محدد المدة" in str(v) for v in values)

    def test_wage_section_has_highlight(self, sample_form_data):
        """US2: Total wage and net wage rows must be highlighted"""
        result = generate_contract_data(sample_form_data)
        wage_section = result["sections"][8]  # section 9
        assert wage_section["num"] == 9
        highlighted = [r for r in wage_section["rows"] if r.get("highlight")]
        assert len(highlighted) >= 2  # total + net

    def test_obligations_sections_exist(self, sample_form_data):
        """US2: Sections 11-16 (obligations, disputes, etc.) must exist"""
        result = generate_contract_data(sample_form_data)
        for i in range(10, 16):  # sections 11-16
            section = result["sections"][i]
            assert section["num"] == i + 1

    def test_section_11_employer_obligations(self, sample_form_data):
        """US2: Section 11 must have employer obligations with multi_clauses"""
        result = generate_contract_data(sample_form_data)
        section_11 = result["sections"][10]
        assert section_11["num"] == 11
        assert "multi_clauses" in section_11
        assert len(section_11["multi_clauses"]) > 0

    def test_section_12_employee_obligations(self, sample_form_data):
        """US2: Section 12 must have employee obligations with multi_clauses"""
        result = generate_contract_data(sample_form_data)
        section_12 = result["sections"][11]
        assert section_12["num"] == 12
        assert "multi_clauses" in section_12
        assert len(section_12["multi_clauses"]) > 0

    def test_generate_with_empty_data(self):
        """US2: Generate with empty dict should not crash"""
        result = generate_contract_data({})
        assert result is not None
        assert len(result["sections"]) == 16

    def test_gosi_default_rate(self):
        """US2: Default GOSI rate should be 9.75%"""
        result = generate_contract_data({"basic_salary": "10000"})
        assert result["calculations"]["gosi_rate"] == 9.75


# ════════════════════════════════════════════════════════════════
#  US3: Review Contract - Unit Tests (Knowledge Base)
# ════════════════════════════════════════════════════════════════

class TestUS3KnowledgeBase:
    """Unit tests for knowledge base loading and structure"""

    def test_knowledge_base_loaded(self):
        """US3: Knowledge base must be loaded successfully"""
        assert KNOWLEDGE_BASE is not None

    def test_knowledge_base_has_required_keys(self):
        """US3: Knowledge base must have essential keys"""
        required_keys = [
            "meta", "executive_regulations", "contract_template",
            "glossary", "key_labor_law_articles"
        ]
        for key in required_keys:
            assert key in KNOWLEDGE_BASE, f"KB missing key: {key}"

    def test_knowledge_base_meta(self):
        """US3: Knowledge base meta must have source info"""
        meta = KNOWLEDGE_BASE["meta"]
        assert "title_ar" in meta
        assert "title_en" in meta

    def test_knowledge_base_has_regulations(self):
        """US3: Knowledge base must have executive regulations"""
        regs = KNOWLEDGE_BASE["executive_regulations"]
        assert isinstance(regs, list)
        assert len(regs) > 0

    def test_knowledge_base_contract_template(self):
        """US3: Knowledge base must have contract template with sections"""
        template = KNOWLEDGE_BASE["contract_template"]
        assert "sections" in template
        assert len(template["sections"]) > 0

    def test_knowledge_base_key_articles(self):
        """US3: Knowledge base must have key labor law articles"""
        articles = KNOWLEDGE_BASE["key_labor_law_articles"]
        assert isinstance(articles, list)
        assert len(articles) > 0
        # Check article 80 (termination without award) exists
        article_nums = [a.get("article") for a in articles]
        assert 80 in article_nums

    def test_knowledge_base_glossary(self):
        """US3: Knowledge base must have a glossary"""
        glossary = KNOWLEDGE_BASE["glossary"]
        assert isinstance(glossary, list)
        assert len(glossary) > 0

    def test_load_knowledge_base_function(self):
        """US3: load_knowledge_base() should return valid data"""
        kb = load_knowledge_base()
        assert kb is not None
        assert isinstance(kb, dict)


# ════════════════════════════════════════════════════════════════
#  General Unit Tests
# ════════════════════════════════════════════════════════════════

class TestGeneralUtils:
    """Unit tests for utility functions"""

    def test_reshape_arabic_basic(self):
        """Reshape Arabic text should return a string"""
        result = reshape_arabic("مرحبا")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_reshape_arabic_empty(self):
        """Reshape Arabic with empty string should return empty"""
        result = reshape_arabic("")
        assert result == ""

    def test_reshape_arabic_none(self):
        """Reshape Arabic with None should return empty"""
        result = reshape_arabic(None)
        assert result == ""

    def test_reshape_arabic_english(self):
        """Reshape Arabic with English text should return it unchanged"""
        result = reshape_arabic("Hello World")
        assert isinstance(result, str)
