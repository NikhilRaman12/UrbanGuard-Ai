# UrbanGuard AI stakeholder demo

## What this demo proves

UrbanGuard AI is a municipal decision-support prototype. It helps a sanitation or environmental-health team answer:

> Which locations should we inspect first, why are they prioritized, and can we document the decision for human approval?

It is not an epidemiological diagnosis system and does not claim that a pathogen is present.

## Data provenance

The default presentation data is stored in `backend/data/realistic_scenario.json`.

- It is synthetic training data, designed from plausible Munich municipal conditions.
- It contains no names, addresses, personal identifiers, or private citizen records.
- It must be labelled synthetic during the presentation.
- It is used to demonstrate the workflow reproducibly when live municipal feeds are unavailable.
- The live weather connector uses Open-Meteo public environmental data as an exposure proxy.
- Report-derived signals are triage evidence only and require field verification.

This transparent boundary is a strength: officials can see what is real, what is simulated, and what still requires authorisation.

## Expected scenario ranking

After clicking **LOAD REALISTIC SCENARIO**, the dashboard should rank the locations approximately as follows:

| Priority | Munich area | Approx. PRI | Signal | Recommended review |
| --- | --- | ---: | --- | --- |
| 1 | Neuhausen-Nymphenburg | 79.7 | Prolonged standing water, blocked gully, waste accumulation | Same-day field inspection |
| 2 | Schwabing-Freimann | 68.0 | Drain obstruction and pooled water near pedestrian access | Inspection within 24 hours |
| 3 | Altstadt-Lehel | 36.7 | Pooled water near a public waste point | Monitor and verify |
| 4 | Obergiesing-Fasangarten | 35.8 | Organic-waste overflow | Verify collection/service history |
| 5 | Bogenhausen | 20.7 | Routine water-edge observation | Continue monitoring |

Scores are transparent weighted indicators, not probabilities of infection.

## Five-minute demo script

1. Open the Streamlit dashboard.
2. Explain the problem: municipal teams receive fragmented reports and must decide where limited crews should go first.
3. Show the five ranked reference locations and point out that each score has named contributors.
4. Select **Neuhausen-Nymphenburg** and open the evidence panel.
5. Explain that the highest score is driven by standing water, sewer level, waste, and clog probability.
6. Click **DRAFT REVIEWED DISPATCH**.
7. Show the generated work order with `pending approval` status and protocol references.
8. Explain the safety boundary: the system drafts a recommendation, but an authorised official must approve it.
9. Select **Bogenhausen** to demonstrate that a low-risk area remains in monitoring rather than triggering unnecessary work.
10. Close with the deployment path: connect authorised drainage, waste, inspection, weather, and Open311-style feeds while retaining the same audit and approval controls.

## Stakeholder value

- Operations teams get a ranked inspection queue.
- Supervisors get an explainable reason for each priority.
- Compliance teams get protocol references and an audit trail.
- Public-communication teams get reviewable multilingual advisories.
- Data-protection officers get minimised, purpose-limited telemetry.
- City leadership gets a realistic path from pilot to authorised municipal deployment.

## Claims to avoid

Do not say that UrbanGuard AI detects disease, proves contamination, predicts infection, or replaces inspectors. Say that it prioritizes environmental sanitation signals for human-reviewed field verification.

## Live-data upgrade path

For a genuine pilot, replace or supplement the synthetic scenario with:

1. Authorised Munich drainage and waste-management telemetry.
2. Approved Open311 or municipal reporting feeds.
3. Verified inspection outcomes for calibration and evaluation.
4. A documented retention policy, access control, DPIA, and responsible-use review.
5. Outcome metrics such as inspection prioritization time, response time, false-alert rate, and percentage of recommendations verified in the field.
