"""
Ensaf (إنصاف) - Intelligent Platform for Legal Contracts in Saudi Arabia
=========================================================================
Flask application implementing employment contracts following official Saudi Labor Law template.
"""

from flask import Flask, render_template, request, jsonify, send_file
import openai
import os
import json
from datetime import datetime
from io import BytesIO
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'ensaf-secret-key')
openai.api_key = os.getenv('OPENAI_API_KEY')

# Load Knowledge Base
def load_knowledge_base():
    kb_path = os.path.join(os.path.dirname(__file__), 'data', 'knowledge_base.json')
    try:
        with open(kb_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return None

KNOWLEDGE_BASE = load_knowledge_base()

# Contract Fields Definition
CONTRACT_FIELDS = {
    "contract_info": {
        "title_ar": "بيانات العقد", "title_en": "Contract Information", "number": 1,
        "fields": [
            {"id": "contract_number", "label_ar": "رقم العقد", "label_en": "Contract No.", "type": "text"},
            {"id": "contract_type", "label_ar": "نوع العقد من حيث مدته", "label_en": "Contract Type", "type": "select", 
             "options": ["محدد المدة / Fixed-term", "غير محدد المدة / Open-ended"]},
            {"id": "contract_date", "label_ar": "تاريخ إبرام العقد", "label_en": "Contract Execution Date", "type": "date"},
            {"id": "start_date", "label_ar": "تاريخ مباشرة العمل", "label_en": "Starting Date", "type": "date"},
            {"id": "end_date", "label_ar": "تاريخ نهاية العقد", "label_en": "Contract End Date", "type": "date"},
            {"id": "contract_location", "label_ar": "مكان إبرام العقد", "label_en": "Contract Execution Location", "type": "text"},
        ]
    },
    "first_party": {
        "title_ar": "بيانات الطرف الأول (شخص اعتباري)", "title_en": "First Party's Information (Legal Person)", "number": 2,
        "fields": [
            {"id": "employer_name", "label_ar": "اسم المنشأة (صاحب العمل)", "label_en": "Establishment Name (Employer)", "type": "text", "required": True},
            {"id": "employer_type", "label_ar": "نوع المنشأة", "label_en": "Establishment Type", "type": "text"},
            {"id": "employer_hrsd_id", "label_ar": "رقم تسجيل HRSD", "label_en": "HRSD Registration Number", "type": "text"},
            {"id": "employer_unified_no", "label_ar": "الرقم الوطني الموحد", "label_en": "Unified National Number", "type": "text"},
            {"id": "employer_address", "label_ar": "العنوان الوطني", "label_en": "National Address", "type": "text"},
            {"id": "employer_phone", "label_ar": "رقم هاتف المنشأة", "label_en": "Phone Number", "type": "text"},
            {"id": "employer_email", "label_ar": "البريد الإلكتروني", "label_en": "Email", "type": "email"},
            {"id": "employer_rep_name", "label_ar": "ممثل المنشأة في التوقيع", "label_en": "Signatory Representative", "type": "text"},
            {"id": "employer_rep_id", "label_ar": "رقم هوية الممثل", "label_en": "Representative ID", "type": "text"},
            {"id": "employer_rep_capacity", "label_ar": "صفته", "label_en": "Capacity", "type": "text"},
        ]
    },
    "second_party": {
        "title_ar": "بيانات الطرف الثاني", "title_en": "Second Party's Information", "number": 3,
        "fields": [
            {"id": "employee_name", "label_ar": "اسم العامل", "label_en": "Employee Name", "type": "text", "required": True},
            {"id": "employee_nationality", "label_ar": "الجنسية", "label_en": "Nationality", "type": "text", "required": True},
            {"id": "employee_id_type", "label_ar": "نوع الهوية", "label_en": "ID Type", "type": "select", "options": ["هوية وطنية / National ID", "إقامة / Resident ID"]},
            {"id": "employee_id_number", "label_ar": "رقم الهوية", "label_en": "ID Number", "type": "text", "required": True},
            {"id": "employee_passport", "label_ar": "رقم الجواز", "label_en": "Passport Number", "type": "text"},
            {"id": "employee_gender", "label_ar": "الجنس", "label_en": "Gender", "type": "select", "options": ["ذكر / Male", "أنثى / Female"]},
            {"id": "employee_marital_status", "label_ar": "الحالة الاجتماعية", "label_en": "Marital Status", "type": "select", "options": ["أعزب / Single", "متزوج / Married"]},
            {"id": "employee_birth_date", "label_ar": "تاريخ الميلاد", "label_en": "Birth Date", "type": "date"},
            {"id": "employee_address", "label_ar": "العنوان الوطني", "label_en": "National Address", "type": "text"},
            {"id": "employee_phone", "label_ar": "رقم الجوال", "label_en": "Mobile Number", "type": "text"},
            {"id": "employee_email", "label_ar": "البريد الإلكتروني", "label_en": "Email", "type": "email"},
        ]
    },
    "job_info": {
        "title_ar": "المهنة ومعلومات العمل", "title_en": "Profession & Work Information", "number": 4,
        "fields": [
            {"id": "job_title", "label_ar": "المسمى الوظيفي", "label_en": "Job Title", "type": "text", "required": True},
            {"id": "work_location", "label_ar": "مقر العمل (المدينة)", "label_en": "Work Location (City)", "type": "text", "required": True},
        ]
    },
    "contract_duration": {
        "title_ar": "مدة العقد", "title_en": "Contract Period", "number": 5,
        "fields": [
            {"id": "duration_months", "label_ar": "مدة العقد (بالأشهر)", "label_en": "Duration (Months)", "type": "number", "default": "12"},
            {"id": "auto_renewal", "label_ar": "التجديد التلقائي", "label_en": "Auto Renewal", "type": "select", "options": ["نعم / Yes", "لا / No"]},
        ]
    },
    "probation": {
        "title_ar": "فترة التجربة", "title_en": "Probationary Period", "number": 6,
        "fields": [{"id": "probation_days", "label_ar": "مدة التجربة (بالأيام)", "label_en": "Probation (Days)", "type": "number", "default": "90"}]
    },
    "working_hours": {
        "title_ar": "ساعات العمل والراحة الأسبوعية", "title_en": "Work Hours & Weekly Rest", "number": 7,
        "fields": [
            {"id": "working_days", "label_ar": "أيام العمل/أسبوع", "label_en": "Working Days/Week", "type": "number", "default": "5"},
            {"id": "working_hours", "label_ar": "ساعات العمل/أسبوع", "label_en": "Working Hours/Week", "type": "number", "default": "48"},
            {"id": "rest_days", "label_ar": "أيام الراحة/أسبوع", "label_en": "Rest Days/Week", "type": "number", "default": "2"},
        ]
    },
    "annual_leave": {
        "title_ar": "الإجازات السنوية", "title_en": "Annual Leaves", "number": 8,
        "fields": [{"id": "vacation_days", "label_ar": "أيام الإجازة السنوية", "label_en": "Annual Leave Days", "type": "number", "default": "21"}]
    },
    "wage": {
        "title_ar": "الأجر والمزايا", "title_en": "Wage & Benefits", "number": 9,
        "fields": [
            {"id": "basic_salary", "label_ar": "الأجر الأساسي (ريال)", "label_en": "Basic Wage (SAR)", "type": "number", "required": True},
            {"id": "housing_allowance", "label_ar": "بدل السكن (ريال)", "label_en": "Housing Allowance (SAR)", "type": "number", "default": "0"},
            {"id": "transport_allowance", "label_ar": "بدل النقل (ريال)", "label_en": "Transport Allowance (SAR)", "type": "number", "default": "0"},
            {"id": "other_allowances", "label_ar": "بدلات أخرى (ريال)", "label_en": "Other Allowances (SAR)", "type": "number", "default": "0"},
            {"id": "gosi_deduction", "label_ar": "استقطاع التأمينات %", "label_en": "GOSI Deduction %", "type": "number", "default": "9.75"},
        ]
    },
    "bank_info": {
        "title_ar": "معلومات الحساب البنكي للطرف الثاني", "title_en": "Bank Account Information", "number": 10,
        "fields": [
            {"id": "bank_name", "label_ar": "اسم البنك", "label_en": "Bank Name", "type": "text"},
            {"id": "iban", "label_ar": "رقم الآيبان", "label_en": "IBAN", "type": "text"},
        ]
    },
}

def generate_contract_data(form_data):
    """Generate structured contract data for table display"""
    basic = float(form_data.get('basic_salary', 0) or 0)
    housing = float(form_data.get('housing_allowance', 0) or 0)
    transport = float(form_data.get('transport_allowance', 0) or 0)
    other = float(form_data.get('other_allowances', 0) or 0)
    total = basic + housing + transport + other
    gosi_rate = float(form_data.get('gosi_deduction', 9.75) or 9.75)
    gosi = total * (gosi_rate / 100)
    net = total - gosi
    
    return {
        "title_ar": "عقد العمل الموحد",
        "title_en": "Unified Employment Contract",
        "date": form_data.get('contract_date', datetime.now().strftime('%Y-%m-%d')),
        "sections": [
            {"num": 1, "title_ar": "بيانات العقد", "title_en": "Contract Information", "rows": [
                {"ar": "رقم العقد", "en": "Contract No.", "val": form_data.get('contract_number', '')},
                {"ar": "نوع العقد من حيث مدته", "en": "Contract Type", "val": form_data.get('contract_type', ''),
                 "note_ar": "عقد محدد المدة/ غير محدد المدة (يتم اختيار نوع العقد من قائمة منسدلة)",
                 "note_en": "Fixed-term Contract / Open-ended Contract (selected from dropdown)"},
                {"ar": "تاريخ إبرام العقد", "en": "Contract Execution Date", "val": form_data.get('contract_date', '')},
                {"ar": "تاريخ مباشرة العمل", "en": "Starting Date", "val": form_data.get('start_date', '')},
                {"ar": "تاريخ نهاية العقد", "en": "Contract End Date", "val": form_data.get('end_date', ''),
                 "note_ar": "(للعقد محدد المدة)", "note_en": "(Fixed-term Contract)"},
                {"ar": "مكان إبرام العقد", "en": "Contract Execution Location", "val": form_data.get('contract_location', '')},
            ]},
            {"num": 2, "title_ar": "بيانات الطرف الأول (شخص اعتباري)", "title_en": "First Party's Information (Legal Person)", "rows": [
                {"ar": "اسم المنشأة (صاحب العمل)", "en": "Establishment Name (Employer)", "val": form_data.get('employer_name', '')},
                {"ar": "نوع المنشأة", "en": "Establishment Type", "val": form_data.get('employer_type', '')},
                {"ar": "رقم تسجيل HRSD", "en": "HRSD Registration Number", "val": form_data.get('employer_hrsd_id', '')},
                {"ar": "الرقم الوطني الموحد", "en": "Unified National Number", "val": form_data.get('employer_unified_no', '')},
                {"ar": "العنوان الوطني", "en": "National Address", "val": form_data.get('employer_address', '')},
                {"ar": "رقم الهاتف", "en": "Phone Number", "val": form_data.get('employer_phone', '')},
                {"ar": "البريد الإلكتروني", "en": "Email", "val": form_data.get('employer_email', '')},
                {"ar": "ممثل المنشأة في التوقيع", "en": "Signatory Representative", "val": form_data.get('employer_rep_name', '')},
                {"ar": "رقم هوية الممثل", "en": "Representative ID", "val": form_data.get('employer_rep_id', '')},
                {"ar": "صفته", "en": "Capacity", "val": form_data.get('employer_rep_capacity', '')},
            ], "footer_ar": "ويشار إليه فيما بعد بـ (الطرف الأول)", "footer_en": "Hereinafter referred to as the (\"First Party\")"},
            {"num": 3, "title_ar": "بيانات الطرف الثاني", "title_en": "Second Party's Information", "rows": [
                {"ar": "اسم العامل", "en": "Employee Name", "val": form_data.get('employee_name', '')},
                {"ar": "الجنسية", "en": "Nationality", "val": form_data.get('employee_nationality', '')},
                {"ar": "نوع الهوية", "en": "ID Type", "val": form_data.get('employee_id_type', '')},
                {"ar": "رقم الهوية", "en": "ID Number", "val": form_data.get('employee_id_number', '')},
                {"ar": "رقم الجواز", "en": "Passport Number", "val": form_data.get('employee_passport', ''),
                 "note_ar": "في حال كان العامل غير سعودي", "note_en": "If non-Saudi"},
                {"ar": "الجنس", "en": "Gender", "val": form_data.get('employee_gender', '')},
                {"ar": "الحالة الاجتماعية", "en": "Marital Status", "val": form_data.get('employee_marital_status', '')},
                {"ar": "تاريخ الميلاد", "en": "Birth Date", "val": form_data.get('employee_birth_date', '')},
                {"ar": "العنوان الوطني", "en": "National Address", "val": form_data.get('employee_address', '')},
                {"ar": "رقم الجوال", "en": "Mobile", "val": form_data.get('employee_phone', '')},
                {"ar": "البريد الإلكتروني", "en": "Email", "val": form_data.get('employee_email', '')},
            ], "footer_ar": "ويشار إليه فيما بعد بـ (الطرف الثاني)", "footer_en": "Hereinafter referred to as the (\"Second Party\")"},
            {"num": 4, "title_ar": "المهنة ومعلومات العمل", "title_en": "Profession & Work's Location", "rows": [
                {"ar": "المسمى الوظيفي", "en": "Job Title", "val": form_data.get('job_title', '')},
                {"ar": "نطاق العمل", "en": "Work Domain", "val": "داخل المملكة / Inside KSA"},
                {"ar": "مقر العمل (المدينة)", "en": "Work Location (City)", "val": form_data.get('work_location', '')},
                {"ar": "نوع عقد العمل", "en": "Work Type", "val": "أصلي / Original Contract"},
            ]},
            {"num": 5, "title_ar": "مدة العقد", "title_en": "Contract Period", "clause": True, "text_ar": f"5.1 يسري هذا العقد لمدة ({form_data.get('duration_months', '12')}) شهراً ابتداءً من تاريخ مباشرة العمل الوارد في البند رقم (1).", "text_en": f"5.1 This contract is valid for ({form_data.get('duration_months', '12')}) months starting from the commencement date in Clause (1)."},
            {"num": 6, "title_ar": "فترة التجربة", "title_en": "Probationary Period", "clause": True, "text_ar": f"6.1 يخضع الطرف الثاني لفترة تجربة مدتها ({form_data.get('probation_days', '90')}) يوماً.", "text_en": f"6.1 The Second Party is subject to a probationary period of ({form_data.get('probation_days', '90')}) days."},
            {"num": 7, "title_ar": "ساعات العمل والراحة الأسبوعية", "title_en": "Work Hours & Weekly Rest", "clause": True, "text_ar": f"تحدد أيام العمل بـ ({form_data.get('working_days', '5')}) أيام وساعات العمل ({form_data.get('working_hours', '48')}) ساعة أسبوعياً، مع ({form_data.get('rest_days', '2')}) أيام راحة.", "text_en": f"Working days: ({form_data.get('working_days', '5')}) days/week, ({form_data.get('working_hours', '48')}) hours/week, with ({form_data.get('rest_days', '2')}) rest days."},
            {"num": 8, "title_ar": "الإجازات السنوية", "title_en": "Annual Leaves", "clause": True, "text_ar": f"8.1 يستحق الطرف الثاني إجازة سنوية مدفوعة الأجر مدتها ({form_data.get('vacation_days', '21')}) يوماً.", "text_en": f"8.1 The Second Party is entitled to ({form_data.get('vacation_days', '21')}) days paid annual leave."},
            {"num": 9, "title_ar": "الأجر والمزايا", "title_en": "Wage & Benefits", "rows": [
                {"ar": "الأجر الأساسي", "en": "Basic Wage", "val": f"{basic:,.2f} ريال / SAR"},
                {"ar": "بدل السكن", "en": "Housing Allowance", "val": f"{housing:,.2f} ريال / SAR"},
                {"ar": "بدل النقل", "en": "Transport Allowance", "val": f"{transport:,.2f} ريال / SAR"},
                {"ar": "بدلات أخرى", "en": "Other Allowances", "val": f"{other:,.2f} ريال / SAR"},
                {"ar": "إجمالي الأجر", "en": "Total Wage", "val": f"{total:,.2f} ريال / SAR", "highlight": True},
                {"ar": f"استقطاع التأمينات ({gosi_rate}%)", "en": f"GOSI Deduction ({gosi_rate}%)", "val": f"-{gosi:,.2f} ريال / SAR"},
                {"ar": "صافي الأجر", "en": "Net Wage", "val": f"{net:,.2f} ريال / SAR", "highlight": True},
            ]},
            {"num": 10, "title_ar": "معلومات الحساب البنكي للطرف الثاني", "title_en": "Bank Account Information", "rows": [
                {"ar": "اسم البنك", "en": "Bank Name", "val": form_data.get('bank_name', '')},
                {"ar": "رقم الآيبان", "en": "IBAN", "val": form_data.get('iban', '')},
            ]},
            # Section 11: First Party's Obligations
            {"num": 11, "title_ar": "التزامات الطرف الأول", "title_en": "First Party's Obligations", "clause": True, "multi_clauses": [
                {"ar": "1.11 يلتزم الطرف الأول بدفع أجر الطرف الثاني حسب المذكور في البند (9)، وتوثيق الدفع عبر منصة الأجور المعتمدة لدى وزارة الموارد البشرية والتنمية الاجتماعية.",
                 "en": "11.1 The First Party shall pay the Second Party's wage mentioned in Clause No. (9) and document the payment via the wage Portal approved by the HRSD."},
                {"ar": "2.11 يلتزم الطرف الأول بدفع العمولات الواردة في الفقرة (3.1.9) من البند رقم (9) للطرف الثاني في تاريخ الاستحقاق.",
                 "en": "11.2 The First Party shall pay the commissions mentioned in Paragraph No. (9.1.3) of Clause No. (9) to the Second Party on the due date."},
                {"ar": "3.11 يلتزم الطرف الأول بتسليم المزايا العينية الواردة في الفقرة (4.1.9) من البند رقم (9) لصالح الطرف الثاني في تاريخ الاستحقاق.",
                 "en": "11.3 The First Party shall provide the Second Party with the in-kind benefits mentioned in Paragraph No. (9.1.4) of Clause No. (9) on the Due Date."},
                {"ar": "4.11 عند تكليف الطرف الثاني بساعات عمل إضافية، يلتزم الطرف الأول بتكليفه كتابياً (أو إلكترونياً)، ويدفع الطرف الأول أجراً إضافياً عن ساعات العمل الإضافية يوازي أجر الساعة الإجمالي مضافاً إليه (50%) من أجر الساعة الأساسي، ويتم دفعه من خلال وسيلة الدفع المذكورة في البند رقم (9).",
                 "en": "11.4 When assigning the Second Party to additional working hours, the First Party is obligated to assign them in writing (or electronically), and the First Party pays an additional wage equal to the total hourly wage plus (50%) of the basic hourly wage."},
                {"ar": "1.4.11 يجوز للطرف الأول بموافقة الطرف الثاني كتابياً (أو إلكترونياً) أن يحتسب للطرف الثاني أيام إجازة تعويضية مدفوعة الأجر بدلاً عن الأجر المستحق للطرف الثاني لساعات العمل الإضافية وفقاً لأحكام اللائحة التنفيذية لنظام العمل.",
                 "en": "11.4.1 The First Party, with the written (or electronic) consent of the Second Party, may count paid compensatory leave days instead of the wages due for the additional working hours."},
                {"ar": "2.4.11 يلتزم الطرف الأول بعدم تجاوز الحد الأعلى لساعات العمل الإضافية المحددة في نظام العمل ولائحته التنفيذية عند تكليف الطرف الثاني، ويجوز بموافقة الطرف الثاني كتابياً (أو إلكترونياً) زيادة عدد الساعات الإضافية عن الحد الأعلى.",
                 "en": "11.4.2 The First Party is obligated not to exceed the maximum limit of additional working hours specified in the Labor Law, and with the written consent of the Second Party, the number of additional hours may be increased beyond the maximum limit."},
                {"ar": "5.11 يلتزم الطرف الأول بتوفير العناية الصحية الوقائية والعلاجية للطرف الثاني مع مراعاة ما يوفره نظام الضمان الصحي التعاوني.",
                 "en": "11.5 The First Party shall provide the Second Party with preventive and curative health care in accordance with the regulations of the Cooperative Health Insurance Law."},
                {"ar": "6.11 يلتزم الطرف الأول بتسجيل الطرف الثاني لدى المؤسسة العامة للتأمينات الاجتماعية، وسداد الاشتراكات حسب أنظمتها.",
                 "en": "11.6 The First Party shall register the Second Party in the General Organization for Social Insurance (GOSI) and fulfill the payments of contributions according to their systems."},
                {"ar": "1.6.11 يلتزم الطرف الأول بدفع رسوم استقدام الطرف الثاني، ورسوم الإقامة ورخصة العمل وتجديدهما وما يترتب على تأخير ذلك من غرامات يتسبب بها الطرف الأول، ورسوم تغيير المهنة، والخروج والعودة وتذكرة عودة الطرف الثاني إلى موطنه بعد انتهاء العلاقة بين الطرفين.",
                 "en": "11.6.1 The First Party is obligated to pay the Second Party's recruitment fees, residency and work permit fees, and their renewal, as well as any fines resulting from delays caused by the First Party."},
                {"ar": "7.11 يلتزم الطرف الأول بمنح الطرف الثاني الإجازة السنوية المنصوص عليها في الفقرة (1.8)، والعطل الرسمية والإجازات المرضية والإجازات الأخرى المنصوص عليها في نظام العمل ولائحة تنظيم العمل.",
                 "en": "11.7 The First Party shall grant the Second Party annual leave stipulated in Paragraph (8.1), and official holidays, sick leaves, and other leaves stipulated in the Labor Law."},
                {"ar": "8.11 يلتزم الطرف الأول برد جميع ما أودعه لديه الطرف الثاني من شهادات أو وثائق خلال المدة المنصوص عليها في الفقرة (9.11).",
                 "en": "11.8 The First Party shall return to the Second Party all certificates or documents that have been submitted during the period stipulated in Paragraph (11.9) hereof."},
                {"ar": "9.11 يلتزم الطرف الأول بدفع أجر الطرف الثاني وتصفية حقوقه خلال أسبوع -كحد أقصى- من تاريخ انتهاء العقد، وفي حال الإنهاء من الطرف الثاني فيلتزم الطرف الأول بدفع أجر الطرف الثاني وتصفية حقوقه خلال مدة لا تزيد عن أسبوعين من تاريخ انتهاء العقد.",
                 "en": "11.9 The First Party shall pay the Second Party's wage and settle its entitlements within a maximum period of one week from the contract end date. If the Second Party ends the contract, the First Party shall settle all entitlements within two weeks."},
                {"ar": "10.11 يلتزم الطرف الأول بدفع مكافأة نهاية الخدمة للطرف الثاني عند انتهاء العقد خلال المدة المنصوص عليها في الفقرة (9.11)، ويستثنى من ذلك إنهاء العقد خلال مدة التجربة أو استقالة الطرف الثاني وخدمته تقل عن سنتين متتاليتين أو كان إنهاء العقد بحسب إحدى الحالات الواردة بالمادة (80) من نظام العمل.",
                 "en": "11.10 The First Party shall pay the Second Party an end-of-service remuneration upon the end of the contract, except for termination during the probationary period, resignation with less than two consecutive years of service, or termination under Article (80)."},
                {"ar": "11.11 يلتزم الطرف الأول بدفع جميع التكاليف والنفقات التي يتحملها الطرف الثاني في سبيل إنهاء المهمات المكلّف بها من قبل الطرف الأول.",
                 "en": "11.11 The First Party shall pay all the costs and expenses incurred by the Second Party to complete the tasks assigned by the First Party."},
            ]},
            # Section 12: Second Party's Obligations
            {"num": 12, "title_ar": "التزامات الطرف الثاني", "title_en": "Second Party's Obligations", "clause": True, "multi_clauses": [
                {"ar": "1.12 يلتزم الطرف الثاني بإنجاز العمل الموكل إليه؛ وفقا لأصول المهنة، ووفقا لتعليمات الطرف الأول، مالم يكن في هذه التعليمات ما يخالف العقد، أو النظام، أو الآداب العامة، ولم يكن في تنفيذها ما يعرضه للخطر.",
                 "en": "12.1 The Second Party is obliged to finish the assigned work in accordance with the principles of the profession and the instructions of the First Party."},
                {"ar": "2.12 يلتزم الطرف الثاني بأن يعتني عناية كافية بالأدوات، والمهمات المسندة إليه والخامات المملوكة للطرف الأول الموضوعة تحت تصرف الطرف الثاني، أو التي تكون في عهدته، وأن يعيد إلى الطرف الأول المواد غير المستهلكة.",
                 "en": "12.2 The Second Party is obliged to take adequate care of the tools and tasks assigned and restore to the First Party the materials that were not used."},
                {"ar": "3.12 يلتزم الطرف الثاني بحسن السلوك والأخلاق أثناء العمل، والالتزام بالأنظمة، والأعراف، والعادات، والآداب المرعية في المملكة العربية السعودية والقواعد واللوائح والتعليمات المعمول بها لدى الطرف الأول، ويتحمل الطرف الثاني كامل الغرامات المالية الناتجة عن مخالفته لتلك الأنظمة.",
                 "en": "12.3 The Second Party is obliged to commit to good behavior and ethics at work, adhere to laws, customs, rules, and etiquette in the Kingdom of Saudi Arabia."},
                {"ar": "4.12 يلتزم الطرف الثاني بأن يقدم كل عون ومساعدة دون أن يشترط لذلك أجراً إضافياً، وذلك في حالات الكوارث والأخطار التي تهدد سلامة مكان العمل أو الأشخاص العاملين فيه.",
                 "en": "12.4 The Second Party is obliged to provide all assistance and support without requiring additional wages in the event of disasters and threats to the safety of the place of work."},
                {"ar": "5.12 يلتزم الطرف الثاني -عند طلب الطرف الأول- بأداء الفحوصات الطبية التي يرغب الطرف الأول إجرائها عليه قبل الالتحاق بالعمل أو أثناءه لغرض التحقق من خلوه من الأمراض المهنية أو السارية.",
                 "en": "12.5 The Second Party is obliged to undergo medical examination, according to the First Party's request, prior to or during work."},
            ]},
            # Section 13: Applicable Law and Settlement of Disputes
            {"num": 13, "title_ar": "النظام واجب التطبيق وتسوية النزاعات", "title_en": "Applicable Law and Settlement of Disputes", "clause": True, "multi_clauses": [
                {"ar": "1.13 يطبق نظام العمل ولائحته التنفيذية واللوائح والقرارات الوزارية ولائحة تنظيم العمل بالمنشأة المعتمدة من قبل وزارة الموارد البشرية والتنمية الاجتماعية على هذا العقد وعلى كل ما لم يرد فيه نص في هذا العقد. ويحل هذا العقد محل كافة الاتفاقيات والعقود السابقة الشفهية منها أو الكتابية بين الطرفين إن وجدت.",
                 "en": "13.1 The Labor Law, its Executive Regulations, ministerial regulations and decisions, and the work policy approved by the Ministry of Human Resources and Social Development shall apply to this contract."},
                {"ar": "2.13 يخضع هذا العقد ويُفسَر وفقاً للأنظمة واللوائح المعمول بها في المملكة العربية السعودية.",
                 "en": "13.2 This contract is governed by and construed in accordance with the laws and regulations in force in the Kingdom of Saudi Arabia."},
                {"ar": "3.13 يعد هذا العقد سنداً تنفيذياً، وينعقد الاختصاص لمحكمة التنفيذ فيما يلي:",
                 "en": "13.3 This contract is considered an executive document, and the jurisdiction shall be vested in the Enforcement Court for the following matters:"},
                {"ar": "1.3.13 التزام الطرف الأول بدفع صافي الأجر المستحق الوارد في الفقرة (7.1.1.9) من البند رقم (9) من هذا العقد.",
                 "en": "13.3.1 The obligation of the First Party to pay the net wage due as stated in Clause (9.1.1.7) of Clause No. (9) hereof."},
                {"ar": "4.13 فيما عدا الحقوق والالتزامات القابلة للتنفيذ الواردة في الفقرة (3.13) من هذا البند، والتي ينعقد الاختصاص فيها لمحكمة التنفيذ وفقاً لنظام التنفيذ، فإن كل نزاع أو خلاف ينشأ عن هذا العقد يتم حلّه ابتداءً من خلال التسوية الودية. وفي حال تعذر الوصول إلى تسوية، فينعقد الاختصاص بنظر النزاع للمحاكم العمالية في المملكة العربية السعودية.",
                 "en": "13.4 Except for the applicable rights and obligations stated in Paragraph (13.3), any dispute or disagreement arising from this contract shall initially be resolved through amicable settlement. If a settlement cannot be reached, the jurisdiction shall lie with the labor courts in the Kingdom of Saudi Arabia."},
            ]},
            # Section 14: General Provisions
            {"num": 14, "title_ar": "أحكام عامة", "title_en": "General Provisions", "clause": True, "multi_clauses": [
                {"ar": "1.14 اتفق الطرفان على أن الإشعارات والإخطارات وأي تصرفات تصدر لأي غرض بناءً على إرادة الطرفين أو أحدهما وذات علاقة بهذا العقد لن تكون منتجة لآثارها القانونية إلا إذا تمّت بواسطة الخدمات أو الوسائل أو النماذج التي تعتمدها المنصة لهذا الغرض ووفقاً لاشتراطاتها ومتطلباتها.",
                 "en": "14.1 The Parties agree that no notices or correspondence issued for any reason will be legally effective unless carried out via the Portal's approved methods."},
                {"ar": "2.14 باستثناء ما ورد في الفقرة (1.11) من البند (11)، وبما لا يتعارض مع الفقرة (1.14) من هذا البند، يحق للطرفين - في حال عدم توفّر الخدمات - توجيه الإشعارات والإخطارات اللازمة بواسطة العنوان الوطني أو بالبريد المسجّل أو الممتاز أو عبر الهاتف أو البريد الإلكتروني.",
                 "en": "14.2 Except as mentioned in Paragraph (11.1), the Parties shall have the right to send notifications via the National Address, registered or express mail, phone, email, or by hand delivery."},
                {"ar": "3.14 يقر الطرفان بعلمهما وقبولهما لكل الشروط والأحكام الواردة في هذا العقد.",
                 "en": "14.3 The Parties acknowledge that they have known and understood all the terms and conditions of this contract."},
                {"ar": "4.14 يوافق الطرف الثاني على استقطاع الطرف الأول للنسبة المقررة عليه من الأجر الشهري للاشتراك في المؤسسة العامة للتأمينات الاجتماعية.",
                 "en": "14.4 The Second Party approves that the First Party will deduct a certain percentage from its monthly wage as a contribution to the GOSI."},
                {"ar": "5.14 يجوز للطرفين الاتفاق على إضافة شروط وأحكام إضافية في بند الشروط الإضافية عند إبرام العقد، بشرط عدم تعارضها مع الشروط والأحكام الواردة في هذا العقد، أو نظام العمل ولائحته التنفيذية أو لائحة تنظيم العمل الداخلية المعتمدة من وزارة الموارد البشرية والتنمية الاجتماعية، وفي حال تعارضها، تعد الشروط الإضافية ملغية.",
                 "en": "14.5 The Parties may add additional terms and conditions in Additional Terms Clause, provided that they shall not contradict the terms hereof, the Labor Law, its Executive Regulations, or the internal work policy."},
                {"ar": "6.14 يُعمل بالتقويم (الميلادي) في كل ما يتعلق بتنفيذ هـذا العـقد.",
                 "en": "14.6 The (Gregorian) calendar shall apply with regard to all matters related to the implementation of this Contract."},
                {"ar": "7.14 تعتبر اللغة العربية هي اللغة المعتمدة في تنفيذ وتفسير هذا العقد، ويجوز للطرفين استخدام لغة أخرى إلى جانب اللغة العربية، وفي حال وجود اختلاف، فيعتد بالنص الوارد باللغة العربية.",
                 "en": "14.7 Arabic shall be the official language for the execution and interpretation of this contract."},
                {"ar": "8.14 يجوز التعديل على البيانات الواردة في البنود المذكورة أدناه بموافقة الطرفين وفقاً للشروط والإجراءات المعتمدة عبر المنصة.",
                 "en": "14.8 The data mentioned in the clauses below may be amended with the consent of both parties through the Portal."},
                {"ar": "9.14 يلتزم الطرف الأول بتوثيق أي تعديل حسب الفقرة (8.14) من خلال المنصة.",
                 "en": "14.9 The First Party shall document any amendment as per Paragraph (14.8) through the Portal."},
                {"ar": "10.14 حرر هذا العقد كنسخة إلكترونية متطابقة لكل من صاحب العمل والعامل وموقعة إلكترونياً من طرفي العقد، وقد تسلم كل طرف نسخته للعمل بموجبها. كما اتفق الطرفان على أن للمنصة الحق في تبادل بيانات هذا العقد وسجل المعاملات المالية وغيرها الناتجة عن تنفيذه.",
                 "en": "14.10 This Contract is made and concluded as an identical electronic counterpart for the Employer and the Employee, who signed it electronically."},
            ]},
            # Section 15: Additional Terms (Optional)
            {"num": 15, "title_ar": "الشروط الإضافية (اختياري)", "title_en": "Additional Terms (Optional)", "clause": True, "multi_clauses": [
                {"ar": "يجوز للطرفين الاتفاق على إضافة أحكام وشروط إضافية بشرط عدم تعارضها مع الشروط والأحكام الواردة هذا العقد الموحد وفي حال تعارضها، تعد الشروط الإضافية ملغية.",
                 "en": "The Parties may add additional terms and conditions, provided that the same shall not contradict the Terms and Conditions hereof; otherwise, the additional terms and conditions will be deemed null and void."},
            ]},
            # Section 16: Appendix
            {"num": 16, "title_ar": "الملحق", "title_en": "Appendix", "clause": True, "multi_clauses": []},
        ],
        "calculations": {"basic": basic, "housing": housing, "transport": transport, "other": other, "total": total, "gosi_rate": gosi_rate, "gosi": gosi, "net": net}
    }

def call_openai(prompt, system_message, max_tokens=2000):
    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": system_message}, {"role": "user", "content": prompt}],
            max_tokens=max_tokens, temperature=0.7
        )
        return {"success": True, "content": response.choices[0].message.content}
    except Exception as e:
        return {"success": False, "error": str(e)}

