"""
Ensaf Test Configuration
========================
Shared fixtures for unit, integration, and system tests.
"""

import pytest
import sys
import os
import json

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import app, CONTRACT_FIELDS, KNOWLEDGE_BASE, generate_contract_data


@pytest.fixture
def client():
    """Flask test client"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def sample_form_data():
    """Complete sample form data for contract generation"""
    return {
        "contract_number": "EMP-2025-001",
        "contract_type": "محدد المدة / Fixed-term",
        "contract_date": "2025-01-15",
        "start_date": "2025-02-01",
        "end_date": "2026-01-31",
        "contract_location": "الرياض",
        "employer_name": "شركة التقنية المتقدمة",
        "employer_type": "شركة ذات مسؤولية محدودة",
        "employer_hrsd_id": "12345",
        "employer_unified_no": "700012345",
        "employer_address": "الرياض، حي العليا، شارع الملك فهد",
        "employer_phone": "0112345678",
        "employer_email": "hr@techco.sa",
        "employer_rep_name": "أحمد محمد",
        "employer_rep_id": "1010101010",
        "employer_rep_capacity": "مدير الموارد البشرية",
        "employee_name": "سعد عبدالله",
        "employee_nationality": "سعودي",
        "employee_id_type": "هوية وطنية / National ID",
        "employee_id_number": "1098765432",
        "employee_passport": "",
        "employee_gender": "ذكر / Male",
        "employee_marital_status": "متزوج / Married",
        "employee_birth_date": "1995-06-15",
        "employee_address": "الرياض، حي النزهة",
        "employee_phone": "0551234567",
        "employee_email": "saad@email.com",
        "job_title": "مهندس برمجيات",
        "work_location": "الرياض",
        "duration_months": "12",
        "auto_renewal": "نعم / Yes",
        "probation_days": "90",
        "working_days": "5",
        "working_hours": "48",
        "rest_days": "2",
        "vacation_days": "21",
        "basic_salary": "10000",
        "housing_allowance": "2500",
        "transport_allowance": "1000",
        "other_allowances": "500",
        "gosi_deduction": "9.75",
        "bank_name": "البنك الأهلي السعودي",
        "iban": "SA1234567890123456789012",
    }


@pytest.fixture
def minimal_form_data():
    """Minimal required form data"""
    return {
        "employer_name": "شركة اختبار",
        "employee_name": "عامل اختبار",
        "employee_nationality": "سعودي",
        "employee_id_number": "1234567890",
        "job_title": "موظف",
        "work_location": "الرياض",
        "basic_salary": "5000",
    }


@pytest.fixture
def sample_contract_text_ar():
    """Sample Arabic employment contract text for review testing"""
    return """
    عقد عمل
    الطرف الأول: شركة التقنية المتقدمة
    الطرف الثاني: سعد عبدالله العمري
    
    البند الأول: يلتزم الطرف الثاني بالعمل لدى الطرف الأول بوظيفة مهندس برمجيات.
    البند الثاني: مدة هذا العقد سنة واحدة تبدأ من تاريخ 2025/02/01 وتنتهي في 2026/01/31.
    البند الثالث: يتقاضى الطرف الثاني راتباً شهرياً قدره 10,000 ريال سعودي.
    البند الرابع: ساعات العمل 8 ساعات يومياً، 5 أيام في الأسبوع.
    البند الخامس: يستحق الطرف الثاني إجازة سنوية مدفوعة الأجر مدتها 21 يوماً.
    البند السادس: فترة التجربة 90 يوماً من تاريخ مباشرة العمل.
    """


@pytest.fixture
def sample_contract_text_en():
    """Sample English employment contract text for review testing"""
    return """
    Employment Contract
    First Party (Employer): Advanced Technology Company
    Second Party (Employee): Saad Abdullah Al-Omari
    
    Article 1: The second party shall work for the first party as a Software Engineer.
    Article 2: This contract is valid for one year starting from 01/02/2025 to 31/01/2026.
    Article 3: The second party shall receive a monthly salary of 10,000 SAR.
    Article 4: Working hours are 8 hours daily, 5 days per week.
    Article 5: The second party is entitled to 21 days paid annual leave.
    Article 6: Probation period is 90 days from the date of commencement.
    """
