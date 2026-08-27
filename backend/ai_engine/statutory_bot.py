"""
Statutory Knowledge Base & Regulatory Advisory Bot Engine for Indian Coal Mines
Covers Coal Mines Regulations (CMR 2017), Mines Act 1952, DGMS Circulars,
CPCB Environmental Standards, and Labour / Contractor Compliance Laws.
"""

import re

STATUTORY_KNOWLEDGE = [
    {
        'category': 'Methane & Gas Safety',
        'keywords': ['methane', 'ch4', 'inflammable gas', 'firedamp', 'gas testing', 'flame safety lamp'],
        'regulation': 'Coal Mines Regulations (CMR 2017) - Regulation 168 & 169',
        'title': 'Precautions against Inflammable Gas & Mandatory Evacuation Limits',
        'summary': 'In any return airway or working face, if CH4 exceeds 0.75%, immediate corrective ventilation is mandatory. If CH4 reaches 1.25%, all electrical power must be immediately disconnected and personnel evacuated (Reg 169). Only DGMS-approved methanometers/safety lamps may be used.'
    },
    {
        'category': 'Spontaneous Combustion & Carbon Monoxide',
        'keywords': ['carbon monoxide', 'co', 'spontaneous heating', 'fire', 'smoke', 'goaf heating', 'graham ratio'],
        'regulation': 'CMR 2017 - Regulation 142 & 144',
        'title': 'Precaution Against Spontaneous Combustion & Underground Fire',
        'summary': 'Every coal seam liable to spontaneous combustion must be laid out in panels isolated by explosion-proof preparatory stoppings. Continuous CO telemetry is required. CO > 10 ppm indicates heating; CO > 25 ppm requires immediate sealing and rescue deployment.'
    },
    {
        'category': 'Roof & Strata Control',
        'keywords': ['roof support', 'strata', 'rock bolt', 'ssr', 'systematic support rules', 'fall of roof', 'side fall'],
        'regulation': 'CMR 2017 - Regulation 123',
        'title': 'Strata Control and Monitoring Plan (SCAMP)',
        'summary': 'Every underground mine manager must formulate a Scientific Strata Control and Monitoring Plan (SCAMP) approved by CIM/DGMS. Resin-grouted roof bolts must achieve minimum 6-tonne load bearing capacity within 30 minutes and 10 tonnes in 24 hours.'
    },
    {
        'category': 'Open-cast Slope Stability',
        'keywords': ['slope', 'overburden', 'bench height', 'dump', 'landslide', 'slope failure', 'radar'],
        'regulation': 'DGMS Technical Circular (Open Cast) No. 02 of 2020',
        'title': 'Slope Management Plan (SMP) for Open Cast Coal Mines',
        'summary': 'Bench height in alluvium/soft ground must not exceed 3 meters or the reach of the excavator boom. Overburden dump slope must not exceed the natural angle of repose (maximum 28° overall slope). Continuous slope stability radar (SSR) is mandatory for pits deeper than 100 meters.'
    },
    {
        'category': 'Environmental Clearances & Air Quality',
        'keywords': ['environment', 'ec', 'cpcb', 'spcb', 'pm10', 'pm2.5', 'dust', 'cto', 'cte', 'topsoil'],
        'regulation': 'MoEF&CC Environmental Clearance Norms & CPCB Air Standards',
        'title': 'Statutory Environmental Baseline & Emission Standards',
        'summary': 'Ambient air quality must adhere to 24-hr PM10 < 100 µg/m³ and PM2.5 < 60 µg/m³. Continuous water sprinkling, mobile mist cannons on haul roads, and CAAQMS (Continuous Ambient Air Quality Monitoring Stations) with live CPCB server uplink are statutory requirements.'
    },
    {
        'category': 'Worker Medical & Vocational Training',
        'keywords': ['form o', 'vtc', 'vocational training', 'medical', 'pme', 'ime', 'pneumoconiosis', 'audiometry'],
        'regulation': 'Mines Rules 1955 (Rule 29B, Form O) & Mines Vocational Training Rules 1966',
        'title': 'Initial/Periodic Medical Examination & VTC Certification',
        'summary': 'Every mine worker must undergo Initial Medical Examination (IME) and Periodic Medical Examination (PME - Form O) every 5 years (every 3 years for workers above 45 years). Mandatory chest X-rays with ILO classification for Coal Workers\' Pneumoconiosis (CWP).'
    },
    {
        'category': 'Contractor Labour Compliance',
        'keywords': ['contractor', 'contract labour', 'pf', 'esi', 'cmpf', 'gate pass', 'form b'],
        'regulation': 'Contract Labour (R&A) Act 1970 & Coal Mines Provident Fund (CMPF) Act',
        'title': 'Statutory Governance for Mining Contractors',
        'summary': 'Contractors must maintain valid Labor Licenses, Form B register of employees, 100% CMPF/EPF registration, issue DGMS-standard PPE (Steel-toe boots, helmets with reflective tape, miner lamps), and ensure 100% VTC safety training before mine entry.'
    }
]

class StatutoryBotEngine:
    """Answers queries regarding Indian Coal Mining statutes and regulations."""

    @classmethod
    def query_statute(cls, user_query: str) -> dict:
        query_lower = user_query.lower()
        best_match = None
        highest_score = 0

        for item in STATUTORY_KNOWLEDGE:
            score = 0
            for kw in item['keywords']:
                if kw in query_lower:
                    score += 2
            # Check title / category
            if item['category'].lower() in query_lower:
                score += 3
            if score > highest_score:
                highest_score = score
                best_match = item

        if best_match and highest_score > 0:
            return {
                'found': True,
                'category': best_match['category'],
                'regulation': best_match['regulation'],
                'title': best_match['title'],
                'summary': best_match['summary'],
                'confidence': min(98.0, 70.0 + (highest_score * 5.0))
            }
        else:
            return {
                'found': False,
                'category': 'General Coal Mines Regulations',
                'regulation': 'Coal Mines Regulations (CMR) 2017 & Mines Act 1952',
                'title': 'Indian Coal Mining Statutory Framework',
                'summary': 'Coal mining operations in India are strictly governed by the Mines Act 1952, Coal Mines Regulations (CMR 2017) enforced by DGMS, and Environmental Clearances under MoEF&CC/CPCB. You may inquire about methane limits, roof support, slope stability, Form O medicals, or contractor compliance.',
                'confidence': 60.0
            }