def explain_clause(clause_text, language="arabic"):
    kb_context = ""
    if KNOWLEDGE_BASE:
        kb_context = f"\n\nKnowledge Base Reference:\n{json.dumps(KNOWLEDGE_BASE.get('sections', [])[:5], ensure_ascii=False, indent=2)[:3000]}"
    
    system_message = f"""You are a legal assistant helping people understand Saudi employment contract clauses.
Give simple, clear explanations in {'Arabic' if language == 'arabic' else 'English'}.
Be concise (2-3 paragraphs max). Highlight risks. Use examples.
Always note this is educational only, not legal advice.{kb_context}"""
    
    prompt = f"Explain this contract clause simply:\n\"{clause_text}\"\n\nLanguage: {'Arabic' if language == 'arabic' else 'English'}"
    return call_openai(prompt, system_message, 1000)

# ── US3: Review Contract - Extract text from uploaded PDF ──
def extract_text_from_pdf(file_storage):
    """Extract text from an uploaded PDF file"""
    try:
        import fitz  # PyMuPDF
        pdf_bytes = file_storage.read()
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text() + "\n"
        doc.close()
        return {"success": True, "text": text.strip()}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ── US3: Review Contract - Compare with standard template using AI ──
def review_contract(contract_text, language="arabic"):
    """Compare uploaded contract text against standard Saudi labor law template"""
    # Build knowledge base context for the AI
    kb_sections = ""
    if KNOWLEDGE_BASE:
        # Get the standard contract template sections
        template = KNOWLEDGE_BASE.get('contract_template', {})
        sections = template.get('sections', [])
        if sections:
            kb_sections = json.dumps(sections[:10], ensure_ascii=False, indent=1)[:4000]
        
        # Get key labor law articles
        key_articles = KNOWLEDGE_BASE.get('key_labor_law_articles', [])
        if key_articles:
            kb_sections += "\n\nKey Labor Law Articles:\n" + json.dumps(key_articles, ensure_ascii=False, indent=1)[:3000]
        
        # Get executive regulations summary
        exec_regs = KNOWLEDGE_BASE.get('executive_regulations', [])
        if exec_regs:
            # Include key regulations (first 20 for context)
            kb_sections += "\n\nExecutive Regulations (sample):\n" + json.dumps(exec_regs[:20], ensure_ascii=False, indent=1)[:2000]

    lang_name = 'Arabic' if language == 'arabic' else 'English'
    
    system_message = f"""You are an expert legal contract reviewer specializing in Saudi Arabian Labor Law (نظام العمل السعودي).
Your task is to compare the user's uploaded contract against the standard unified employment contract template (عقد العمل الموحد) from the Ministry of Human Resources and Social Development.

Standard Contract Template Reference:
{kb_sections}

IMPORTANT RULES:
- Respond ONLY in {lang_name}.
- You are NOT providing legal advice. You are providing an educational comparison only.
- Structure your response clearly with these sections:

1. **نظرة عامة / Overview**: Brief summary of the contract type and what it covers.

2. **البنود الموجودة / Present Clauses**: List the standard clauses that ARE present in the uploaded contract. Use ✅ emoji.

3. **البنود المفقودة / Missing Clauses**: List important standard clauses that are MISSING from the uploaded contract. Use ❌ emoji. Compare against these standard sections:
   - Contract Information (بيانات العقد)
   - First Party / Employer Information (بيانات الطرف الأول)
   - Second Party / Employee Information (بيانات الطرف الثاني)
   - Job Information (المهنة ومعلومات العمل)
   - Contract Duration (مدة العقد)
   - Probationary Period (فترة التجربة)
   - Working Hours (ساعات العمل)
   - Annual Leave (الإجازات)
   - Wage & Benefits (الأجر والمزايا)
   - Bank Account Info (معلومات الحساب البنكي)
   - Employer Obligations (التزامات الطرف الأول)
   - Employee Obligations (التزامات الطرف الثاني)
   - Dispute Resolution (تسوية النزاعات)
   - General Provisions (أحكام عامة)

4. **بنود تحتاج مراجعة / Clauses Needing Attention**: Identify any clauses that seem unclear, potentially risky, or deviate significantly from standard Saudi labor law. Use ⚠️ emoji.

5. **توصيات / Recommendations**: Provide 3-5 actionable recommendations for the user.

6. **ملاحظة / Disclaimer**: Always end with a note that this is an educational tool, not legal advice.

Be thorough but concise. Use bullet points for clarity."""
    
    prompt = f"""Please review and compare the following contract against the standard Saudi unified employment contract template:

--- CONTRACT TEXT ---
{contract_text[:8000]}
--- END CONTRACT TEXT ---

Provide a detailed comparison in {lang_name}."""
    
    return call_openai(prompt, system_message, 3000)

