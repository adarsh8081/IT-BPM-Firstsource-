"""
Script to generate 20 synthetic PDF documents for demo purposes
"""

import os
import random
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from typing import List, Dict, Any

# Sample data for PDF generation
DOCUMENT_TYPES = [
    'Medical License', 'DEA Registration', 'Board Certification',
    'Hospital Privileges', 'Malpractice Insurance', 'Continuing Education',
    'Peer Review', 'Quality Assurance', 'Credentialing Application',
    'Background Check', 'Reference Letter', 'Education Verification'
]

HOSPITALS = [
    'City General Hospital', 'Regional Medical Center', 'University Hospital',
    'Community Health Clinic', 'Metropolitan Medical Group', 'Valley Health System',
    'Sunshine Medical Center', 'Riverside Hospital', 'Mountain View Medical'
]

STATES = [
    'California', 'New York', 'Texas', 'Florida', 'Illinois', 'Pennsylvania',
    'Ohio', 'Georgia', 'North Carolina', 'Michigan', 'New Jersey', 'Virginia',
    'Washington', 'Arizona', 'Massachusetts', 'Tennessee', 'Indiana', 'Missouri'
]

def generate_medical_license_pdf(filename: str, provider_data: Dict[str, Any]):
    """Generate a medical license PDF document"""
    doc = SimpleDocTemplate(filename, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.darkblue
    )
    
    story.append(Paragraph("MEDICAL LICENSE", title_style))
    story.append(Spacer(1, 20))
    
    # License information
    license_data = [
        ['License Number:', provider_data['license_number']],
        ['Licensee Name:', f"Dr. {provider_data['first_name']} {provider_data['last_name']}"],
        ['Date of Birth:', f"{random.randint(1950, 1990)}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}"],
        ['Medical School:', random.choice(['Harvard Medical School', 'Johns Hopkins University', 
                                         'Stanford University', 'Mayo Clinic School of Medicine'])],
        ['Graduation Year:', str(random.randint(1985, 2015))],
        ['Specialty:', provider_data['specialty']],
        ['Issue Date:', (datetime.now() - timedelta(days=random.randint(365, 3650))).strftime('%Y-%m-%d')],
        ['Expiry Date:', provider_data['license_expiry'].strftime('%Y-%m-%d')],
        ['Status:', 'Active' if provider_data['license_expiry'] > datetime.now() else 'Expired']
    ]
    
    license_table = Table(license_data, colWidths=[2*inch, 3*inch])
    license_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('BACKGROUND', (1, 0), (1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(license_table)
    story.append(Spacer(1, 30))
    
    # Additional information
    story.append(Paragraph("LICENSE CONDITIONS:", styles['Heading2']))
    conditions = [
        "This license authorizes the practice of medicine within the state of " + provider_data['state'],
        "Licensee must maintain current malpractice insurance coverage",
        "Continuing medical education requirements must be met",
        "License subject to renewal every three years",
        "Any disciplinary actions will be reported to the National Practitioner Data Bank"
    ]
    
    for condition in conditions:
        story.append(Paragraph(f"• {condition}", styles['Normal']))
        story.append(Spacer(1, 6))
    
    story.append(Spacer(1, 20))
    
    # Signature section
    signature_data = [
        ['State Medical Board Official:', '_________________________'],
        ['Date:', datetime.now().strftime('%Y-%m-%d')],
        ['Board Seal:', '[OFFICIAL SEAL]']
    ]
    
    signature_table = Table(signature_data, colWidths=[2*inch, 3*inch])
    signature_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12)
    ]))
    
    story.append(signature_table)
    
    doc.build(story)

