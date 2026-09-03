"""
Predictive Risk & Anomaly Analytics Engine for Coal Mine Operations
Analyzes environmental telemetry, historical violation frequencies, and operational parameters
to detect hazards, predict safety breaches, and compute zone risk scores.
"""

import math
from datetime import datetime, timedelta

# Statutory Thresholds under Coal Mines Regulations (CMR 2017) and CPCB Standards
STATUTORY_THRESHOLDS = {
    'ch4_methane': {
        'normal_max': 0.5,      # % in general body of air
        'warning_max': 0.75,    # % threshold for alarming / return airway alert
        'danger_max': 1.25,     # % DGMS mandatory power cut & evacuation (CMR 2017 Reg 169)
        'unit': '%'
    },
    'co_carbon_monoxide': {
        'normal_max': 10.0,     # ppm baseline in coal seam
        'warning_max': 25.0,    # ppm warning for spontaneous combustion/heating
        'danger_max': 50.0,     # ppm critical emergency threshold
        'unit': 'ppm'
    },
    'dust_pm10': {
        'normal_max': 100.0,    # µg/m³ 24-hr standard (CPCB/MoEFCC)
        'warning_max': 250.0,   # µg/m³ active face warning
        'danger_max': 500.0,    # µg/m³ acute respirable coal dust danger
        'unit': 'µg/m³'
    },
    'dust_pm25': {
        'normal_max': 60.0,     # µg/m³
        'warning_max': 120.0,
        'danger_max': 250.0,
        'unit': 'µg/m³'
    },
    'airflow_cfm': {
        'normal_min': 50000.0,  # Minimum CFM required for active ventilation district
        'warning_min': 35000.0,
        'danger_min': 20000.0,
        'unit': 'CFM'
    },
    'slope_displacement': {
        'normal_max': 2.0,      # mm/day in open-cast overburden benches
        'warning_max': 6.0,     # mm/day slope stability alarm
        'danger_max': 15.0,     # mm/day impending slope failure / landslide
        'unit': 'mm/day'
    },
    'water_ph': {
        'normal_min': 6.5,
        'normal_max': 8.5,
        'acid_drainage_alert': 5.5, # Acid Mine Drainage (AMD) indicator
        'unit': 'pH'
    }
}


