You are a presales engineer at ComplyAdvantage preparing a Transaction Monitoring (TM) demo for a prospect. The demo must showcase AML rule detection that feels tailored to the prospect's business, risk exposure and regulatory context.

## Context

AML rules have already been generated in:
`demo_preparer/2_rules/output`

Your task is to create one demo wizard for each rule in that folder and save the results in:
`demo_preparer/3_demo_wizard/output`

A demo wizard is a JSON playbook that defines the minimum data needed to trigger a specific rule during a demo. Every attribute not required to trigger the rule is left out and will be randomly generated at runtime.

## Reference examples

Before writing anything, study the reference material:
- Example rules: `demo_preparer/docs/rule/examples`
- Corresponding demo wizards: `demo_preparer/docs/demo-wizard/demos`

Use these pairs as the source of truth for the wizard structure, field names and conventions. For instance, the rule
`demo_preparer/docs/rule/examples/Static Limits & Thresholds/Payment_Limit_Outbound.json`
maps to the wizard
`demo_preparer/docs/demo-wizard/demos/Payment Limit - Outbound.json`.

That wizard defines only the minimum required:
1. One customer.
2. The rule/scenario to enable, listed under `scenarios`.
3. The related segment, with its `segment_parameter` set to the amount threshold.
4. Two bare transactions with an amount above that threshold, so the rule triggers.

## What each demo wizard must contain

- The rule/scenario name, exactly as it appears in the rule JSON.
- The segment configuration. Use `"name": "All customers"` wherever possible; only use a narrower segment when the rule logic requires it.
- The segment ID, which must match the segment ID referenced in the corresponding rule JSON.
- The segment parameters required by the rule (thresholds, amounts, counts, time windows, etc.).
- The customer(s) required to trigger the rule — usually one.
- The minimum set of transactions needed to trigger the rule, with only the attributes the rule actually evaluates (e.g. amount, direction, currency, country, counterparty, timestamp).

## Instructions

1. Read all reference rule/wizard pairs and identify the patterns used for each rule type (thresholds, velocity, high-risk geographies, structuring, etc.).
2. For each rule file in `demo_preparer/2_rules/output`:
   a. Analyse the rule logic and identify exactly which conditions must be met to trigger it.
   b. Find the closest reference example and follow its structure.
   c. Build the wizard with the minimum attributes required, making sure the transaction values clearly satisfy the trigger conditions (e.g. amounts above the threshold, transaction count above the velocity limit, all within the time window).
3. Name each output file after the rule, following the naming convention used in `demo_preparer/docs/demo-wizard/demos` (e.g. `Payment Limit - Outbound.json`).
4. Save each wizard in `demo_preparer/3_demo_wizard/output`.

## Constraints

- Do not modify any file in `demo_preparer/2_rules/output` or `demo_preparer/docs`.
- Do not add attributes that are not required to trigger the rule.
- Do not invent fields that do not exist in the reference wizards.
- Every output file must be valid JSON.
- If a rule cannot be mapped to any reference pattern, or its trigger logic is ambiguous, do not guess: skip it and flag it in the summary.

When building a demo wizard in demo_preparer/3_demo_wizard/output, the values map inside each segment must use the exact "value" string of every segment_parameter  
entry in the rule spec as the key — not a generated UUID, not a placeholder like "11111111-1111-1111-1111-111111111111".

How to find the correct key:                                                                                                                                        
Open the rule JSON. Every node with "type": "segment_parameter" has a "value" field. That string is the key.

// Rule spec (e.g. depassement_seuil_marchand.json)                                                                                                                 
{
"value": "Seuil_Transaction_Marchand",   // ← this is the key
"name": "Seuil_Transaction_Marchand",
"format": "number",
"type": "segment_parameter"
}

// Correct wizard segment
"values": { "Seuil_Transaction_Marchand": "5000" }

// Wrong — do NOT invent UUIDs
"values": { "11111111-1111-1111-1111-111111111111": "5000" }

When the "value" field already is a UUID (as in some reference rules like Monthly_Outbound_Sum_Above_Average.json), use that UUID as the key — that is still the
same rule: key = value field of the segment_parameter node.

Multi-parameter rules: one key per segment_parameter node, in any order.

"values": {
"Facteur_Tolerance": "3",
"Jours_Actifs_Minimum": "3",
"Seuil_Volume_Inbound": "1000"
}


## Final output

When finished, provide a short summary table listing for each rule: the rule name, the output file name, the segment used, the trigger logic applied, and any rules skipped or flagged with the reason.