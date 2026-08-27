
# --------------------
# AI Classification & Priority Engine Model
# --------------------

Assuming a 'complaints_history' table exists (or using the current 'complaints' table), 
we can simulate a learning engine that adjusts keyword weights, but for this rule-based system,
we will implement an "Escalation Logic" based on repeated complaints.

LOGIC:
1. If a similar complaint (same category, same user, or same location) exists within the last 7 days and is still 'Pending', ESCALATE PRIORITY.
2. If "General" issues are detected with no strong keywords, default to Low.