class PredictiveRiskEngine:
    """Calculates risk heatmaps, detects sensor anomalies, and forecasts hazard probabilities."""

    @staticmethod
    def analyze_telemetry_reading(telemetry_data: dict) -> dict:
        """
        Evaluates a real-time sensor packet against statutory limits and historical variance.
        Returns anomaly flags, alert severity, and regulatory references.
        """
        anomalies = []
        overall_severity = 'Normal'
        risk_score = 10.0 # baseline normal

        # 1. Methane (CH4) Check
        ch4 = float(telemetry_data.get('ch4_percent', 0.0) or 0.0)
        if ch4 >= STATUTORY_THRESHOLDS['ch4_methane']['danger_max']:
            anomalies.append({
                'parameter': 'CH4 (Methane Gas)',
                'value': ch4,
                'threshold': STATUTORY_THRESHOLDS['ch4_methane']['danger_max'],
                'unit': '%',
                'severity': 'Critical',
                'regulation': 'CMR 2017 Reg 169 - Mandatory Evacuation & Power Interruption',
                'recommendation': 'Cut off electrical power immediately; evacuate personnel from return airways and face.'
            })
            overall_severity = 'Critical'
            risk_score = max(risk_score, 95.0)
        elif ch4 >= STATUTORY_THRESHOLDS['ch4_methane']['warning_max']:
            anomalies.append({
                'parameter': 'CH4 (Methane Gas)',
                'value': ch4,
                'threshold': STATUTORY_THRESHOLDS['ch4_methane']['warning_max'],
                'unit': '%',
                'severity': 'Warning',
                'regulation': 'CMR 2017 Reg 168 - Inflammable Gas Precautions',
                'recommendation': 'Increase ventilation aux fans; monitor flame safety lamp/methanometer continuously.'
            })
            if overall_severity != 'Critical':
                overall_severity = 'Warning'
            risk_score = max(risk_score, 70.0)

        # 2. Carbon Monoxide (CO) Check
        co = float(telemetry_data.get('co_ppm', 0.0) or 0.0)
        if co >= STATUTORY_THRESHOLDS['co_carbon_monoxide']['danger_max']:
            anomalies.append({
                'parameter': 'CO (Carbon Monoxide)',
                'value': co,
                'threshold': STATUTORY_THRESHOLDS['co_carbon_monoxide']['danger_max'],
                'unit': 'ppm',
                'severity': 'Critical',
                'regulation': 'CMR 2017 Reg 144 - Spontaneous Heating & Toxic Gas Defense',
                'recommendation': 'Spontaneous combustion detected. Activate mine rescue team and seal off suspected goaf.'
            })
            overall_severity = 'Critical'
            risk_score = max(risk_score, 90.0)
        elif co >= STATUTORY_THRESHOLDS['co_carbon_monoxide']['warning_max']:
            anomalies.append({
                'parameter': 'CO (Carbon Monoxide)',
                'value': co,
                'threshold': STATUTORY_THRESHOLDS['co_carbon_monoxide']['warning_max'],
                'unit': 'ppm',
                'severity': 'Warning',
                'regulation': 'CMR 2017 Reg 142 - Precaution against Heating',
                'recommendation': 'Sample return air for Graham\'s Ratio; inspect isolation stoppings.'
            })
            if overall_severity != 'Critical':
                overall_severity = 'Warning'
            risk_score = max(risk_score, 65.0)

        # 3. Coal Dust (PM10) Check
        pm10 = float(telemetry_data.get('dust_pm10', 0.0) or 0.0)
        if pm10 >= STATUTORY_THRESHOLDS['dust_pm10']['danger_max']:
            anomalies.append({
                'parameter': 'Respirable Dust (PM10)',
                'value': pm10,
                'threshold': STATUTORY_THRESHOLDS['dust_pm10']['danger_max'],
                'unit': 'µg/m³',
                'severity': 'Critical',
                'regulation': 'CMR 2017 Reg 143 - Coal Dust Explosion & Pneumoconiosis Prevention',
                'recommendation': 'Engage water mist atomizers and stone dust barriers immediately.'
            })
            if overall_severity != 'Critical':
                overall_severity = 'High'
            risk_score = max(risk_score, 80.0)
        elif pm10 >= STATUTORY_THRESHOLDS['dust_pm10']['warning_max']:
            anomalies.append({
                'parameter': 'Respirable Dust (PM10)',
                'value': pm10,
                'threshold': STATUTORY_THRESHOLDS['dust_pm10']['warning_max'],
                'unit': 'µg/m³',
                'severity': 'Warning',
                'regulation': 'CPCB National Ambient Air Quality Standards',
                'recommendation': 'Operate water sprinkling on haul roads and transfer chutes.'
            })
            if overall_severity == 'Normal':
                overall_severity = 'Warning'
            risk_score = max(risk_score, 50.0)

        # 4. Slope Displacement (Open Cast Slope Radar)
        disp = float(telemetry_data.get('slope_displacement_mm', 0.0) or 0.0)
        if disp >= STATUTORY_THRESHOLDS['slope_displacement']['danger_max']:
            anomalies.append({
                'parameter': 'Overburden Slope Displacement',
                'value': disp,
                'threshold': STATUTORY_THRESHOLDS['slope_displacement']['danger_max'],
                'unit': 'mm/day',
                'severity': 'Critical',
                'regulation': 'DGMS Circular on Open-cast Slope Stability Management Plan (SMP)',
                'recommendation': 'Immediate bench slide imminent. Evacuate HEMM dumpers and shovels from pit floor.'
            })
            overall_severity = 'Critical'
            risk_score = max(risk_score, 98.0)
        elif disp >= STATUTORY_THRESHOLDS['slope_displacement']['warning_max']:
            anomalies.append({
                'parameter': 'Overburden Slope Displacement',
                'value': disp,
                'threshold': STATUTORY_THRESHOLDS['slope_displacement']['warning_max'],
                'unit': 'mm/day',
                'severity': 'Warning',
                'regulation': 'DGMS SMP Bench Monitoring Guidelines',
                'recommendation': 'Increase piezometer and radar monitoring frequency; reduce crest surcharge load.'
            })
            if overall_severity != 'Critical':
                overall_severity = 'Warning'
            risk_score = max(risk_score, 60.0)

        return {
            'has_anomalies': len(anomalies) > 0,
            'anomalies_count': len(anomalies),
            'anomalies': anomalies,
            'overall_severity': overall_severity,
            'calculated_risk_score': round(risk_score, 1),
            'timestamp': datetime.now().isoformat()
        }

    @staticmethod
    def calculate_mine_compliance_index(active_compliances: list, open_violations: list, overdue_capas: list) -> dict:
        """
        Computes a composite 0-100 Statutory Compliance & Safety Index for a Mine/Colliery.
        Weights:
        - Statutory Audit Compliance: 40%
        - Field Inspection Violations: 35%
        - CAPA Closure Track Record: 25%
        """
        total_statutory = len(active_compliances) or 1
        compliant_statutory = sum(1 for c in active_compliances if c.get('status') == 'Compliant')
        statutory_score = (compliant_statutory / total_statutory) * 100.0

        # Violations penalty
        critical_violations = sum(1 for v in open_violations if v.get('risk_level') == 'Critical')
        high_violations = sum(1 for v in open_violations if v.get('risk_level') == 'High')
        med_violations = sum(1 for v in open_violations if v.get('risk_level') == 'Medium')
        
        violation_penalty = (critical_violations * 20.0) + (high_violations * 10.0) + (med_violations * 4.0)
        inspection_score = max(0.0, 100.0 - violation_penalty)

        # CAPA score
        total_capas = len(overdue_capas) + sum(1 for c in active_compliances if c.get('has_capa')) or 1
        overdue_count = len(overdue_capas)
        capa_score = max(0.0, 100.0 - (overdue_count * 15.0))

        composite_index = (statutory_score * 0.40) + (inspection_score * 0.35) + (capa_score * 0.25)
        composite_index = round(max(0.0, min(100.0, composite_index)), 1)

        rating_tier = 'A+ (Exemplary)'
        color = 'success'
        if composite_index < 50:
            rating_tier = 'D (High Statutory Risk - DGMS Audit Triggered)'
            color = 'danger'
        elif composite_index < 70:
            rating_tier = 'C (Substandard - Corrective Actions Required)'
            color = 'warning'
        elif composite_index < 85:
            rating_tier = 'B (Satisfactory Compliance)'
            color = 'info'

        return {
            'composite_index': composite_index,
            'rating_tier': rating_tier,
            'color': color,
            'statutory_score': round(statutory_score, 1),
            'inspection_score': round(inspection_score, 1),
            'capa_score': round(capa_score, 1),
            'critical_violations': critical_violations,
            'overdue_capas': overdue_count
        }

    @staticmethod
    def predict_recurring_violations(violations_history: list) -> list:
        """
        Identifies recurring compliance failure patterns across shifts, seams, and contractors.
        """
        category_counts = {}
        location_counts = {}
        shift_counts = {}

        for v in violations_history:
            cat = v.get('category') or v.get('violation_type') or 'General'
            loc = v.get('location') or v.get('pit_seam') or 'Unspecified'
            shift = v.get('shift') or 'General'

            category_counts[cat] = category_counts.get(cat, 0) + 1
            location_counts[loc] = location_counts.get(loc, 0) + 1
            shift_counts[shift] = shift_counts.get(shift, 0) + 1

        patterns = []
        for cat, count in category_counts.items():
            if count >= 3:
                patterns.append({
                    'type': 'Category Recurrence',
                    'identifier': cat,
                    'count': count,
                    'risk': 'High',
                    'recommendation': f"High recurring frequency of '{cat}'. Initiate specialized refresher VTC module and equipment audit."
                })

        for loc, count in location_counts.items():
            if count >= 3:
                patterns.append({
                    'type': 'Hotspot Zone',
                    'identifier': loc,
                    'count': count,
                    'risk': 'Critical',
                    'recommendation': f"Section '{loc}' has registered {count} violations. Deploy dedicated Safety Officer and continuous gas telemetry."
                })

        return patterns
