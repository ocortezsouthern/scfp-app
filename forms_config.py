"""
Data-driven definitions for every inspection type SCFP uses.

Each inspection type is described declaratively (sections -> fields) so that:
  - the HTML entry form is rendered generically (templates/inspection_form.html)
  - the read-only detail view is rendered generically (templates/inspection_detail.html)
  - the PDF report is generated generically (pdf_gen.py)

Field "type" values:
  text, textarea, number, date, select, yn, ynna, checkbox, table

A "table" field renders as a spreadsheet-like grid the inspector can add/remove
rows to. "columns" defines each column; "default_rows" (optional) pre-fills the
first column values (e.g. a fixed inventory checklist).

`frequency_months` drives automatic due-date scheduling: when an inspection of
this type is marked complete, the next due date for that site/asset is set to
inspection_date + frequency_months.

`asset_scope` says whether this inspection is normally tied to a specific
piece of equipment (an Asset row) or just to the Site as a whole.
"""

YN_OPTIONS = ["Yes", "No"]
YNNA_OPTIONS = ["Yes", "No", "N/A"]
PF_OPTIONS = ["Pass", "Fail"]
PFNA_OPTIONS = ["Pass", "Fail", "N/A"]

CLOSING_SECTION = {
    "name": "System Status & Sign-Off",
    "fields": [
        {"key": "overall_result", "label": "Overall Result", "type": "select",
         "options": ["Pass", "Fail", "Incomplete"]},
        {"key": "system_impaired", "label": "Is the system impaired?", "type": "yn"},
        {"key": "critical_deficiencies", "label": "Does the system have critical deficiencies?", "type": "yn"},
        {"key": "non_critical_deficiencies", "label": "Does the system have non-critical deficiencies?", "type": "yn"},
        {"key": "comments", "label": "Comments / Additional Observations", "type": "textarea"},
        {"key": "materials_used", "label": "Additional Materials / Parts Used", "type": "textarea"},
        {"key": "incomplete_reason", "label": "Incomplete Service Reason", "type": "select",
         "options": ["", "Maintained by", "Declined by", "System not present", "Other"]},
        {"key": "satisfactory", "label": "Was the inspection completed in a satisfactory manner?", "type": "yn"},
        {"key": "manager_name", "label": "Manager's Name", "type": "text"},
        {"key": "manager_initials", "label": "Manager's Initials", "type": "text"},
        {"key": "manager_signature_date", "label": "Manager Sign-off Date", "type": "date"},
    ],
}

GENERIC_CHECKLIST_TABLE = {
    "key": "checklist", "label": "Inspection Checklist", "type": "table",
    "columns": [
        {"key": "item", "label": "Item", "type": "text"},
        {"key": "result", "label": "Y / N / N/A", "type": "select", "options": ["", "Y", "N", "N/A"]},
        {"key": "note", "label": "Note", "type": "text"},
    ],
}