def reshape_arabic(text):
    """Reshape Arabic text for proper PDF rendering"""
    import arabic_reshaper
    from bidi.algorithm import get_display
    if not text:
        return ""
    try:
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)
    except:
        return text

def create_pdf_document(contract_data, form_data):
    """Create PDF in official table format with proper Arabic support"""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        
        # Register Arabic-capable fonts - use bundled fonts
        import os
        font_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts')
        font_regular = os.path.join(font_dir, 'FreeSerif.ttf')
        font_bold = os.path.join(font_dir, 'FreeSerifBold.ttf')
        
        # Fallback to system fonts if bundled fonts not found
        if not os.path.exists(font_regular):
            # Try Linux path
            font_regular = '/usr/share/fonts/truetype/freefont/FreeSerif.ttf'
            font_bold = '/usr/share/fonts/truetype/freefont/FreeSerifBold.ttf'
        if not os.path.exists(font_regular):
            # Try Windows common paths
            for base in [os.path.expanduser('~'), 'C:\\Windows\\Fonts']:
                candidate = os.path.join(base, 'FreeSerif.ttf')
                if os.path.exists(candidate):
                    font_regular = candidate
                    font_bold = os.path.join(base, 'FreeSerifBold.ttf')
                    break
        
        pdfmetrics.registerFont(TTFont('Arabic', font_regular))
        pdfmetrics.registerFont(TTFont('ArabicBold', font_bold))
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=1.5*cm, leftMargin=1.5*cm, topMargin=1.5*cm, bottomMargin=1.5*cm)
        
        styles = getSampleStyleSheet()
        
        # Styles using Arabic font
        title_style = ParagraphStyle('TitleAr', parent=styles['Heading1'], fontSize=16, alignment=TA_CENTER, spaceAfter=10, fontName='ArabicBold')
        title_en_style = ParagraphStyle('TitleEn', parent=styles['Heading1'], fontSize=14, alignment=TA_CENTER, spaceAfter=20, fontName='ArabicBold')
        cell_ar = ParagraphStyle('CellAr', parent=styles['Normal'], fontSize=9, alignment=TA_RIGHT, fontName='Arabic', leading=14)
        cell_en = ParagraphStyle('CellEn', parent=styles['Normal'], fontSize=9, alignment=TA_LEFT, fontName='Arabic', leading=14)
        cell_val = ParagraphStyle('CellVal', parent=styles['Normal'], fontSize=9, alignment=TA_CENTER, fontName='Arabic', leading=14)
        note_style = ParagraphStyle('NoteAr', parent=styles['Normal'], fontSize=8, alignment=TA_CENTER, fontName='Arabic', textColor=colors.HexColor('#1a5f2a'), leading=12)
        clause_ar = ParagraphStyle('ClauseAr', parent=styles['Normal'], fontSize=9, alignment=TA_RIGHT, fontName='Arabic', leading=14, rightIndent=5, leftIndent=5)
        clause_en = ParagraphStyle('ClauseEn', parent=styles['Normal'], fontSize=9, alignment=TA_LEFT, fontName='Arabic', leading=14, rightIndent=5, leftIndent=5)
        
        story = []
        ar = reshape_arabic  # shortcut
        
        # Title
        story.append(Paragraph(ar(contract_data.get('title_ar', 'عقد العمل الموحد')), title_style))
        story.append(Paragraph('Unified Employment Contract', title_en_style))
        story.append(Spacer(1, 10))
        
        # Process sections
        for section in contract_data.get('sections', []):
            # Section header with green background
            header_en = f"{section['num']}    {section['title_en']}"
            header_ar = ar(f"{section['title_ar']}    {section['num']}")
            header_data = [[
                Paragraph(header_en, ParagraphStyle('HdrEn', parent=cell_en, textColor=colors.white, fontName='ArabicBold', fontSize=10)),
                Paragraph(header_ar, ParagraphStyle('HdrAr', parent=cell_ar, textColor=colors.white, fontName='ArabicBold', fontSize=10))
            ]]
            header_table = Table(header_data, colWidths=[doc.width/2, doc.width/2])
            header_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#1a7a7a')),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ]))
            story.append(header_table)
            
            # Handle multi_clauses (sections 11-16)
            if section.get('multi_clauses'):
                for mc in section['multi_clauses']:
                    clause_data = [[
                        Paragraph(mc.get('en', ''), clause_en),
                        Paragraph(ar(mc.get('ar', '')), clause_ar)
                    ]]
                    ct = Table(clause_data, colWidths=[doc.width/2, doc.width/2])
                    ct.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8f9fa')),
                        ('BOX', (0, 0), (-1, -1), 0.25, colors.HexColor('#dee2e6')),
                        ('LINEBELOW', (0, 0), (-1, -1), 0.25, colors.HexColor('#dee2e6')),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                        ('TOPPADDING', (0, 0), (-1, -1), 8),
                        ('LEFTPADDING', (0, 0), (-1, -1), 8),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ]))
                    story.append(ct)
            elif section.get('clause') and not section.get('multi_clauses'):
                # Single clause sections (5-8)
                clause_data = [[
                    Paragraph(section.get('text_en', ''), clause_en),
                    Paragraph(ar(section.get('text_ar', '')), clause_ar)
                ]]
                ct = Table(clause_data, colWidths=[doc.width/2, doc.width/2])
                ct.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8f9fa')),
                    ('BOX', (0, 0), (-1, -1), 0.25, colors.HexColor('#dee2e6')),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                    ('TOPPADDING', (0, 0), (-1, -1), 10),
                    ('LEFTPADDING', (0, 0), (-1, -1), 10),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ]))
                story.append(ct)
            
            if section.get('rows'):
                for row in section['rows']:
                    bg_color = colors.HexColor('#e8f5e9') if row.get('highlight') else colors.white
                    # Reshape Arabic content in the value column too
                    val_text = str(row.get('val', ''))
                    # Check if value contains Arabic characters
                    has_arabic = any('\u0600' <= c <= '\u06FF' for c in val_text)
                    if has_arabic:
                        val_text = ar(val_text)
                    row_data = [[
                        Paragraph(row.get('en', ''), cell_en),
                        Paragraph(val_text, cell_val),
                        Paragraph(ar(row.get('ar', '')), cell_ar)
                    ]]
                    rt = Table(row_data, colWidths=[doc.width*0.30, doc.width*0.40, doc.width*0.30])
                    rt.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, -1), bg_color),
                        ('BOX', (0, 0), (-1, -1), 0.25, colors.HexColor('#dee2e6')),
                        ('LINEBELOW', (0, 0), (-1, -1), 0.25, colors.HexColor('#dee2e6')),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                        ('TOPPADDING', (0, 0), (-1, -1), 6),
                        ('LEFTPADDING', (0, 0), (-1, -1), 6),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ]))
                    story.append(rt)
                    
                    if row.get('note_ar') or row.get('note_en'):
                        note_text = f"{row.get('note_en', '')} | {ar(row.get('note_ar', ''))}"
                        nd = [[Paragraph(note_text, note_style)]]
                        nt = Table(nd, colWidths=[doc.width])
                        nt.setStyle(TableStyle([
                            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#fff3cd')),
                            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                            ('TOPPADDING', (0, 0), (-1, -1), 4),
                        ]))
                        story.append(nt)
                
                if section.get('footer_ar'):
                    fd = [[
                        Paragraph(section.get('footer_en', ''), cell_en),
                        Paragraph(ar(section.get('footer_ar', '')), cell_ar)
                    ]]
                    ft = Table(fd, colWidths=[doc.width/2, doc.width/2])
                    ft.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#e8f5e9')),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                        ('TOPPADDING', (0, 0), (-1, -1), 8),
                        ('LEFTPADDING', (0, 0), (-1, -1), 8),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                    ]))
                    story.append(ft)
            
            story.append(Spacer(1, 8))
        
        # Disclaimer
        story.append(Spacer(1, 15))
        disc_ar = ar("تنويه: هذا نموذج استرشادي وليس استشارة قانونية.")
        disc_en = "Disclaimer: This is a template for reference only, not legal advice."
        dd = [[Paragraph(disc_en, cell_en), Paragraph(disc_ar, cell_ar)]]
        dt = Table(dd, colWidths=[doc.width/2, doc.width/2])
        dt.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#fff3cd')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#ffc107')),
        ]))
        story.append(dt)
        
        doc.build(story)
        buffer.seek(0)
        return {"success": True, "file": buffer}
    except Exception as e:
        import traceback
        return {"success": False, "error": f"{str(e)}\n{traceback.format_exc()}"}

# Routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/app')
def main_app():
    return render_template('app.html', contract_fields=CONTRACT_FIELDS)

@app.route('/api/contract-fields', methods=['GET'])
def get_contract_fields():
    return jsonify({"success": True, "fields": CONTRACT_FIELDS})

@app.route('/api/generate-contract', methods=['POST'])
def generate_contract_api():
    data = request.get_json()
    form_data = data.get('form_data', {})
    contract_data = generate_contract_data(form_data)
    return jsonify({"success": True, "contract": contract_data, "generated_at": datetime.now().isoformat()})

@app.route('/api/explain-clause', methods=['POST'])
def explain_clause_api():
    data = request.get_json()
    clause_text = data.get('clause_text', '')
    language = data.get('language', 'arabic')
    if not clause_text or len(clause_text.strip()) < 10:
        return jsonify({"success": False, "error": "يرجى إدخال نص البند"}), 400
    result = explain_clause(clause_text, language)
    if result["success"]:
        return jsonify({"success": True, "explanation": result["content"]})
    return jsonify({"success": False, "error": result["error"]}), 500

@app.route('/api/export-pdf', methods=['POST'])
def export_pdf():
    data = request.get_json()
    contract_data = data.get('contract_data', {})
    form_data = data.get('form_data', {})
    if not contract_data:
        contract_data = generate_contract_data(form_data)
    result = create_pdf_document(contract_data, form_data)
    if result["success"]:
        filename = f"Ensaf_Contract_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        return send_file(result["file"], as_attachment=True, download_name=filename, mimetype='application/pdf')
    return jsonify({"success": False, "error": result["error"]}), 500

