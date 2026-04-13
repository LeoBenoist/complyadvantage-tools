import os
import json
import mesh_client as mc

MATCH_THRESHOLD = int(os.getenv("MATCH_THRESHOLD", "90"))

def extract_alert_data(data):
    print(data)

    results = []
    case = data.get('case', {})
    customer = case.get('customer', {})
    case_identifier = case.get('identifier')
    alerts = data.get('alerts', [])
    # aml_types_i = case.get('risk_catalog_risk_types', [{}])[0].get('risk_types', [])
    # aml_types = [d['key'].removeprefix('r_') for d in aml_types_i]

    # Aggregated at case level — all alerts merged into one row
    all_sanctions, all_watchlists, all_peps = [], [], []
    all_profile_identifiers, all_profile_names, all_profile_scores, all_profile_risks = [], [], [], []

    for alert in alerts:
        for risk in alert.get('risks', []):
            profile_info = risk.get('detail', {}).get('profile', {})
            match_score = round(profile_info.get('match_score'), 2) * 100

            if match_score is None or match_score < MATCH_THRESHOLD:
                continue

            risk_indicators = risk.get('details', {}).get('detail', {}).get('profile', {}).get('risk_indicators', [])

            for ri in risk_indicators:
                for s in ri.get('sanction_indicators', {}).get('values', []):
                    all_sanctions.append(s.get("source_name"))
                for w in ri.get('watchlist_indicators', {}).get('values', []):
                    all_watchlists.append(w.get("source_name"))
                for p in ri.get('pep_indicators', {}).get('values', []):
                    all_peps.append(p.get("class"))

            all_profile_identifiers.append(profile_info.get('identifier'))
            all_profile_names.append(risk.get('details', {}).get('detail', {}).get('profile', {}).get('match_details', {}).get('match_name', {}).get('name', ''))
            all_profile_scores.append(int(match_score))
            all_profile_risks.extend(risk.get('details', {}).get('detail', {}).get('profile', {}).get('risk_types', []))

    if all_profile_identifiers:
        results.append({
            'case_identifier': case_identifier,
            'customer_identifier': customer.get('external_identifier', []),
            'customer_name': customer.get('name', []),
            'profile_identifier': json.dumps(all_profile_identifiers),
            'profile_matching_name': json.dumps(list(dict.fromkeys(all_profile_names))),
            'profile_match_score': json.dumps(list(dict.fromkeys(all_profile_scores))),
            'profile_risk': list(dict.fromkeys(all_profile_risks)),
            # 'case_aml_types': aml_types,
            'sanctions': json.dumps(all_sanctions),
            'watchlists': json.dumps(all_watchlists),
            'peps': json.dumps(all_peps),
            'mesh_url': 'https://mesh.complyadvantage.com/cases/' + case_identifier,
        })
    return results


if __name__ == "__main__":
    mc.run_main(extract_alert_data, f"nextgen_meged_{mc.search_key}_{MATCH_THRESHOLD}.xlsx")