def generate_dea_registration_pdf(filename: str, provider_data: Dict[str, Any]):
    """Generate a DEA registration PDF document"""
    doc = SimpleDocTemplate(filename, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.darkred
    )
    
    story.append(Paragraph("DEA REGISTRATION", title_style))
    story.append(Spacer(1, 20))
    
    # Registration information
    dea_number = f"{provider_data['state']}{provider_data['last_name'][:2].upper()}{random.randint(100000, 999999)}"
    
    registration_data = [
        ['DEA Number:', dea_number],
        ['Registrant Name:', f"Dr. {provider_data['first_name']} {provider_data['last_name']}"],
        ['Business Address:', f"{provider_data['address_line1']}, {provider_data['city']}, {provider_data['state']} {provider_data['zip_code']}"],
        ['Business Name:', provider_data['organization']],
        ['Registration Class:', 'Practitioner'],
        ['Schedules:', 'II, III, IV, V'],
        ['Issue Date:', (datetime.now() - timedelta(days=random.randint(365, 3650))).strftime('%Y-%m-%d')],
        ['Expiry Date:', (datetime.now() + timedelta(days=random.randint(30, 1095))).strftime('%Y-%m-%d')],
        ['Status:', 'Active']
    ]
    
    registration_table = Table(registration_data, colWidths=[2*inch, 3*inch])
    registration_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('BACKGROUND', (1, 0), (1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(registration_table)
    story.append(Spacer(1, 30))
    
    # Important notices
    story.append(Paragraph("IMPORTANT NOTICES:", styles['Heading2']))
    notices = [
        "This registration authorizes the prescribing, dispensing, and administration of controlled substances",
        "Registration must be renewed annually",
        "Compliance with all federal and state regulations is required",
        "Any violations may result in revocation of registration",
        "Registration is non-transferable"
    ]
    
    for notice in notices:
        story.append(Paragraph(f"• {notice}", styles['Normal']))
        story.append(Spacer(1, 6))
    
    doc.build(story)

def generate_hospital_privileges_pdf(filename: str, provider_data: Dict[str, Any]):
    """Generate a hospital privileges PDF document"""
    doc = SimpleDocTemplate(filename, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.darkgreen
    )
    
    hospital = random.choice(HOSPITALS)
    story.append(Paragraph(f"HOSPITAL PRIVILEGES - {hospital.upper()}", title_style))
    story.append(Spacer(1, 20))
    
    # Privileges information
    privileges_data = [
        ['Physician Name:', f"Dr. {provider_data['first_name']} {provider_data['last_name']}"],
        ['NPI Number:', provider_data['npi']],
        ['Medical License:', provider_data['license_number']],
        ['Specialty:', provider_data['specialty']],
        ['Hospital:', hospital],
        ['Privilege Level:', random.choice(['Active Staff', 'Associate Staff', 'Consulting Staff'])],
        ['Department:', random.choice(['Internal Medicine', 'Surgery', 'Emergency Medicine', 'Radiology'])],
        ['Granted Date:', (datetime.now() - timedelta(days=random.randint(365, 3650))).strftime('%Y-%m-%d')],
        ['Expiry Date:', (datetime.now() + timedelta(days=random.randint(30, 1095))).strftime('%Y-%m-%d')],
        ['Status:', 'Active']
    ]
    
    privileges_table = Table(privileges_data, colWidths=[2*inch, 3*inch])
    privileges_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('BACKGROUND', (1, 0), (1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(privileges_table)
    story.append(Spacer(1, 30))
    
    # Privileges granted
    story.append(Paragraph("PRIVILEGES GRANTED:", styles['Heading2']))
    privileges_list = [
        "Admit patients to the hospital",
        "Perform procedures within scope of practice",
        "Order diagnostic tests and treatments",
        "Access electronic medical records",
        "Participate in medical staff committees"
    ]
    
    for privilege in privileges_list:
        story.append(Paragraph(f"• {privilege}", styles['Normal']))
        story.append(Spacer(1, 6))
    
    doc.build(story)

def generate_credentialing_application_pdf(filename: str, provider_data: Dict[str, Any]):
    """Generate a credentialing application PDF document"""
    doc = SimpleDocTemplate(filename, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.darkblue
    )
    
    story.append(Paragraph("CREDENTIALING APPLICATION", title_style))
    story.append(Spacer(1, 20))
    
    # Personal information
    story.append(Paragraph("PERSONAL INFORMATION:", styles['Heading2']))
    personal_data = [
        ['Full Name:', f"Dr. {provider_data['first_name']} {provider_data['last_name']}"],
        ['Date of Birth:', f"{random.randint(1950, 1990)}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}"],
        ['SSN (Last 4):', f"***-**-{random.randint(1000, 9999)}"],
        ['Email:', provider_data['email']],
        ['Phone:', provider_data['phone']],
        ['Address:', f"{provider_data['address_line1']}, {provider_data['city']}, {provider_data['state']} {provider_data['zip_code']}"]
    ]
    
    personal_table = Table(personal_data, colWidths=[2*inch, 3*inch])
    personal_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('BACKGROUND', (1, 0), (1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(personal_table)
    story.append(Spacer(1, 20))
    
    # Professional information
    story.append(Paragraph("PROFESSIONAL INFORMATION:", styles['Heading2']))
    professional_data = [
        ['NPI Number:', provider_data['npi']],
        ['Medical License:', provider_data['license_number']],
        ['License State:', provider_data['license_state']],
        ['Specialty:', provider_data['specialty']],
        ['Medical School:', random.choice(['Harvard Medical School', 'Johns Hopkins University', 
                                         'Stanford University', 'Mayo Clinic School of Medicine'])],
        ['Graduation Year:', str(random.randint(1985, 2015))],
        ['Residency Program:', random.choice(['Internal Medicine Residency', 'Surgery Residency', 
                                            'Family Medicine Residency', 'Pediatrics Residency'])],
        ['Board Certification:', random.choice(['Yes - Current', 'Yes - Expired', 'No'])],
        ['Malpractice Insurance:', random.choice(['Yes - Current', 'Yes - Expired', 'No'])],
        ['DEA Registration:', random.choice(['Yes - Current', 'Yes - Expired', 'No'])]
    ]
    
    professional_table = Table(professional_data, colWidths=[2*inch, 3*inch])
    professional_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('BACKGROUND', (1, 0), (1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(professional_table)
    
    doc.build(story)

def generate_demo_pdfs(providers_data: List[Dict[str, Any]], output_dir: str = "demo_documents"):
    """Generate 20 demo PDF documents"""
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # PDF generators
    pdf_generators = [
        ("medical_license", generate_medical_license_pdf),
        ("dea_registration", generate_dea_registration_pdf),
        ("hospital_privileges", generate_hospital_privileges_pdf),
        ("credentialing_application", generate_credentialing_application_pdf)
    ]
    
    generated_files = []
    
    # Generate 20 PDF documents
    for i in range(20):
        # Select random provider and document type
        provider = random.choice(providers_data)
        doc_type, generator_func = random.choice(pdf_generators)
        
        # Generate filename
        filename = f"{doc_type}_{provider['npi']}_{i+1:02d}.pdf"
        filepath = os.path.join(output_dir, filename)
        
        try:
            # Generate PDF
            generator_func(filepath, provider)
            generated_files.append(filepath)
            print(f"Generated: {filename}")
            
        except Exception as e:
            print(f"Failed to generate {filename}: {e}")
    
    return generated_files

def main():
    """Main function to generate demo PDFs"""
    print("Generating 20 demo PDF documents...")
    
    # Load provider data from JSON file
    try:
        with open('demo_providers.json', 'r') as f:
            providers_data = json.load(f)
        print(f"Loaded {len(providers_data)} provider records")
    except FileNotFoundError:
        print("Error: demo_providers.json not found. Please run generate_demo_data.py first.")
        return
    
    # Generate PDFs
    generated_files = generate_demo_pdfs(providers_data[:20])  # Use first 20 providers
    
    print(f"\nSuccessfully generated {len(generated_files)} PDF documents:")
    for filepath in generated_files:
        print(f"  - {filepath}")
    
    print("\nPDF documents include:")
    print("- Medical Licenses")
    print("- DEA Registrations") 
    print("- Hospital Privileges")
    print("- Credentialing Applications")
    print("\nAll documents are saved in the 'demo_documents' directory.")

if __name__ == "__main__":
    import json
    main()