INSPECTION_TYPES = {

    "backflow": {
        "label": "Backflow Prevention Assembly Inspection",
        "frequency_months": 12,
        "asset_scope": "backflow",
        "sections": [
            {"name": "Assembly Details", "fields": [
                {"key": "water_purveyor", "label": "Water Purveyor", "type": "text"},
                {"key": "water_meter_number", "label": "Water Meter Number", "type": "text"},
                {"key": "manufacturer", "label": "Manufacturer", "type": "text"},
                {"key": "diameter", "label": "Diameter", "type": "text"},
                {"key": "model_number", "label": "Model Number", "type": "text"},
                {"key": "serial_number", "label": "Serial Number", "type": "text"},
                {"key": "physical_location", "label": "Physical Location", "type": "text"},
                {"key": "confined_space_entry", "label": "Confined Space Entry Required?", "type": "yn"},
                {"key": "new_installation", "label": "Is this a new installation?", "type": "yn"},
                {"key": "permit_number", "label": "Permit Number (if new)", "type": "text"},
                {"key": "replaces_another", "label": "Does this replace another assembly?", "type": "yn"},
                {"key": "old_serial_number", "label": "Old Serial Number (if replacing)", "type": "text"},
                {"key": "position", "label": "Position", "type": "select", "options": ["Primary", "Bypass"]},
                {"key": "service_type", "label": "Service Type", "type": "select",
                 "options": ["Domestic", "Irrigation", "Fireline"]},
                {"key": "assembly_type", "label": "Assembly Type", "type": "select",
                 "options": ["DCVA", "DCDA", "RPBA", "RPDA", "AVB", "PVB", "Other"]},
            ]},
            {"name": "Initial Test", "fields": [
                {"key": "init_cv1_result", "label": "Check Valve #1", "type": "select", "options": ["Closed Tight", "Leaked"]},
                {"key": "init_cv1_rp_psid", "label": "Check Valve #1 RP PSID", "type": "number"},
                {"key": "init_cv1_dc_psid", "label": "Check Valve #1 DC PSID", "type": "number"},
                {"key": "init_cv2_result", "label": "Check Valve #2", "type": "select", "options": ["Closed Tight", "Leaked"]},
                {"key": "init_cv2_dc_psid", "label": "Check Valve #2 DC PSID", "type": "number"},
                {"key": "init_relief_result", "label": "Differential Pressure Relief Valve", "type": "select",
                 "options": ["Opened", "Did Not Open"]},
                {"key": "init_relief_opened_at", "label": "Relief Valve Opened At (PSID)", "type": "number"},
                {"key": "init_backpressure_result", "label": "Back Pressure / PVB", "type": "select",
                 "options": ["Air Inlet Opened", "Did Not Open", "Leaked"]},
                {"key": "init_air_inlet_psid", "label": "Air Inlet PSID", "type": "number"},
                {"key": "init_check_valve_psid", "label": "Check Valve Held PSID", "type": "number"},
                {"key": "initial_test_result", "label": "Initial Test Result", "type": "select", "options": PF_OPTIONS},
            ]},
            {"name": "Repairs", "fields": [
                {"key": "repair_cv1", "label": "Check Valve #1 Repair", "type": "select",
                 "options": ["", "Cleaned", "Rubber Kit", "Other"]},
                {"key": "repair_cv1_note", "label": "Check Valve #1 Repair Notes", "type": "text"},
                {"key": "repair_cv2", "label": "Check Valve #2 Repair", "type": "select",
                 "options": ["", "Cleaned", "Rubber Kit", "Other"]},
                {"key": "repair_cv2_note", "label": "Check Valve #2 Repair Notes", "type": "text"},
                {"key": "repair_relief", "label": "Diff. Pressure Relief Repair", "type": "select",
                 "options": ["", "Cleaned", "Rubber Kit", "Other"]},
                {"key": "repair_relief_note", "label": "Diff. Pressure Relief Repair Notes", "type": "text"},
                {"key": "repair_backpressure", "label": "Back Pressure / PVB Repair", "type": "select",
                 "options": ["", "Cleaned", "Rubber Kit", "Other"]},
                {"key": "repair_backpressure_note", "label": "Back Pressure / PVB Repair Notes", "type": "text"},
            ]},
            {"name": "Final Test", "fields": [
                {"key": "final_cv1_result", "label": "Check Valve #1", "type": "select", "options": ["Closed Tight", "Leaked"]},
                {"key": "final_cv1_rp_psid", "label": "Check Valve #1 RP PSID", "type": "number"},
                {"key": "final_cv1_dc_psid", "label": "Check Valve #1 DC PSID", "type": "number"},
                {"key": "final_cv2_result", "label": "Check Valve #2", "type": "select", "options": ["Closed Tight", "Leaked"]},
                {"key": "final_cv2_dc_psid", "label": "Check Valve #2 DC PSID", "type": "number"},
                {"key": "final_relief_opened_at", "label": "Relief Valve Opened At (PSID)", "type": "number"},
                {"key": "final_air_inlet_psid", "label": "Air Inlet PSID", "type": "number"},
                {"key": "final_check_valve_psid", "label": "Check Valve Held PSID", "type": "number"},
                {"key": "final_test_result", "label": "Final Test Result", "type": "select", "options": PF_OPTIONS},
            ]},
            {"name": "Tester & Certification", "fields": [
                {"key": "initial_test_by", "label": "Initial Test By", "type": "text"},
                {"key": "initial_cert_number", "label": "Certified Tester Number", "type": "text"},
                {"key": "initial_test_date", "label": "Initial Test Date", "type": "date"},
                {"key": "repaired_by", "label": "Repaired By", "type": "text"},
                {"key": "repaired_date", "label": "Repaired Date", "type": "date"},
                {"key": "test_kit_serial", "label": "Test Kit Serial Number", "type": "text"},
                {"key": "final_test_by", "label": "Final Test By", "type": "text"},
                {"key": "final_cert_number", "label": "Certified Tester Number", "type": "text"},
                {"key": "final_test_date", "label": "Final Test Date", "type": "date"},
            ]},
        ],
    },

    "sprinkler_wet": {
        "label": "Fire Sprinkler Annual Inspection (Wet Pipe)",
        "frequency_months": 12,
        "asset_scope": "site",
        "sections": [
            {"name": "Wet Systems", "fields": [
                {"key": "wet_systems", "label": "Wet System Risers", "type": "table", "columns": [
                    {"key": "location", "label": "Location", "type": "text"},
                    {"key": "last_inspection", "label": "Last Inspection", "type": "date"},
                    {"key": "last_5yr", "label": "Last 5-Yr Inspection", "type": "date"},
                    {"key": "riser_size", "label": "Riser Size", "type": "text"},
                    {"key": "static_pressure", "label": "Static Pressure", "type": "number"},
                    {"key": "residual_pressure", "label": "Residual Pressure", "type": "number"},
                    {"key": "return_static", "label": "Return Static", "type": "number"},
                ]},
                {"key": "main_drain_operated", "label": "Did the main drain operate as designed / discharge safely?", "type": "ynna"},
                {"key": "pressure_within_guidelines", "label": "Do pressure readings fall within acceptable guidelines?", "type": "ynna"},
            ]},
            {"name": "Sprinkler Alarm Devices", "fields": [
                {"key": "alarm_devices", "label": "Alarm Devices", "type": "table", "columns": [
                    {"key": "device", "label": "Device", "type": "text"},
                    {"key": "qty", "label": "Qty", "type": "number"},
                    {"key": "free_of_damage", "label": "Free of Physical Damage?", "type": "ynna"},
                    {"key": "alarm_timing_ok", "label": "Alarm Activation Within Spec?", "type": "ynna"},
                ], "default_rows": ["Mechanical Water Flow Device", "Water Flow Switch (Vane/Paddle/Pressure)",
                                     "Control Valve Supervisory Switch"]},
            ]},
            {"name": "System Components", "fields": [
                dict(GENERIC_CHECKLIST_TABLE, key="system_components", label="System Components Checklist"),
            ]},
            {"name": "Hose Stations", "fields": [
                {"key": "hose_stations", "label": "Hose Stations", "type": "table", "columns": [
                    {"key": "location", "label": "Location", "type": "text"},
                    {"key": "unobstructed", "label": "Unobstructed/Accessible", "type": "ynna"},
                    {"key": "caps_in_place", "label": "Caps in Place & Undamaged", "type": "ynna"},
                    {"key": "valve_handles", "label": "Valve Handles Present/Undamaged", "type": "ynna"},
                    {"key": "hose_threads", "label": "Hose Threads Undamaged", "type": "ynna"},
                    {"key": "valves_piping_free", "label": "Valves/Piping Free of Leaks & Corrosion", "type": "ynna"},
                    {"key": "hose_removed_inspected", "label": "Hose Removed/Inspected/Reloaded", "type": "ynna"},
                    {"key": "nozzles_present", "label": "Approved Nozzles Present/Gasketed", "type": "ynna"},
                ]},
            ]},
            {"name": "Control Valves", "fields": [
                {"key": "control_valves", "label": "Control Valves", "type": "table", "columns": [
                    {"key": "type", "label": "Type", "type": "text"},
                    {"key": "location", "label": "Location", "type": "text"},
                    {"key": "system_controlled", "label": "System/Area Controlled", "type": "text"},
                    {"key": "correct_position", "label": "In Appropriate Open/Closed Position", "type": "ynna"},
                    {"key": "locked_sealed", "label": "Locked/Sealed/Monitored", "type": "ynna"},
                    {"key": "proper_signage", "label": "Proper Signage", "type": "ynna"},
                    {"key": "returned_normal", "label": "Operated & Returned to Normal", "type": "ynna"},
                    {"key": "free_of_leaks", "label": "Free of External Leaks/Damage", "type": "ynna"},
                ]},
            ]},
            {"name": "Equipment Inventory", "fields": [
                {"key": "inventory", "label": "Service Location Inventory", "type": "table", "columns": [
                    {"key": "component", "label": "Component", "type": "text"},
                    {"key": "make", "label": "Make", "type": "text"},
                    {"key": "model", "label": "Model", "type": "text"},
                    {"key": "size", "label": "Size", "type": "text"},
                    {"key": "total_count", "label": "Total Count", "type": "number"},
                    {"key": "tested_count", "label": "Tested Count", "type": "number"},
                    {"key": "pass_fail", "label": "Pass/Fail", "type": "select", "options": ["", "Pass", "Fail", "N/A"]},
                ], "default_rows": ["Wet Riser", "Antifreeze Loop", "Water Flow Switch", "Tamper Switch",
                                     "Pressure Switch", "Fire Pump", "Hose Rerack", "Standpipe Valve",
                                     "Sectional Control Valve", "MIC Probe Testing", "Backflow (Fireline)"]},
            ]},
        ],
    },

    "sprinkler_dry": {
        "label": "Fire Sprinkler Annual Inspection (Dry Pipe)",
        "frequency_months": 12,
        "asset_scope": "site",
        "sections": [
            {"name": "Dry Systems", "fields": [
                {"key": "dry_systems", "label": "Dry System Risers", "type": "table", "columns": [
                    {"key": "location", "label": "Location", "type": "text"},
                    {"key": "riser_size", "label": "Riser Size", "type": "text"},
                    {"key": "air_pressure", "label": "Air Pressure", "type": "number"},
                    {"key": "priming_water_level", "label": "Priming Water Level", "type": "text"},
                    {"key": "last_inspection", "label": "Last Inspection", "type": "date"},
                ]},
                {"key": "in_service", "label": "Is the dry pipe system in service?", "type": "ynna"},
                {"key": "air_pressure_meets_min", "label": "Do air pressures & priming levels meet minimum requirements?", "type": "ynna"},
                {"key": "aux_drains_opened", "label": "Were auxiliary drains opened during inspection?", "type": "ynna"},
                {"key": "quick_opening_device_operated", "label": "Did quick opening device(s) operate?", "type": "ynna"},
                {"key": "dry_valve_operated_min_std", "label": "Did dry valve operate within minimum standards?", "type": "ynna"},
                {"key": "dry_valve_reset", "label": "Did dry system valve reset?", "type": "ynna"},
            ]},
            {"name": "System Components", "fields": [
                dict(GENERIC_CHECKLIST_TABLE, key="system_components", label="System Components Checklist"),
            ]},
            {"name": "Hose Stations", "fields": [
                {"key": "hose_stations", "label": "Hose Stations", "type": "table", "columns": [
                    {"key": "location", "label": "Location", "type": "text"},
                    {"key": "unobstructed", "label": "Unobstructed/Accessible", "type": "ynna"},
                    {"key": "caps_in_place", "label": "Caps in Place & Undamaged", "type": "ynna"},
                    {"key": "hose_threads", "label": "Hose Threads Undamaged", "type": "ynna"},
                    {"key": "valves_piping_free", "label": "Valves/Piping Free of Leaks & Corrosion", "type": "ynna"},
                    {"key": "nozzles_present", "label": "Approved Nozzles Present/Gasketed", "type": "ynna"},
                ]},
            ]},
            {"name": "Control Valves", "fields": [
                {"key": "control_valves", "label": "Control Valves", "type": "table", "columns": [
                    {"key": "type", "label": "Type", "type": "text"},
                    {"key": "location", "label": "Location", "type": "text"},
                    {"key": "correct_position", "label": "In Appropriate Open/Closed Position", "type": "ynna"},
                    {"key": "locked_sealed", "label": "Locked/Sealed/Monitored", "type": "ynna"},
                    {"key": "returned_normal", "label": "Operated & Returned to Normal", "type": "ynna"},
                ]},
            ]},
            {"name": "Equipment Inventory", "fields": [
                {"key": "inventory", "label": "Service Location Inventory", "type": "table", "columns": [
                    {"key": "component", "label": "Component", "type": "text"},
                    {"key": "make", "label": "Make", "type": "text"},
                    {"key": "model", "label": "Model", "type": "text"},
                    {"key": "size", "label": "Size", "type": "text"},
                    {"key": "total_count", "label": "Total Count", "type": "number"},
                    {"key": "tested_count", "label": "Tested Count", "type": "number"},
                    {"key": "pass_fail", "label": "Pass/Fail", "type": "select", "options": ["", "Pass", "Fail", "N/A"]},
                ], "default_rows": ["Dry Riser", "Waterflow Switch", "Tamper Switch",
                                     "Quick Opening Device", "Low Point Drain", "Air Compressor"]},
            ]},
        ],
    },

    "sprinkler_5yr": {
        "label": "Sprinkler 5-Year Internal Obstruction Investigation",
        "frequency_months": 60,
        "asset_scope": "site",
        "sections": [
            {"name": "Investigation Details", "fields": [
                {"key": "dry_system_coverage_area", "label": "Dry System Coverage Area (if applicable)", "type": "text"},
                {"key": "tag_color_compliance", "label": "Tag Color / Compliance", "type": "text"},
            ]},
            {"name": "5-Year Investigation and Prevention Checklist", "fields": [
                {"key": "investigation_checklist", "label": "Checklist", "type": "table", "columns": [
                    {"key": "item", "label": "Item", "type": "text"},
                    {"key": "result", "label": "Y / N/A / N", "type": "select", "options": ["", "Y", "N/A", "N"]},
                ], "default_rows": [
                    "System in service before conducting investigation",
                    "Pertinent parties notified before conducting investigation",
                    "Adequate drainage ensured before draining system",
                    "System impairment program implemented before conducting investigation",
                    "Flushing connection of one main and sprinkler of one branch line removed",
                    "Alternative non-destructive examination method utilized",
                    "No foreign material indicated by non-destructive examination method",
                    "Interior of main, branch line and sprinkler outlet checked for foreign material",
                    "No significant foreign material observed",
                    "Interior checked for presence of tubercles or slime",
                    "No tubercles or slime observed",
                    "Parties notified of inspection completion",
                    "Alarm panel clear",
                    "System returned to service",
                ]},
            ]},
            {"name": "System Inventory", "fields": [
                {"key": "inventory", "label": "Inventory", "type": "table", "columns": [
                    {"key": "component", "label": "Component", "type": "text"},
                    {"key": "total_count", "label": "Total Count", "type": "number"},
                    {"key": "tested_count", "label": "Tested Count", "type": "number"},
                    {"key": "system", "label": "System #", "type": "text"},
                    {"key": "tag_color_compliance", "label": "Tag Color/Compliance", "type": "text"},
                ], "default_rows": ["Wet/Dry Riser(s)", "Waterflow Switch", "Tamper Switch (Supervisory)"]},
            ]},
            {"name": "Sign-Off", "fields": [
                {"key": "inspector_initial", "label": "Inspector's Initial", "type": "text"},
                {"key": "owner_rep_initial", "label": "Owner/Designated Rep. Initial", "type": "text"},
            ]},
        ],
    },

    "dry_riser_full_trip": {
        "label": "Annual Dry Riser Full Trip Test",
        "frequency_months": 12,
        "asset_scope": "site",
        "sections": [
            {"name": "Full Dry Trip Test", "fields": [
                {"key": "trip_results", "label": "Trip Results", "type": "table", "columns": [
                    {"key": "system", "label": "Sys #", "type": "text"},
                    {"key": "air_pressure_at_opening", "label": "Air Pressure at Valve Opening", "type": "number"},
                    {"key": "time_to_remote_test_point", "label": "Time to Remote Test Point", "type": "text"},
                    {"key": "air_pressure_priming_ok", "label": "Air Pressure/Priming Meets Min Reqs", "type": "select", "options": PFNA_OPTIONS},
                    {"key": "quick_opening_operated", "label": "Quick Opening Device(s) Operated", "type": "select", "options": PFNA_OPTIONS},
                    {"key": "dry_valve_operated_min_std", "label": "Dry Valve Operated Within Min Standards", "type": "select", "options": PFNA_OPTIONS},
                    {"key": "dry_valve_reset", "label": "Dry System Valve Reset", "type": "select", "options": PF_OPTIONS},
                ]},
            ]},
        ],
    },

    "dry_riser_partial_trip": {
        "label": "Annual Dry Riser Partial Trip Test",
        "frequency_months": 12,
        "asset_scope": "site",
        "sections": [
            {"name": "Partial Dry Trip Test", "fields": [
                {"key": "trip_results", "label": "Trip Results", "type": "table", "columns": [
                    {"key": "system", "label": "Sys #", "type": "text"},
                    {"key": "air_pressure_at_opening", "label": "Air Pressure at Valve Opening", "type": "number"},
                    {"key": "air_pressure_priming_ok", "label": "Air Pressure/Priming Meets Min Reqs", "type": "select", "options": PFNA_OPTIONS},
                    {"key": "quick_opening_operated", "label": "Quick Opening Device(s) Operated", "type": "select", "options": PFNA_OPTIONS},
                    {"key": "dry_valve_operated_min_std", "label": "Dry Valve Operated Within Min Standards", "type": "select", "options": PFNA_OPTIONS},
                    {"key": "dry_valve_reset", "label": "Dry System Valve Reset", "type": "select", "options": PF_OPTIONS},
                ]},
            ]},
        ],
    },

    "fire_alarm": {
        "label": "Fire Alarm Inspection",
        "frequency_months": 12,
        "asset_scope": "site",
        "sections": [
            {"name": "Pre-Test Notifications", "fields": [
                {"key": "notifications", "label": "Notifications", "type": "table", "columns": [
                    {"key": "party", "label": "Notified Party", "type": "text"},
                    {"key": "status", "label": "Y / N / N/A", "type": "select", "options": ["", "Y", "N", "N/A"]},
                    {"key": "time", "label": "Time", "type": "text"},
                    {"key": "person_operator", "label": "Person / Operator #", "type": "text"},
                ], "default_rows": ["Monitoring Company", "Building Occupants", "Municipal Box", "Notifications", "Other"]},
                {"key": "monitoring_company_name", "label": "Monitoring Company Name", "type": "text"},
            ]},
            {"name": "Main Control Panel", "fields": [
                {"key": "panel_manufacturer", "label": "Manufacturer", "type": "text"},
                {"key": "panel_model", "label": "Model #", "type": "text"},
                {"key": "power_on_light", "label": "Green 'power on' light illuminated?", "type": "yn"},
                {"key": "alarm_trouble_clear", "label": "Alarm/trouble lights clear?", "type": "yn"},
                {"key": "panel_labeled", "label": "Panel properly labeled?", "type": "yn"},
                {"key": "notification_devices_active", "label": "Notification devices active (not bypassed)?", "type": "yn"},
                {"key": "auxiliary_functions_active", "label": "Auxiliary functions active (not bypassed)?", "type": "yn"},
                {"key": "exit_signs", "label": "Exit Signs Present / Qty", "type": "text"},
                {"key": "emergency_lights", "label": "Emergency Lights Present / Qty", "type": "text"},
                {"key": "fireman_elevator_recall", "label": "Fireman Elevator Recall?", "type": "yn"},
                {"key": "emergency_escalator_stop", "label": "Emergency Escalator Stop?", "type": "yn"},
            ]},
            {"name": "NAC Power Supply / Panel Measurements", "fields": [
                {"key": "nac_power", "label": "NAC Power Supplies", "type": "table", "columns": [
                    {"key": "number", "label": "#", "type": "text"},
                    {"key": "manufacturer", "label": "Manufacturer", "type": "text"},
                    {"key": "model", "label": "Model #", "type": "text"},
                    {"key": "charger_voltage", "label": "Charger Voltage", "type": "text"},
                    {"key": "battery_voltage", "label": "Battery Voltage", "type": "text"},
                    {"key": "battery_install_date", "label": "Battery Install Date", "type": "date"},
                ]},
            ]},
            {"name": "Device Inventory & Test", "fields": [
                {"key": "devices", "label": "Devices Tested", "type": "table", "columns": [
                    {"key": "device_counts", "label": "Device Type (Qty) e.g. SD:2, PS:1", "type": "text"},
                    {"key": "location", "label": "Device Location", "type": "text"},
                    {"key": "panel_description_accurate", "label": "Panel Description Accurate", "type": "ynna"},
                    {"key": "operated_properly", "label": "Operated Properly", "type": "yn"},
                    {"key": "note", "label": "Note #", "type": "text"},
                ]},
            ]},
            {"name": "Sprinkler System Devices", "fields": [
                {"key": "sprinkler_devices", "label": "Sprinkler System Devices (WF/TS/PS)", "type": "table", "columns": [
                    {"key": "riser", "label": "Riser #", "type": "text"},
                    {"key": "device_type", "label": "Type (WF/TS/PS)", "type": "text"},
                    {"key": "location", "label": "Location", "type": "text"},
                    {"key": "time_to_alarm_sec", "label": "Time to Alarm Activation (sec)", "type": "number"},
                    {"key": "wheel_turns", "label": "Wheel Turns to Supervisory Signal", "type": "text"},
                    {"key": "panel_description_accurate", "label": "Panel Description Accurate", "type": "yn"},
                    {"key": "comment", "label": "Comment", "type": "text"},
                ]},
            ]},
            {"name": "Fire Pump Interface", "fields": [
                {"key": "fire_pump_interface", "label": "Fire Pump Signals", "type": "table", "columns": [
                    {"key": "signal", "label": "Signal", "type": "text"},
                    {"key": "operated_properly", "label": "Operated Properly", "type": "ynna"},
                    {"key": "panel_description_accurate", "label": "Panel Description Accurate", "type": "yn"},
                    {"key": "comment", "label": "Comment", "type": "text"},
                ], "default_rows": ["Pump Run", "Power Fail", "Phase Reversal", "Switch Off Normal", "System Trouble"]},
                {"key": "notification_circuits_operated", "label": "Notification Circuits Operated Properly", "type": "ynna"},
            ]},
            {"name": "Monitoring Company & Masterbox", "fields": [
                {"key": "monitoring_signals", "label": "Monitoring Company Signals", "type": "table", "columns": [
                    {"key": "signal", "label": "Signal", "type": "text"},
                    {"key": "received", "label": "Received", "type": "ynna"},
                    {"key": "time", "label": "Time", "type": "text"},
                    {"key": "operator", "label": "Operator Name/#", "type": "text"},
                ], "default_rows": ["General Alarm", "Supervisory", "Trouble", "All Signals Clear", "Notify Testing Complete"]},
                {"key": "masterbox_signals", "label": "Masterbox Signals", "type": "table", "columns": [
                    {"key": "signal", "label": "Signal", "type": "text"},
                    {"key": "received", "label": "Received", "type": "ynna"},
                    {"key": "time", "label": "Time", "type": "text"},
                    {"key": "operator", "label": "Operator Name/#", "type": "text"},
                ], "default_rows": ["Alarm", "All Clear"]},
                {"key": "panel_condition_normal", "label": "Post-Test Panel Condition Normal", "type": "yn"},
            ]},
            {"name": "Equipment Inventory", "fields": [
                {"key": "inventory", "label": "Service Location Inventory - Alarm", "type": "table", "columns": [
                    {"key": "component", "label": "Component", "type": "text"},
                    {"key": "make", "label": "Make", "type": "text"},
                    {"key": "model", "label": "Model", "type": "text"},
                    {"key": "size", "label": "Size", "type": "text"},
                    {"key": "total_count", "label": "Total Count", "type": "number"},
                    {"key": "tested_count", "label": "Tested Count", "type": "number"},
                    {"key": "pass_fail", "label": "Pass/Fail", "type": "select", "options": ["", "Pass", "Fail", "N/A"]},
                ], "default_rows": [
                    "Fire Alarm Control Panel", "NAC Panel (Booster Panel)", "Air Sampling Detector",
                    "Beam Detector", "CO Detector", "Duct Detector w/o Remote", "Duct Detector w/ Remote",
                    "Heat Detector", "Smoke Detector", "Smoke/Heat Combo", "Pull Station", "Waterflow Switch",
                    "Tamper Switch (Supervisory)", "Pressure Switch", "Low Air Switch", "Audio Devices",
                    "Visual Devices", "Audio/Visual Devices", "Annunciator", "Elevator Recall", "Door Holder",
                    "Nurse Call Pull Cord",
                ]},
            ]},
        ],
    },

    "fire_pump": {
        "label": "Annual Electric Fire Pump Inspection",
        "frequency_months": 12,
        "asset_scope": "fire_pump",
        "sections": [
            {"name": "Fire Pump", "fields": [
                {"key": "manufacturer", "label": "Manufacturer", "type": "text"},
                {"key": "shop_serial", "label": "Shop/Serial #", "type": "text"},
                {"key": "model_type", "label": "Model/Type", "type": "text"},
                {"key": "rated_gpm", "label": "Rated GPM", "type": "number"},
                {"key": "max_churn_psi", "label": "Max Churn PSI", "type": "number"},
                {"key": "rated_psi", "label": "Rated PSI", "type": "number"},
                {"key": "capacity_150pct_psi", "label": "150% PSI Capacity", "type": "number"},
                {"key": "rated_rpm", "label": "Rated RPM", "type": "number"},
                {"key": "pump_configuration", "label": "Configuration", "type": "select",
                 "options": ["Split Case Fire Pump", "Vertical Turbine Fire Pump"]},
                {"key": "alignment_status", "label": "Alignment Status", "type": "select", "options": PF_OPTIONS},
                {"key": "suction_from", "label": "Suction From", "type": "text"},
                {"key": "shaft_orientation", "label": "Shaft Orientation", "type": "select", "options": ["Horizontal", "Vertical"]},
                {"key": "static_ft", "label": "Static (ft)", "type": "number"},
                {"key": "pumping_ft", "label": "Pumping (ft)", "type": "number"},
            ]},
            {"name": "Water Source", "fields": [
                {"key": "tank_dim1", "label": "Tank Dimension 1 (ft)", "type": "number"},
                {"key": "tank_dim2", "label": "Tank Dimension 2 (ft)", "type": "number"},
                {"key": "tank_volume", "label": "Tank Volume", "type": "text"},
                {"key": "current_level_pct", "label": "Current Level (approx % full)", "type": "number"},
            ]},
            {"name": "Electric Driver", "fields": [
                {"key": "driver_manufacturer", "label": "Manufacturer", "type": "text"},
                {"key": "driver_shop_serial", "label": "Shop/Serial #", "type": "text"},
                {"key": "driver_model_type", "label": "Model/Type", "type": "text"},
                {"key": "driver_rated_hp", "label": "Rated HP", "type": "number"},
                {"key": "driver_rated_rpm", "label": "Rated RPM", "type": "number"},
                {"key": "operating_volt", "label": "Operating Volt", "type": "number"},
                {"key": "rated_volt", "label": "Rated Volt", "type": "number"},
                {"key": "rated_fl_amps", "label": "Rated FL Amps", "type": "number"},
                {"key": "amps_at_150pct", "label": "Amps at 150%", "type": "number"},
                {"key": "phase", "label": "Phase", "type": "text"},
                {"key": "cycles", "label": "Cycles", "type": "text"},
            ]},
            {"name": "Controller", "fields": [
                {"key": "controller_manufacturer", "label": "Manufacturer", "type": "text"},
                {"key": "controller_shop_serial", "label": "Shop/Serial #", "type": "text"},
                {"key": "controller_model_type", "label": "Model/Type", "type": "text"},
                {"key": "controller_start_psi", "label": "Start (PSI)", "type": "number"},
                {"key": "controller_start_method", "label": "Start Method", "type": "text"},
                {"key": "jockey_start_method", "label": "Jockey Pump Start Method", "type": "text"},
                {"key": "jockey_start_psi", "label": "Jockey Pump Start (PSI)", "type": "number"},
                {"key": "jockey_off_psi", "label": "Jockey Pump Off (PSI)", "type": "number"},
            ]},
            {"name": "Test Results", "fields": [
                {"key": "test_results", "label": "Test Results", "type": "table", "columns": [
                    {"key": "capacity_pct", "label": "Rated Capacity %", "type": "text"},
                    {"key": "speed_rpm", "label": "Speed RPM", "type": "number"},
                    {"key": "discharge_psi", "label": "Discharge Pressure PSI", "type": "number"},
                    {"key": "suction_psi", "label": "Suction Pressure PSI", "type": "number"},
                    {"key": "net_head_psi", "label": "Net Head PSI", "type": "number"},
                    {"key": "streams_number", "label": "Streams #", "type": "text"},
                    {"key": "streams_size", "label": "Streams Size/Diameter", "type": "text"},
                    {"key": "pitot_pressure", "label": "Pitot Pressure", "type": "number"},
                    {"key": "discharge_volume_gpm", "label": "Discharge Volume GPM", "type": "number"},
                    {"key": "performance", "label": "Performance (Smooth/Rough)", "type": "text"},
                ], "default_rows": ["0%", "50%", "100%", "150%"]},
                {"key": "motor_amps", "label": "Electric Motor Amps", "type": "table", "columns": [
                    {"key": "capacity_pct", "label": "% Rated Capacity", "type": "text"},
                    {"key": "volts", "label": "Volts", "type": "number"},
                    {"key": "amps_lt1", "label": "Amps LT-1", "type": "number"},
                    {"key": "amps_lt2", "label": "Amps LT-2", "type": "number"},
                    {"key": "amps_lt3", "label": "Amps LT-3", "type": "number"},
                ], "default_rows": ["0%", "100%", "150%"]},
            ]},
            {"name": "Equipment Inventory", "fields": [
                {"key": "inventory", "label": "Service Location Inventory - Pumps", "type": "table", "columns": [
                    {"key": "component", "label": "Component", "type": "text"},
                    {"key": "make", "label": "Make", "type": "text"},
                    {"key": "model", "label": "Model", "type": "text"},
                    {"key": "size", "label": "Size", "type": "text"},
                    {"key": "total_count", "label": "Total Count", "type": "number"},
                    {"key": "tested_count", "label": "Tested Count", "type": "number"},
                    {"key": "pass_fail", "label": "Pass/Fail", "type": "select", "options": ["", "Pass", "Fail", "N/A"]},
                ], "default_rows": ["Fire Pump", "Electric Driver", "Fire Pump Controller", "Jockey Pump"]},
            ]},
        ],
    },

    "hydrant": {
        "label": "Hydrant Inspection",
        "frequency_months": 12,
        "asset_scope": "hydrant",
        "sections": [
            {"name": "Service Details", "fields": [
                {"key": "service_order_number", "label": "Service Order #", "type": "text"},
                {"key": "scheduled_with", "label": "Scheduled With", "type": "text"},
                {"key": "license_number", "label": "Vendor/Inspector License #", "type": "text"},
            ]},
            {"name": "Flow Test", "fields": [
                {"key": "flow_test", "label": "Flow / Static Readings", "type": "table", "columns": [
                    {"key": "reading", "label": "Reading", "type": "text"},
                    {"key": "outlet", "label": "Outlet", "type": "text"},
                    {"key": "elev", "label": "Elev", "type": "text"},
                    {"key": "static_psi", "label": "Static PSI", "type": "number"},
                    {"key": "residual_psi", "label": "Residual PSI", "type": "number"},
                    {"key": "pitot_psi", "label": "Pitot PSI", "type": "number"},
                    {"key": "orifice", "label": "Orifice", "type": "text"},
                    {"key": "discharge_coefficient", "label": "Discharge Coefficient", "type": "text"},
                    {"key": "flow_gpm", "label": "Flow GPM", "type": "number"},
                    {"key": "location", "label": "Location", "type": "text"},
                ], "default_rows": ["Flow 1", "Flow 2", "Static"]},
            ]},
            {"name": "Condition Checklist", "fields": [
                {"key": "flushed_60sec", "label": "Flushed for min. 60 seconds or until clear?", "type": "ynna"},
                {"key": "clear_accessible", "label": "Hydrant clear and accessible?", "type": "ynna"},
                {"key": "free_of_leaks_corrosion", "label": "Free from leaks, corrosion or cracks?", "type": "ynna"},
                {"key": "free_of_ice_water", "label": "Free from ice or water in barrel?", "type": "ynna"},
                {"key": "dry_hydrant_drained", "label": "(Dry pipe) drained within 60 min of shutoff?", "type": "ynna"},
                {"key": "caps_in_place", "label": "Were all caps in place on hydrant?", "type": "ynna"},
                {"key": "no_leaks_gasket_caps", "label": "No leaks in gasket under caps when opened?", "type": "ynna"},
                {"key": "threads_good_condition", "label": "Threads in good condition?", "type": "ynna"},
                {"key": "operating_nut_good", "label": "Operating nut in good condition?", "type": "ynna"},
                {"key": "outlets_lubricated", "label": "Are outlets lubricated?", "type": "ynna"},
                {"key": "hose_house_good_condition", "label": "Hose house/equipment in good condition?", "type": "ynna"},
            ]},
            {"name": "Deficiencies & Notes", "fields": [
                {"key": "deficiencies", "label": "Deficiencies", "type": "textarea"},
                {"key": "notes", "label": "Notes", "type": "textarea"},
            ]},
        ],
    },

    "hose_test": {
        "label": "Fire Hose Service Test",
        "frequency_months": 12,
        "asset_scope": "site",
        "sections": [
            {"name": "Test Details", "fields": [
                {"key": "station", "label": "Station", "type": "text"},
                {"key": "apparatus", "label": "Apparatus", "type": "text"},
                {"key": "officer_ff", "label": "Officer/FF", "type": "text"},
            ]},
            {"name": "Hose Log", "fields": [
                {"key": "hose_log", "label": "Hose Test Log", "type": "table", "columns": [
                    {"key": "diameter", "label": "Diameter", "type": "text"},
                    {"key": "hose_number", "label": "Hose #", "type": "text"},
                    {"key": "pressure", "label": "Pressure", "type": "number"},
                    {"key": "pass_fail", "label": "Pass/Fail", "type": "select", "options": ["", "Pass", "Fail"]},
                    {"key": "notes", "label": "Notes", "type": "text"},
                ]},
            ]},
        ],
    },

    "fdc": {
        "label": "Fire Department Connection (FDC) Visual Inspection",
        "frequency_months": 12,
        "asset_scope": "site",
        "sections": [
            {"name": "FDC Inspection", "fields": [
                {"key": "fdc_table", "label": "Fire Department Connections", "type": "table", "columns": [
                    {"key": "location", "label": "Location", "type": "text"},
                    {"key": "visible_accessible", "label": "Visible/Accessible, Signage", "type": "select", "options": PFNA_OPTIONS},
                    {"key": "couplings_free", "label": "Couplings/Swivels Free & Rotate", "type": "select", "options": PFNA_OPTIONS},
                    {"key": "plugs_caps", "label": "Plugs/Caps in Place, Undamaged", "type": "select", "options": PFNA_OPTIONS},
                    {"key": "gaskets", "label": "Gaskets in Place", "type": "select", "options": PFNA_OPTIONS},
                    {"key": "check_valve", "label": "Check Valve Good Condition", "type": "select", "options": PFNA_OPTIONS},
                    {"key": "auto_drain", "label": "Automatic Drain Valve Operates", "type": "select", "options": PFNA_OPTIONS},
                    {"key": "clapper", "label": "Connection Clapper Operates", "type": "select", "options": PFNA_OPTIONS},
                ]},
            ]},
        ],
    },

    "site_walkthrough": {
        "label": "Annual Fire Protection Systems Walkthrough (Comprehensive)",
        "frequency_months": 12,
        "asset_scope": "site",
        "sections": [
            {"name": "Site Overview", "fields": [
                {"key": "jurisdiction", "label": "Jurisdiction", "type": "text"},
                {"key": "division", "label": "Division", "type": "text"},
                {"key": "inspection_start_time", "label": "Inspection Start Time", "type": "text"},
                {"key": "wet_system_present", "label": "Wet sprinkler system present?", "type": "yn"},
                {"key": "dry_system_present", "label": "Dry pipe system present?", "type": "yn"},
                {"key": "fire_pump_present", "label": "Fire pump present?", "type": "yn"},
                {"key": "alarm_panel_present", "label": "Alarm panel present?", "type": "yn"},
                {"key": "monitoring_company", "label": "Monitoring Company", "type": "text"},
                {"key": "backflow_present", "label": "Backflow present at this location?", "type": "yn"},
                {"key": "last_backflow_inspection", "label": "Last Backflow Inspection Date", "type": "date"},
                {"key": "hood_system_present", "label": "Hood extinguishing system present?", "type": "yn"},
                {"key": "last_hood_inspection", "label": "Last Hood Inspection Date", "type": "date"},
                {"key": "extinguishers_last_serviced", "label": "Extinguishers Last Serviced Date", "type": "date"},
                {"key": "extinguisher_contractor", "label": "Extinguisher Service Contractor", "type": "text"},
                {"key": "p1_issue_reported", "label": "Was a P-1 issue reported?", "type": "yn"},
                {"key": "p2_issue_reported", "label": "Was a P-2 issue reported?", "type": "yn"},
            ]},
            {"name": "Water Flow Test of Main Drain", "fields": [
                {"key": "main_drain_test", "label": "Main Drain Test Readings", "type": "table", "columns": [
                    {"key": "test_number", "label": "Test #", "type": "text"},
                    {"key": "pipe_size", "label": "Pipe Size", "type": "text"},
                    {"key": "static", "label": "Static", "type": "number"},
                    {"key": "residual", "label": "Residual", "type": "number"},
                    {"key": "return_static", "label": "Return Static", "type": "number"},
                ]},
            ]},
            {"name": "Dry System Function Test", "fields": [
                {"key": "dry_function_test", "label": "Dry System Function Test", "type": "table", "columns": [
                    {"key": "system", "label": "System #", "type": "text"},
                    {"key": "start_air_pressure", "label": "Start Air Pressure", "type": "number"},
                    {"key": "start_water_pressure", "label": "Start Water Pressure", "type": "number"},
                    {"key": "air_pressure_at_opening", "label": "Air Pressure at Valve Opening", "type": "number"},
                    {"key": "time_to_remote_test_point", "label": "Time to Remote Test Point", "type": "text"},
                ]},
            ]},
            {"name": "General Site Checklist", "fields": [
                dict(GENERIC_CHECKLIST_TABLE, key="site_checklist", label="Site Checklist",
                     default_rows=[
                    "Aisles unobstructed and free of storage",
                    "Fire lanes unobstructed",
                    "Flue spaces unobstructed",
                    "Store manager offered training on panel reset / riser shutoff",
                ]),
            ]},
        ],
    },
}


def get_type_config(inspection_type):
    return INSPECTION_TYPES.get(inspection_type)


def all_types():
    """Returns list of (key, label) tuples for use in dropdowns."""
    return [(k, v["label"]) for k, v in INSPECTION_TYPES.items()]
