import json
import mesh_client as mc

def extract_alert_data(data):

    results = []
    case = data.get('case', {})
    customer = case.get('customer', {})
    case_identifier = case.get('identifier')
    alerts = data.get('alerts', [])
    # aml_types_i = case.get('risk_catalog_risk_types', [{}])[0].get('risk_types', [])
    # aml_types = [d['key'].removeprefix('r_') for d in aml_types_i]

    for alert in alerts:
        for risk in alert.get('risks', []):
            profile_info = risk.get('detail', {}).get('profile', {})
            risk_indicators = risk.get('details', {}).get('detail', {}).get('profile', {}).get('risk_indicators', [])

            sanctions, peps = [], []
            for ri in risk_indicators:
                for s in ri.get('sanction_indicators', {}).get('values', []):
                    sanctions.append(s.get("source_name"))
                for p in ri.get('pep_indicators', {}).get('values', []):
                    peps.append(p.get("class"))

            results.append({
                'case_identifier': case_identifier,
                'customer_identifier': customer.get('external_identifier', []),
                'customer_name': customer.get('name', []),
                'profile_identifier': profile_info.get('identifier'),
                'profile_matching_name': risk.get('details', {}).get('detail', {}).get('profile', {}).get('match_details', {}).get('match_name', {}).get('name', ''),
                'profile_dob': json.dumps(profile_info.get('person', {}).get('dates_of_birth', {})),
                'profile_match_score': profile_info.get('match_score'),
                'profile_risk': risk.get('details', {}).get('detail', {}).get('profile', {}).get('risk_types', []),
                # 'case_aml_types': aml_types,
                'sanctions': json.dumps(sanctions),
                'peps': json.dumps(peps),
                'mesh_url': 'https://mesh.complyadvantage.com/cases/' + case_identifier,
            })
    return results


if __name__ == "__main__":
    mc.run_main(extract_alert_data, f"nextgen_{mc.search_key}.xlsx")