# ── US3: Review Contract API ──
@app.route('/api/review-contract', methods=['POST'])
def review_contract_api():
    """Handle contract review - accepts PDF upload or pasted text"""
    contract_text = ""
    language = "arabic"
    
    # Check if file was uploaded
    if 'contract_file' in request.files:
        file = request.files['contract_file']
        if file and file.filename:
            if file.filename.lower().endswith('.pdf'):
                result = extract_text_from_pdf(file)
                if result["success"]:
                    contract_text = result["text"]
                else:
                    return jsonify({"success": False, "error": f"خطأ في قراءة الملف: {result['error']}"}), 400
            elif file.filename.lower().endswith('.txt'):
                contract_text = file.read().decode('utf-8', errors='ignore')
            else:
                return jsonify({"success": False, "error": "يرجى رفع ملف PDF أو TXT فقط"}), 400
    
    # Check for pasted text
    if not contract_text:
        if request.content_type and 'json' in request.content_type:
            data = request.get_json()
            contract_text = data.get('contract_text', '')
            language = data.get('language', 'arabic')
        else:
            contract_text = request.form.get('contract_text', '')
            language = request.form.get('language', 'arabic')
    else:
        language = request.form.get('language', 'arabic')
    
    if not contract_text or len(contract_text.strip()) < 50:
        return jsonify({"success": False, "error": "يرجى إدخال نص العقد أو رفع ملف PDF (50 حرف على الأقل)"}), 400
    
    # Perform the AI review
    result = review_contract(contract_text, language)
    if result["success"]:
        return jsonify({
            "success": True,
            "review": result["content"],
            "text_length": len(contract_text),
            "reviewed_at": datetime.now().isoformat()
        })
    return jsonify({"success": False, "error": result["error"]}), 500

if __name__ == '__main__':
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║   إنصاف - Ensaf                                           ║
    ║   منصة العقود الذكية - نظام العمل السعودي                  ║
    ║   Running on: http://127.0.0.1:5000                       ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    app.run(debug=True, port=5000)
