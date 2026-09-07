"""
Public Noticeboard & Statutory Circulars Module:
- /noticeboard (renders noticeboard.html)
"""

from flask import render_template
from . import complaints_bp

@complaints_bp.route('/noticeboard')
def noticeboard():
    """Noticeboard & Acknowledgements page with government circulars, tenders, and public notices."""
    notices = [
        {
            'id': 'NB-2026-001',
            'badge': 'Circular',
            'badge_color': 'danger',
            'category': 'Circulars & Orders',
            'department': 'Ministry of Coal',
            'year': '2026',
            'is_new': True,
            'icon': 'bi-megaphone-fill',
            'date': '05 Sep 2026',
            'due_date': '15 Sep 2026',
            'file_size': '245 KB',
            'file_name': 'Circular_Office_Timings_National_Holidays.pdf',
            'title': 'Circular regarding office timings for national holidays',
            'body': 'Official circular regarding revised administrative office timings, holiday operational rotas, and emergency monitoring shifts across all colliery establishments and regional offices.',
            'reference': 'MoC/CIR/2026/045',
            'status': 'Active'
        },
        {
            'id': 'NB-2026-002',
            'badge': 'Tender',
            'badge_color': 'primary',
            'category': 'Tenders & Bids',
            'department': 'Coal India Limited',
            'year': '2026',
            'is_new': False,
            'icon': 'bi-building-gear',
            'date': '28 Aug 2026',
            'due_date': '30 Sep 2026',
            'file_size': '1.2 MB',
            'file_name': 'Tender_Public_Infrastructure_Project.pdf',
            'title': 'Invitation of bids for public infrastructure project',
            'body': 'Invitation of sealed competitive tenders and bids for mine infrastructure modernization, safety barrier constructions, and smart environmental monitoring retrofitting.',
            'reference': 'CIL/PROJ/INFRA/2026/088',
            'status': 'Active'
        },
        {
            'id': 'NB-2026-003',
            'badge': 'DGMS Directive',
            'badge_color': 'warning',
            'category': 'Safety & Strata',
            'department': 'DGMS',
            'year': '2026',
            'is_new': False,
            'icon': 'bi-exclamation-triangle-fill',
            'date': '10 Aug 2026',
            'due_date': '31 Aug 2026',
            'file_size': '580 KB',
            'file_name': 'DGMS_CMR144_CO_Monitoring.pdf',
            'title': 'CMR 2017 Reg 144: Mandatory Continuous CO & Spontaneous Heating Monitoring',
            'body': 'All colliery managers are directed to ensure daily tube bundle gas chromatography and handheld sensor scanning across all underground Degree-II and Degree-III seams in compliance with Coal Mines Regulation 2017, Regulation 144.',
            'reference': 'DGMS/CMR/2026/144',
            'status': 'Active'
        },
        {
            'id': 'NB-2026-004',
            'badge': 'Statutory Notice',
            'badge_color': 'info',
            'category': 'Labour & Welfare',
            'department': 'DGMS',
            'year': '2026',
            'is_new': False,
            'icon': 'bi-person-badge-fill',
            'date': '10 Jul 2026',
            'due_date': '20 Jul 2026',
            'file_size': '380 KB',
            'file_name': 'DGMS_MinesRules_FormO_Screening.pdf',
            'title': 'Mines Rules 1955: 100% Form O PME Health Screenings for Contract Workers',
            'body': 'Ensure all contractual overburden truck operators, drillers and blasters complete triennial periodic medical examinations (Form O) and Vocational Safety Training (VTC) before deployment on active mining faces.',
            'reference': 'DGMSLab/MR1955/PME/2026',
            'status': 'Active'
        },
        {
            'id': 'NB-2025-014',
            'badge': 'Strata Control',
            'badge_color': 'secondary',
            'category': 'Safety & Strata',
            'department': 'DGMS',
            'year': '2025',
            'is_new': False,
            'icon': 'bi-shield-fill-check',
            'date': '28 Nov 2025',
            'due_date': '31 Dec 2025',
            'file_size': '650 KB',
            'file_name': 'DGMS_SCAMP_Strata_Directive.pdf',
            'title': 'Implementation of SCAMP Strata Support Plan across all Underground Seams',
            'body': 'All mine managers are directed to submit updated Strata Control Action and Management Plans (SCAMP) for each active underground face within 30 days. Non-compliance will attract action under Section 22 of the Mines Act 1952.',
            'reference': 'DGMS/SCAMP/2025/022',
            'status': 'Acknowledged'
        },
        {
            'id': 'NB-2025-009',
            'badge': 'Digital India',
            'badge_color': 'dark',
            'category': 'IT & Governance',
            'department': 'Ministry of Coal',
            'year': '2025',
            'is_new': False,
            'icon': 'bi-pc-display-horizontal',
            'date': '05 Sep 2025',
            'due_date': '30 Nov 2025',
            'file_size': '1.5 MB',
            'file_name': 'MoC_MineGuard_Portal_Gazette.pdf',
            'title': 'MineGuard Portal Launched — Digital Complaint & Compliance Management System',
            'body': 'The Ministry of Coal, in association with DGMS and NIC, has officially launched the MineGuard AI-enabled compliance and complaint management portal. All subsidiaries of Coal India Limited are required to onboard by Q4 2025.',
            'reference': 'MoC/DIG/MineGuard/2025',
            'status': 'Acknowledged'
        },
    ]
    acknowledgements = [
        {
            'icon': 'bi-flag-fill',
            'color': 'text-saffron',
            'title': 'Government of India',
            'body': 'Ministry of Coal & Directorate General of Mines Safety (DGMS)'
        },
        {
            'icon': 'bi-pc-display-horizontal',
            'color': 'text-primary',
            'title': 'National Informatics Centre (NIC)',
            'body': 'Platform design, cloud hosting & Digital India integration'
        },
        {
            'icon': 'bi-tree',
            'color': 'text-success',
            'title': 'MoEF&CC',
            'body': 'Ministry of Environment, Forest and Climate Change — Environmental Compliance Framework'
        },
        {
            'icon': 'bi-people-fill',
            'color': 'text-warning',
            'title': 'Coal India Limited (CIL) & Subsidiaries',
            'body': 'SECL, CCL, WCL, ECL, NCL, BCCL, MCL, NEC — Field operations and compliance data'
        },
    ]
    return render_template('noticeboard.html', notices=notices, acknowledgements=acknowledgements)
