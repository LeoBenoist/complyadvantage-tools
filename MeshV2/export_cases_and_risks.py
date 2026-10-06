import json
import mesh_client as mc


def extract_alert_data(data):
    results = []
    case = data.get('case', {})
    customer = case.get('customer', {})
    customer_detail = data.get('customer_detail', {})
    alerts = data.get('alerts', [])

    case_identifier = case.get('identifier')
    case_risk = ', '.join(rt.get('name', '') for rt in case.get('risk_types', []))

    # Customer fields from detail endpoint
    person = customer_detail.get('person', {})
    company = customer_detail.get('company', {})
    undefined = customer_detail.get('undefined', {})

    dob = person.get('date_of_birth', {})
    cust_dob = f"{dob.get('year', '')}-{dob.get('month', '')}-{dob.get('day', '')}" if dob else ''
    inc = company.get('incorporation_date', {})
    cust_incorporation_date = f"{inc.get('year', '')}-{inc.get('month', '')}-{inc.get('day', '')}" if inc else ''
    cust_birth_year = undefined.get('birth_year')
    cust_country_fields = json.dumps({
        'nationality': person.get('nationality', []),
        'country_of_birth': person.get('country_of_birth'),
        'address_countries': [a.get('country') for a in person.get('address', [])]
                             + [a.get('country') for a in company.get('address', [])],
        'countries_of_residence': [r.get('country_of_residence') for r in person.get('residential_information', [])],
        'undefined_countries': undefined.get('country', []),
    })
    cust_custom_fields = json.dumps(
        person.get('custom_fields', [])
        + company.get('custom_fields', [])
        + undefined.get('custom_fields', [])
    )

    for alert in alerts:
        for risk in alert.get('risks', []):
            profile = risk.get('detail', {}).get('profile', {})
            person = profile.get('person', {})
            risk_indicators = profile.get('risk_indicators', {})

            # Profile countries and source names from lists, peps and sanctions
            countries, source_names = [], []
            for entry in risk_indicators.get('lists', []) + risk_indicators.get('peps', []) + risk_indicators.get('sanctions', []):
                countries.extend(entry.get('country_codes', []))
                for field in entry.get('fields', []):
                    if field.get('name') == 'Country':
                        countries.append(field.get('value'))
                source_names.append(entry.get('name', ''))

            entity_type = 'PERSON' if 'person' in profile else 'COMPANY'

            results.append({
                'customer_internal_id': customer.get('identifier'),
                'customer_external_id': customer.get('external_identifier'),
                'customer_name': customer.get('name'),
                'customer_dob': cust_dob,
                'customer_incorporation_date': cust_incorporation_date,
                'customer_birth_year': cust_birth_year,
                'customer_country_fields': cust_country_fields,
                'customer_acquisition_source': customer.get('acquisition_source'),
                'customer_custom_fields': cust_custom_fields,
                'case_id': case_identifier,
                # 'case_risk': case_risk,
                'case_status': case.get('state'),
                'case_created_at': case.get('created_at'),
                'profile_id': profile.get('identifier'),
                'profile_full_name': profile.get('matching_name'),
                'profile_dob': json.dumps(person.get('dates_of_birth', [])),
                'profile_countries': json.dumps(list(dict.fromkeys(countries))),
                'profile_risk_types': json.dumps(risk_indicators.get('aml_types', [])),
                'profile_entity_type': entity_type,
                'profile_source_names': json.dumps(source_names),
                'profile_status': risk.get('decision'),
                'screening_configuration_id': risk.get('detail', {}).get('configuration_identifier'),
                # 'is_muted': risk.get('is_muted'),
                'mesh_url': 'https://mesh.complyadvantage.com/cases/' + case_identifier,
            })
    return results


if __name__ == "__main__":
    mc.run_main(extract_alert_data, "lydia")
