#!/usr/bin/env python3
"""
convertHeaders.py
Converts FDJ Excel exports (French headers) to the transaction format (English headers).
Supports both card (CARTE) and bank (DEPOT, FLUX IP, Prélèvements, RETRAIT PDV) source formats.

Usage:
    python convertHeaders.py <input_file>
    python convertHeaders.py <input_file> --output <output_file>
    python convertHeaders.py <input_file> --sheet <sheet_name>
    python convertHeaders.py <input_file> --format card|bank   # override auto-detection
"""

import argparse
import sys
import uuid
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Shared customer-role type sets (used by both card and bank converters)
# ---------------------------------------------------------------------------

# Types where the FDJ customer is the DEBTOR (sends money / pays)
CUSTOMER_IS_DEBTOR_TYPES = {"CARD_OUT", "IP_OUT", "SDD_IN"}

# Types where the FDJ customer is the CREDITOR (receives money)
CUSTOMER_IS_CREDITOR_TYPES = {"CARD_IN", "IP_IN", "SDD_OUT"}

# P2P role is ambiguous — resolved per-row via the Direction column:
#   Direction = "Credit" → customer is DEBTOR   (RETRAIT: customer sends to PDV)
#   Direction = "Debit"  → customer is CREDITOR (DEPOT:  customer receives from platform)
# P2P has no real external counterparty: use customer name + random UUID.

# ---------------------------------------------------------------------------
# CARD format mappings
# ---------------------------------------------------------------------------

CARD_COLUMN_MAPPING: dict[str, str] = {
    "Id opération": "transaction.external_identifier",
    "Message": "transaction.monetary_transaction.reference_text",
    # "Devise locale":                "transaction.monetary_transaction.local_value.currency",
    "Méthode": "transaction.monetary_transaction.payment_channel",
    " Solde après opération": "transaction.monetary_transaction.customer_account_balance.current_balance.amount",
    # "Libellé 1":                    "transaction.custom_field[1].string_value",
    # "Libellé 2":                    "transaction.custom_field[2].string_value",
    # Card
    # "InitialOperationId":           "transaction.monetary_transaction.card_payment.related_transaction_identifier",
    # "Type carte":                   "transaction.monetary_transaction.card_payment.card.funding_type",
    "Id carte": "transaction.monetary_transaction.card_payment.card.fingerprint",
    # "Xpay utilisé":                 "transaction.monetary_transaction.card_payment.card.wallet_identifier",
    # "Type de Xpay":                 "transaction.monetary_transaction.card_payment.card.wallet_type",
    # "Statut 3Ds":                   "transaction.monetary_transaction.card_payment.card_verification_results.three_d_secure_check.result",
    # "Mode 3Ds":                     "transaction.monetary_transaction.card_payment.card_verification_results.three_d_secure_check.description",
    # card_holder fields that also fan out to customer[1] are in CARD_MULTI_TARGET_MAPPING
    "MCC": "transaction.monetary_transaction.card_payment.merchant.mcc_category_code",
    # "Siret marchand autorisation": "transaction.monetary_transaction.card_payment.merchant.details.counterparty.external_identifier",
    # "Ville marchand autorisation":  "transaction.monetary_transaction.card_payment.merchant.details.structured_address.town_name",
    "Pays marchand autorisation": "transaction.monetary_transaction.card_payment.merchant.details.structured_address.country",
    # "Contexte":                     "transaction.monetary_transaction.payment_channel",
    # Authorization stage
    # "Statut":                       "transaction.monetary_transaction.card_payment.payment_stages_info.authorization.state",
    # "Date d’autorisation": "transaction.monetary_transaction.card_payment.payment_stages_info.authorization.timestamp",
    # "Cause erreur autorisation":    "transaction.monetary_transaction.card_payment.payment_stages_info.authorization.response.reason_code",
    # "Id autorisation":              "transaction.monetary_transaction.card_payment.payment_stages_info.authorization.identifier",
    # "Montant autorisation":         "transaction.monetary_transaction.card_payment.payment_stages_info.authorization.value.amount",
    # Settlement stage
    # "Date de compensation":         "transaction.monetary_transaction.card_payment.payment_stages_info.settlement.timestamp",
    # "Montant compensation":         "transaction.monetary_transaction.card_payment.payment_stages_info.settlement.value.amount",
    # Chargeback stage
    # "Evénement déclencheur": "transaction.monetary_transaction.card_payment.payment_stages_info.chargeback.reason",
    # "Nature dossier contestation": "transaction.monetary_transaction.card_payment.payment_stages_info.chargeback.description",
    # "Cause du chargeback": "transaction.monetary_transaction.card_payment.payment_stages_info.chargeback.outcome",
}

CARD_MULTI_TARGET_MAPPING: dict[str, list[str]] = {
    "Montant": [
        "transaction.monetary_transaction.base_value.amount",
        # "transaction.monetary_transaction.value.amount",
        "transaction.monetary_transaction.card_payment.payment_stages_info.authorization.value.amount",
    ],
    "Pays carte": [
        "transaction.monetary_transaction.card_payment.card_holder.details.structured_address.country",
        "customer[1].person.address[1].country",
    ],
    "Nom marchand autorisation": [
        "transaction.monetary_transaction.card_payment.merchant.details.name",
        "transaction.monetary_transaction.card_payment.merchant.details.counterparty.external_identifier"
    ],
    "Date d’opération": [# IMPORTANT should be ’ and not '
        "transaction.occurred_at.timestamp",
        "transaction.monetary_transaction.card_payment.payment_stages_info.authorization.timestamp",
    ],
}

CARD_OUTPUT_COLUMNS: list[str] = [
    "transaction.classification",
    "transaction.customer_external_identifier",
    "scenario_configuration_identifier[1]",
    "payment_screening_configuration_identifier",
    "transaction.external_identifier",
    "transaction.occurred_at.timestamp",
    "transaction.monetary_transaction.reference_text",
    "transaction.monetary_transaction.base_value.amount",
    "transaction.monetary_transaction.base_value.currency",
    "transaction.monetary_transaction.local_value.amount",
    "transaction.monetary_transaction.local_value.currency",
    "transaction.monetary_transaction.value.amount",
    "transaction.monetary_transaction.value.currency",
    "transaction.monetary_transaction.payment_channel",
    "transaction.monetary_transaction.customer_account_balance.current_balance.amount",
    "transaction.monetary_transaction.customer_account_balance.current_balance.currency",
    "transaction.monetary_transaction.customer_account_balance.current_base_balance.amount",
    "transaction.monetary_transaction.customer_account_balance.current_base_balance.currency",
    "transaction.monetary_transaction.product_name",
    "transaction.custom_field[1].key",
    "transaction.custom_field[1].string_value",
    "transaction.custom_field[1].decimal_value",
    "transaction.custom_field[2].key",
    "transaction.custom_field[2].string_value",
    "transaction.custom_field[2].decimal_value",
    "transaction.monetary_transaction.card_payment.card_payment_type",
    "transaction.monetary_transaction.card_payment.payment_stage",
    "transaction.monetary_transaction.card_payment.card_payment_scope",
    "transaction.monetary_transaction.card_payment.card_scheme",
    "transaction.monetary_transaction.card_payment.related_transaction_identifier",
    "transaction.monetary_transaction.card_payment.card.funding_type",
    "transaction.monetary_transaction.card_payment.card.fingerprint",
    "transaction.monetary_transaction.card_payment.card.wallet_identifier",
    "transaction.monetary_transaction.card_payment.card.wallet_type",
    "transaction.monetary_transaction.card_payment.card_verification_results.avs_check.result",
    "transaction.monetary_transaction.card_payment.card_verification_results.avs_check.description",
    "transaction.monetary_transaction.card_payment.card_verification_results.cvc_check.result",
    "transaction.monetary_transaction.card_payment.card_verification_results.cvc_check.description",
    "transaction.monetary_transaction.card_payment.card_verification_results.three_d_secure_check.result",
    "transaction.monetary_transaction.card_payment.card_verification_results.three_d_secure_check.description",
    "transaction.monetary_transaction.card_payment.card_holder.details.name",
    "transaction.monetary_transaction.card_payment.card_holder.details.customer.external_identifier",
    "transaction.monetary_transaction.card_payment.card_holder.details.structured_address.address_line1",
    "transaction.monetary_transaction.card_payment.card_holder.details.structured_address.address_line2",
    "transaction.monetary_transaction.card_payment.card_holder.details.structured_address.town_name",
    "transaction.monetary_transaction.card_payment.card_holder.details.structured_address.country_subdivision",
    "transaction.monetary_transaction.card_payment.card_holder.details.structured_address.postal_code",
    "transaction.monetary_transaction.card_payment.card_holder.details.structured_address.country",
    "transaction.monetary_transaction.card_payment.card_holder.details.structured_address.address_type",
    "transaction.monetary_transaction.card_payment.card_holder.details.unstructured_address.local_details",
    "transaction.monetary_transaction.card_payment.card_holder.details.unstructured_address.country",
    "transaction.monetary_transaction.card_payment.issuer.bin",
    "transaction.monetary_transaction.card_payment.issuer.details.name",
    "transaction.monetary_transaction.card_payment.issuer.details.counterparty.external_identifier",
    "transaction.monetary_transaction.card_payment.issuer.details.structured_address.address_line1",
    "transaction.monetary_transaction.card_payment.issuer.details.structured_address.address_line2",
    "transaction.monetary_transaction.card_payment.issuer.details.structured_address.town_name",
    "transaction.monetary_transaction.card_payment.issuer.details.structured_address.country_subdivision",
    "transaction.monetary_transaction.card_payment.issuer.details.structured_address.postal_code",
    "transaction.monetary_transaction.card_payment.issuer.details.structured_address.country",
    "transaction.monetary_transaction.card_payment.issuer.details.structured_address.address_type",
    "transaction.monetary_transaction.card_payment.issuer.details.unstructured_address.local_details",
    "transaction.monetary_transaction.card_payment.issuer.details.unstructured_address.country",
    "transaction.monetary_transaction.card_payment.acquirer.identifier",
    "transaction.monetary_transaction.card_payment.acquirer.details.name",
    "transaction.monetary_transaction.card_payment.acquirer.details.counterparty.external_identifier",
    "transaction.monetary_transaction.card_payment.acquirer.details.structured_address.address_line1",
    "transaction.monetary_transaction.card_payment.acquirer.details.structured_address.address_line2",
    "transaction.monetary_transaction.card_payment.acquirer.details.structured_address.town_name",
    "transaction.monetary_transaction.card_payment.acquirer.details.structured_address.country_subdivision",
    "transaction.monetary_transaction.card_payment.acquirer.details.structured_address.postal_code",
    "transaction.monetary_transaction.card_payment.acquirer.details.structured_address.country",
    "transaction.monetary_transaction.card_payment.acquirer.details.structured_address.address_type",
    "transaction.monetary_transaction.card_payment.acquirer.details.unstructured_address.local_details",
    "transaction.monetary_transaction.card_payment.acquirer.details.unstructured_address.country",
    "transaction.monetary_transaction.card_payment.merchant.category_type",
    "transaction.monetary_transaction.card_payment.merchant.mcc_category_code",
    "transaction.monetary_transaction.card_payment.merchant.mcc_code_description",
    "transaction.monetary_transaction.card_payment.merchant.details.name",
    "transaction.monetary_transaction.card_payment.merchant.details.counterparty.external_identifier",
    "transaction.monetary_transaction.card_payment.merchant.details.customer.external_identifier",
    "transaction.monetary_transaction.card_payment.merchant.details.structured_address.address_line1",
    "transaction.monetary_transaction.card_payment.merchant.details.structured_address.address_line2",
    "transaction.monetary_transaction.card_payment.merchant.details.structured_address.town_name",
    "transaction.monetary_transaction.card_payment.merchant.details.structured_address.country_subdivision",
    "transaction.monetary_transaction.card_payment.merchant.details.structured_address.postal_code",
    "transaction.monetary_transaction.card_payment.merchant.details.structured_address.country",
    "transaction.monetary_transaction.card_payment.merchant.details.structured_address.address_type",
    "transaction.monetary_transaction.card_payment.merchant.details.unstructured_address.local_details",
    "transaction.monetary_transaction.card_payment.merchant.details.unstructured_address.country",
    "transaction.monetary_transaction.card_payment.point_of_sale.condition.code",
    "transaction.monetary_transaction.card_payment.point_of_sale.condition.description",
    "transaction.monetary_transaction.card_payment.point_of_sale.entry_mode.code",
    "transaction.monetary_transaction.card_payment.point_of_sale.entry_mode.description",
    "transaction.monetary_transaction.card_payment.payment_stages_info.authorization.state",
    "transaction.monetary_transaction.card_payment.payment_stages_info.authorization.timestamp",
    "transaction.monetary_transaction.card_payment.payment_stages_info.authorization.response.code",
    "transaction.monetary_transaction.card_payment.payment_stages_info.authorization.response.reason_code",
    "transaction.monetary_transaction.card_payment.payment_stages_info.authorization.identifier",
    "transaction.monetary_transaction.card_payment.payment_stages_info.authorization.value.amount",
    "transaction.monetary_transaction.card_payment.payment_stages_info.authorization.value.currency",
    "transaction.monetary_transaction.card_payment.payment_stages_info.authorization.type",
    "transaction.monetary_transaction.card_payment.payment_stages_info.settlement.timestamp",
    "transaction.monetary_transaction.card_payment.payment_stages_info.settlement.value.amount",
    "transaction.monetary_transaction.card_payment.payment_stages_info.settlement.value.currency",
    "transaction.monetary_transaction.card_payment.payment_stages_info.reversal.timestamp",
    "transaction.monetary_transaction.card_payment.payment_stages_info.reversal.value.amount",
    "transaction.monetary_transaction.card_payment.payment_stages_info.reversal.value.currency",
    "transaction.monetary_transaction.card_payment.payment_stages_info.reversal.identifier",
    "transaction.monetary_transaction.card_payment.payment_stages_info.refund.timestamp",
    "transaction.monetary_transaction.card_payment.payment_stages_info.refund.reason.code",
    "transaction.monetary_transaction.card_payment.payment_stages_info.refund.reason.description",
    "transaction.monetary_transaction.card_payment.payment_stages_info.chargeback.value.amount",
    "transaction.monetary_transaction.card_payment.payment_stages_info.chargeback.value.currency",
    "transaction.monetary_transaction.card_payment.payment_stages_info.chargeback.timestamp",
    "transaction.monetary_transaction.card_payment.payment_stages_info.chargeback.reason",
    "transaction.monetary_transaction.card_payment.payment_stages_info.chargeback.description",
    "transaction.monetary_transaction.card_payment.payment_stages_info.chargeback.outcome",
    "transaction.regulatory_reporting.fincen_cash_transaction_subtype",
    "transaction.regulatory_reporting.gto_type_codes[1]",
    "transaction.regulatory_reporting.transaction_location_external_identifier",
    # Customer (card holder)
    "customer[1].external_identifier",
    "customer[1].person.full_name",
]

CONTEXTE_PAYMENT_CHANNEL: dict[str, str] = {
    "RemotePayment": "WEB",
    "FundTransfer": "OTHER",
    "ProximityPayment": "OTHER",
    "UnattendedVendingMachine": "OTHER",
    "QuasiCash": "OTHER",
    "AtmWithdrawal": "ATM",
    "PreAuthorization": "OTHER",
    "CashAdvance": "OTHER",
}

CARD_PREFIX_COLUMNS = [
    "transaction.external_identifier",
    "transaction.monetary_transaction.card_payment.card_holder.details.customer.external_identifier",
    "transaction.monetary_transaction.card_payment.merchant.details.counterparty.external_identifier",
    "transaction.customer_external_identifier",
    "customer[1].external_identifier",
]

# ---------------------------------------------------------------------------
# BANK format mappings
# ---------------------------------------------------------------------------

# Simple one-to-one column mappings that apply regardless of direction
BANK_COLUMN_MAPPING: dict[str, str] = {
    "Id opération": "transaction.external_identifier",
    "Date d’opération": "transaction.occurred_at.timestamp",
    # "Mandate Id": "transaction.monetary_transaction.bank_payment.mandate_identifier",
    # "Id interbancaire": "transaction.monetary_transaction.bank_payment.end_to_end_identifier",
    "Référence": "transaction.monetary_transaction.bank_payment.remittance_information",
}

# Type d’opération → payment_scheme
TYPE_TO_PAYMENT_SCHEME: dict[str, str] = {
    "IP_IN": "SEPA",
    "IP_OUT": "SEPA",
    "SDD_IN": "SEPA",
    "SDD_OUT": "SEPA",
    "P2P": "OTHER",
}

# Type d’opération → payment_channel
TYPE_TO_PAYMENT_CHANNEL: dict[str, str] = {
    "IP_IN": "OTHER",
    "IP_OUT": "OTHER",
    "SDD_IN": "OTHER",
    "SDD_OUT": "OTHER",
    "P2P": "OTHER",
}

# Statut → bank_payment.state
STATUT_TO_STATE: dict[str, str] = {
    "Completed": "BOOKED",
    "Pending": "PENDING",
    "Failed": "BOOKED",
    "Rejected": "BOOKED",
    "Processing": "PENDING",
    "Cancelled": "BOOKED",
}

BANK_OUTPUT_COLUMNS: list[str] = [
    "transaction.classification",
    "transaction.customer_external_identifier",
    "scenario_configuration_identifier[1]",
    "payment_screening_configuration_identifier",
    "transaction.external_identifier",
    "transaction.occurred_at.timestamp",
    "transaction.monetary_transaction.reference_text",
    "transaction.monetary_transaction.base_value.amount",
    "transaction.monetary_transaction.base_value.currency",
    "transaction.monetary_transaction.local_value.amount",
    "transaction.monetary_transaction.local_value.currency",
    "transaction.monetary_transaction.value.amount",
    "transaction.monetary_transaction.value.currency",
    "transaction.monetary_transaction.payment_channel",
    "transaction.monetary_transaction.customer_account_balance.current_balance.amount",
    "transaction.monetary_transaction.customer_account_balance.current_balance.currency",
    "transaction.monetary_transaction.customer_account_balance.current_base_balance.amount",
    "transaction.monetary_transaction.customer_account_balance.current_base_balance.currency",
    "transaction.monetary_transaction.product_name",
    "transaction.custom_field[1].key",
    "transaction.custom_field[1].string_value",
    "transaction.custom_field[1].decimal_value",
    "transaction.custom_field[2].key",
    "transaction.custom_field[2].string_value",
    "transaction.custom_field[2].decimal_value",
    "transaction.monetary_transaction.bank_payment.state",
    "transaction.monetary_transaction.bank_payment.payment_scheme",
    "transaction.monetary_transaction.bank_payment.end_to_end_identifier",
    "transaction.monetary_transaction.bank_payment.mandate_identifier",
    "transaction.monetary_transaction.bank_payment.remittance_information",
    # Debtor
    "transaction.monetary_transaction.bank_payment.debtor.name",
    "transaction.monetary_transaction.bank_payment.debtor.counterparty.external_identifier",
    "transaction.monetary_transaction.bank_payment.debtor.customer.external_identifier",
    "transaction.monetary_transaction.bank_payment.debtor.structured_address.address_line1",
    "transaction.monetary_transaction.bank_payment.debtor.structured_address.address_line2",
    "transaction.monetary_transaction.bank_payment.debtor.structured_address.town_name",
    "transaction.monetary_transaction.bank_payment.debtor.structured_address.country_subdivision",
    "transaction.monetary_transaction.bank_payment.debtor.structured_address.postal_code",
    "transaction.monetary_transaction.bank_payment.debtor.structured_address.country",
    "transaction.monetary_transaction.bank_payment.debtor.structured_address.address_type",
    "transaction.monetary_transaction.bank_payment.debtor.unstructured_address.local_details",
    "transaction.monetary_transaction.bank_payment.debtor.unstructured_address.country",
    "transaction.monetary_transaction.bank_payment.debtor.account.iban",
    "transaction.monetary_transaction.bank_payment.debtor.account.account_identifier",
    # Ultimate debtor
    "transaction.monetary_transaction.bank_payment.ultimate_debtor.details.name",
    "transaction.monetary_transaction.bank_payment.ultimate_debtor.details.counterparty.external_identifier",
    "transaction.monetary_transaction.bank_payment.ultimate_debtor.details.customer.external_identifier",
    "transaction.monetary_transaction.bank_payment.ultimate_debtor.account.iban",
    # Creditor
    "transaction.monetary_transaction.bank_payment.creditor.name",
    "transaction.monetary_transaction.bank_payment.creditor.counterparty.external_identifier",
    "transaction.monetary_transaction.bank_payment.creditor.customer.external_identifier",
    "transaction.monetary_transaction.bank_payment.creditor.structured_address.address_line1",
    "transaction.monetary_transaction.bank_payment.creditor.structured_address.address_line2",
    "transaction.monetary_transaction.bank_payment.creditor.structured_address.town_name",
    "transaction.monetary_transaction.bank_payment.creditor.structured_address.country_subdivision",
    "transaction.monetary_transaction.bank_payment.creditor.structured_address.postal_code",
    "transaction.monetary_transaction.bank_payment.creditor.structured_address.country",
    "transaction.monetary_transaction.bank_payment.creditor.structured_address.address_type",
    "transaction.monetary_transaction.bank_payment.creditor.unstructured_address.local_details",
    "transaction.monetary_transaction.bank_payment.creditor.unstructured_address.country",
    "transaction.monetary_transaction.bank_payment.creditor.account.iban",
    "transaction.monetary_transaction.bank_payment.creditor.account.account_identifier",
    # Ultimate creditor
    "transaction.monetary_transaction.bank_payment.ultimate_creditor.details.name",
    "transaction.monetary_transaction.bank_payment.ultimate_creditor.details.counterparty.external_identifier",
    "transaction.monetary_transaction.bank_payment.ultimate_creditor.details.customer.external_identifier",
    "transaction.monetary_transaction.bank_payment.ultimate_creditor.account.iban",
    # Agents
    "transaction.monetary_transaction.bank_payment.agents[1].bank.bic",
    "transaction.monetary_transaction.bank_payment.agents[1].bank.details.name",
    "transaction.monetary_transaction.bank_payment.agents[1].bank.details.counterparty.external_identifier",
    "transaction.monetary_transaction.bank_payment.agents[1].bank.details.structured_address.address_line1",
    "transaction.monetary_transaction.bank_payment.agents[1].bank.details.structured_address.address_line2",
    "transaction.monetary_transaction.bank_payment.agents[1].bank.details.structured_address.town_name",
    "transaction.monetary_transaction.bank_payment.agents[1].bank.details.structured_address.country_subdivision",
    "transaction.monetary_transaction.bank_payment.agents[1].bank.details.structured_address.postal_code",
    "transaction.monetary_transaction.bank_payment.agents[1].bank.details.structured_address.country",
    "transaction.monetary_transaction.bank_payment.agents[1].bank.details.structured_address.address_type",
    "transaction.monetary_transaction.bank_payment.agents[1].bank.details.unstructured_address.local_details",
    "transaction.monetary_transaction.bank_payment.agents[1].bank.details.unstructured_address.country",
    "transaction.regulatory_reporting.fincen_cash_transaction_subtype",
    "transaction.regulatory_reporting.gto_type_codes[1]",
    "transaction.regulatory_reporting.transaction_location_external_identifier",
    # Customer (FDJ account holder)
    "customer[1].external_identifier",
    "customer[1].person.full_name",
]

BANK_PREFIX_COLUMNS = [
    "transaction.external_identifier",
    "transaction.customer_external_identifier",
    "customer[1].external_identifier",
    "transaction.monetary_transaction.bank_payment.debtor.customer.external_identifier",
    "transaction.monetary_transaction.bank_payment.debtor.counterparty.external_identifier",
    "transaction.monetary_transaction.bank_payment.creditor.customer.external_identifier",
    "transaction.monetary_transaction.bank_payment.creditor.counterparty.external_identifier",
]

# ---------------------------------------------------------------------------
# Source-type detection
# ---------------------------------------------------------------------------

CARD_OP_TYPES = {"CARD_OUT", "CARD_IN"}


def detect_source_type(df: pd.DataFrame) -> str:
    """Return 'card' if the data looks like card transactions, else 'bank'."""
    if "Id carte" in df.columns and df["Id carte"].notna().any():
        return "card"
    if "Type d’opération" in df.columns:
        op_types = set(df["Type d’opération"].dropna().unique())
        if op_types & CARD_OP_TYPES:
            return "card"
    return "bank"


# ---------------------------------------------------------------------------
# Converters
# ---------------------------------------------------------------------------

def _apply_common_post_processing(result: pd.DataFrame, df: pd.DataFrame, prefix: str, prefix_cols: list[str]) -> None:
    """In-place: set classification, currency, apply prefix, format dates, cast amounts."""
    result["transaction.classification"] = "MONETARY"
    result["scenario_configuration_identifier[1]"] = "019eabb9-8538-7d36-b479-c78df293d136"

    # Set currency to EUR for every populated amount column
    for col in list(result.columns):
        if col.endswith(".amount") and result[col].notna().any():
            result[col.removesuffix(".amount") + ".currency"] = "EUR"

    # Override currency from source Devise column when present
    if "Devise" in df.columns:
        for col in list(result.columns):
            if col.endswith(".base_value.currency"):
                result[col] = df["Devise"].where(df["Devise"].notna(), result[col])

    if prefix:
        for col in prefix_cols:
            if col in result.columns:
                mid = "ct-" if col.endswith("counterparty.external_identifier") else ""
                result[col] = prefix + "-" + mid + result[col].astype(str)

    for col in result.columns:
        if col.endswith(".timestamp"):
            result[col] = pd.to_datetime(result[col], dayfirst=True, errors="coerce").dt.strftime(
                "%Y-%m-%dT%H:%M:%S.%fZ"
            )

    for col in result.columns:
        if col.endswith(".amount"):
            result[col] = pd.to_numeric(result[col], errors="coerce")


def convert_card(df: pd.DataFrame, prefix: str = "") -> pd.DataFrame:
    """Convert a card-transaction DataFrame to the card output format."""
    if "Type d’opération" in df.columns:
        invalid = df[~df["Type d’opération"].isin(CARD_OP_TYPES)]["Type d’opération"].dropna().unique()
        if len(invalid):
            raise ValueError(f"Unexpected 'Type d\'opération' value(s): {list(invalid)}")

    # Skip rows where Identité créditeur is empty
    if "Identité créditeur" in df.columns:
        before = len(df)
        df = df[df["Identité créditeur"].notna() & (df["Identité créditeur"].astype(str).str.strip() != "")].copy()
        dropped = before - len(df)
        if dropped:
            print(f"Skipped {dropped} row(s) with empty 'Identité créditeur'.", file=sys.stderr)

    all_mapped = set(CARD_COLUMN_MAPPING) | set(CARD_MULTI_TARGET_MAPPING)
    missing = [col for col in all_mapped if col not in df.columns]
    if missing:
        print(f"Warning: {len(missing)} source column(s) not found in input:", file=sys.stderr)
        for col in missing:
            print(f"  - {col!r}", file=sys.stderr)

    result = pd.DataFrame(index=df.index)

    for src_col, targets in CARD_MULTI_TARGET_MAPPING.items():
        if src_col in df.columns:
            for target in targets:
                result[target] = df[src_col]

    # Merchant name fallback: if "Nom marchand autorisation" is empty, use "Nom marchand compensation"
    merchant_name_col = "transaction.monetary_transaction.card_payment.merchant.details.name"
    merchant_cp_col = "transaction.monetary_transaction.card_payment.merchant.details.counterparty.external_identifier"
    if "Nom marchand compensation" in df.columns:
        fallback = df["Nom marchand compensation"]
        for col in (merchant_name_col, merchant_cp_col):
            if col not in result.columns:
                result[col] = fallback
            else:
                result[col] = result[col].where(result[col].notna() & (result[col] != ""), fallback)

    for src_col, tgt_col in CARD_COLUMN_MAPPING.items():
        if src_col in df.columns:
            result[tgt_col] = df[src_col]

    if "Contexte" in df.columns:
        unknown = [v for v in df["Contexte"].dropna().unique() if v not in CONTEXTE_PAYMENT_CHANNEL]
        if unknown:
            raise ValueError(f"Unexpected 'Contexte' value(s): {unknown}")
        result["transaction.monetary_transaction.payment_channel"] = df["Contexte"].map(CONTEXTE_PAYMENT_CHANNEL)

    # Card holder assignment — conditional on transaction direction.
    # CARD_OUT: customer is the DEBTOR (card holder pays merchant)
    #   → card holder name comes from Identité débiteur
    # CARD_IN:  customer is the CREDITOR (card holder receives refund/cashback)
    #   → card holder name comes from Identité créditeur
    # Merchant is always the COUNTERPARTY regardless of direction.
    if "Type d’opération" in df.columns:
        is_card_out = df["Type d’opération"].isin(CUSTOMER_IS_DEBTOR_TYPES)
        is_card_in = df["Type d’opération"].isin(CUSTOMER_IS_CREDITOR_TYPES)
    else:
        # No type column — assume CARD_OUT (original behaviour)
        is_card_out = pd.Series(True, index=df.index)
        is_card_in = pd.Series(False, index=df.index)

    # For each direction: set card holder name AND the three customer identity fields
    # from the customer's name. The prefix mechanism in post-processing will turn these
    # into "{prefix}-{customer_name}", giving a deterministic, human-readable customer ID.
    card_holder_name_col = "transaction.monetary_transaction.card_payment.card_holder.details.name"

    def _set_card_customer(mask: pd.Series, name_src_col: str) -> None:
        if name_src_col not in df.columns or not mask.any():
            return
        names = df.loc[mask, name_src_col]
        result.loc[mask, card_holder_name_col] = names
        result.loc[mask, "customer[1].person.full_name"] = names
        result.loc[mask, "customer[1].external_identifier"] = names
        result.loc[mask, "transaction.customer_external_identifier"] = names
        result.loc[mask, "transaction.monetary_transaction.card_payment.card_holder.details.name"] = names
        result.loc[mask, "transaction.monetary_transaction.card_payment.card_holder.details.customer.external_identifier"] = names

    _set_card_customer(is_card_out, "Identité débiteur")
    _set_card_customer(is_card_in, "Identité créditeur")

    _apply_common_post_processing(result, df, prefix, CARD_PREFIX_COLUMNS)

    # Zero-pad MCC to 4 digits (e.g. "818" → "0818")
    mcc_col = "transaction.monetary_transaction.card_payment.merchant.mcc_category_code"
    if mcc_col in result.columns:
        result[mcc_col] = result[mcc_col].apply(
            lambda v: str(int(v)).zfill(4) if pd.notna(v) else v
        )

    # CARD_IN: customer receives money → amount is negative
    if is_card_in.any():
        for col in result.columns:
            if col.endswith(".amount"):
                result.loc[is_card_in, col] = -result.loc[is_card_in, col]

    populated = [col for col in CARD_OUTPUT_COLUMNS if col in result.columns and result[col].notna().any()]
    return result[populated]


def convert_bank(df: pd.DataFrame, prefix: str = "") -> pd.DataFrame:
    """Convert a bank-transaction DataFrame to the bank output format.

    Direction semantics (from FDJ platform account perspective):
      "Debit"  → money leaves platform → customer is the CREDITOR (receives money)
      "Credit" → money enters platform → customer is the DEBTOR (sends money)
    """
    result = pd.DataFrame(index=df.index)

    # Simple column mappings
    for src_col, tgt_col in BANK_COLUMN_MAPPING.items():
        if src_col in df.columns:
            result[tgt_col] = df[src_col]

    # Reference text: prefer Message, fall back to Libellé
    if "Message" in df.columns:
        result["transaction.monetary_transaction.reference_text"] = df["Message"]
    if "Libellé" in df.columns:
        ref_col = "transaction.monetary_transaction.reference_text"
        if ref_col not in result.columns:
            result[ref_col] = df["Libellé"]
        else:
            result[ref_col] = result[ref_col].where(result[ref_col].notna(), df["Libellé"])

    # Amount
    if "Montant" in df.columns:
        result["transaction.monetary_transaction.base_value.amount"] = df["Montant"]

    # Payment scheme and channel from Type d’opération
    if "Type d’opération" in df.columns:
        unknown_types = [
            v for v in df["Type d’opération"].dropna().unique()
            if v not in TYPE_TO_PAYMENT_SCHEME
        ]
        if unknown_types:
            print(f"Warning: unknown 'Type d\'opération' value(s): {unknown_types}", file=sys.stderr)

        result["transaction.monetary_transaction.bank_payment.payment_scheme"] = (
            df["Type d’opération"].map(TYPE_TO_PAYMENT_SCHEME)
        )
        result["transaction.monetary_transaction.payment_channel"] = (
            df["Type d’opération"].map(TYPE_TO_PAYMENT_CHANNEL)
        )

    # Bank payment state from Statut; default to BOOKED when empty
    state_col = "transaction.monetary_transaction.bank_payment.state"
    if "Statut" in df.columns:
        result[state_col] = df["Statut"].map(STATUT_TO_STATE)
    if state_col not in result.columns:
        result[state_col] = "BOOKED"
    else:
        empty_state = result[state_col].isna() | (result[state_col].astype(str).str.strip() == "")
        result.loc[empty_state, state_col] = "BOOKED"

    # Customer / counterparty assignment.
    #
    # Each transaction has exactly one CUSTOMER (debtor XOR creditor) and one COUNTERPARTY.
    # The three fields customer[1].external_identifier, customer[1].person.full_name, and
    # transaction.customer_external_identifier must always be filled for every row.
    #
    # Priority 1 – explicit type rules (unambiguous):
    #   CUSTOMER_IS_DEBTOR_TYPES  : IP_OUT, SDD_IN
    #   CUSTOMER_IS_CREDITOR_TYPES: IP_IN,  SDD_OUT
    # Priority 2 – Direction fallback for P2P and unknown types:
    #   Direction = "Debit"  → customer is creditor (money leaves platform to customer)
    #   Direction = "Credit" → customer is debtor   (money enters platform from customer)
    op_col = "Type d’opération"
    has_op = op_col in df.columns
    has_dir = "Direction" in df.columns

    # Build mutually exclusive boolean masks (a row can be in at most one)
    if has_op:
        customer_is_creditor = df[op_col].isin(CUSTOMER_IS_CREDITOR_TYPES)
        customer_is_debtor = df[op_col].isin(CUSTOMER_IS_DEBTOR_TYPES)
        needs_direction = ~(customer_is_creditor | customer_is_debtor)
        if has_dir and needs_direction.any():
            dir_is_debit = df["Direction"].str.strip().str.lower() == "debit"
            customer_is_creditor = customer_is_creditor | (needs_direction & dir_is_debit)
            customer_is_debtor = customer_is_debtor | (needs_direction & ~dir_is_debit)
    elif has_dir:
        dir_is_debit = df["Direction"].str.strip().str.lower() == "debit"
        customer_is_creditor = dir_is_debit
        customer_is_debtor = ~dir_is_debit
    else:
        customer_is_creditor = pd.Series(False, index=df.index)
        customer_is_debtor = pd.Series(False, index=df.index)

    unresolved = ~(customer_is_creditor | customer_is_debtor)
    if unresolved.any():
        print(
            f"Warning: {unresolved.sum()} row(s) have no customer role resolved "
            f"(missing Type d’opération / Direction). "
            f"customer[1].external_identifier will be empty for those rows.",
            file=sys.stderr,
        )

    # --- customer is CREDITOR, counterparty is debtor ---
    # Customer ID is built from the customer's name; the prefix mechanism in post-processing
    # will produce the final "{prefix}-{customer_name}" identifier.
    cred_name_col = "Identité créditeur"
    deb_name_col = "Identité débiteur"

    if customer_is_creditor.any():
        if cred_name_col in df.columns:
            names = df.loc[customer_is_creditor, cred_name_col]
            result.loc[customer_is_creditor, "customer[1].person.full_name"] = names
            result.loc[customer_is_creditor, "customer[1].external_identifier"] = names
            result.loc[customer_is_creditor, "transaction.customer_external_identifier"] = names
            result.loc[customer_is_creditor, "transaction.monetary_transaction.bank_payment.creditor.customer.external_identifier"] = names
            result.loc[customer_is_creditor, "transaction.monetary_transaction.bank_payment.creditor.name"] = names

        # Counterparty = debtor side — use name as ID (prefix applied in post-processing)
        if deb_name_col in df.columns:
            result.loc[customer_is_creditor, "transaction.monetary_transaction.bank_payment.debtor.counterparty.external_identifier"] = df.loc[customer_is_creditor, deb_name_col]
            result.loc[customer_is_creditor, "transaction.monetary_transaction.bank_payment.debtor.name"] = df.loc[customer_is_creditor, deb_name_col]

    # --- customer is DEBTOR, counterparty is creditor ---
    if customer_is_debtor.any():
        if deb_name_col in df.columns:
            names = df.loc[customer_is_debtor, deb_name_col]
            result.loc[customer_is_debtor, "customer[1].person.full_name"] = names
            result.loc[customer_is_debtor, "customer[1].external_identifier"] = names
            result.loc[customer_is_debtor, "transaction.customer_external_identifier"] = names
            result.loc[customer_is_debtor, "transaction.monetary_transaction.bank_payment.debtor.customer.external_identifier"] = names
            result.loc[customer_is_debtor, "transaction.monetary_transaction.bank_payment.debtor.name"] = names

        # Counterparty = creditor side — use name as ID (prefix applied in post-processing)
        if cred_name_col in df.columns:
            result.loc[customer_is_debtor, "transaction.monetary_transaction.bank_payment.creditor.counterparty.external_identifier"] = df.loc[customer_is_debtor, cred_name_col]
            result.loc[customer_is_debtor, "transaction.monetary_transaction.bank_payment.creditor.name"] = df.loc[customer_is_debtor, cred_name_col]

    # --- P2P: no real external counterparty ---
    # Override counterparty fields with the customer's own name and a generated UUID.
    # This applies to DEPOT (customer=creditor, counterparty=debtor side)
    # and RETRAIT (customer=debtor, counterparty=creditor side).
    if has_op:
        is_p2p = df[op_col].str.strip() == "P2P"

        p2p_cred = is_p2p & customer_is_creditor
        if p2p_cred.any():
            n = int(p2p_cred.sum())
            customer_names = result.loc[p2p_cred, "customer[1].person.full_name"]
            result["transaction.monetary_transaction.bank_payment.debtor.name"] = result["transaction.monetary_transaction.bank_payment.debtor.name"].astype(object)
            result["transaction.monetary_transaction.bank_payment.debtor.counterparty.external_identifier"] = result["transaction.monetary_transaction.bank_payment.debtor.counterparty.external_identifier"].astype(object)
            result.loc[p2p_cred, "transaction.monetary_transaction.bank_payment.debtor.name"] = customer_names.to_numpy(dtype=object)
            result.loc[p2p_cred, "transaction.monetary_transaction.bank_payment.debtor.counterparty.external_identifier"] = customer_names.to_numpy(dtype=object)


        p2p_deb = is_p2p & customer_is_debtor
        if p2p_deb.any():
            n = int(p2p_deb.sum())
            customer_names = result.loc[p2p_deb, "customer[1].person.full_name"]
            result["transaction.monetary_transaction.bank_payment.creditor.name"] = result["transaction.monetary_transaction.bank_payment.creditor.name"].astype(object)
            result["transaction.monetary_transaction.bank_payment.creditor.counterparty.external_identifier"] = result["transaction.monetary_transaction.bank_payment.creditor.counterparty.external_identifier"].astype(object)
            result.loc[p2p_deb, "transaction.monetary_transaction.bank_payment.creditor.name"] = customer_names.to_numpy(dtype=object)
            result.loc[p2p_deb, "transaction.monetary_transaction.bank_payment.creditor.counterparty.external_identifier"] = customer_names.to_numpy(dtype=object)

    _apply_common_post_processing(result, df, prefix, BANK_PREFIX_COLUMNS)

    # Remove rows that don't have at least one non-empty counterparty.external_identifier
    # and at least one non-empty customer.external_identifier
    counterparty_cols = [c for c in result.columns if "counterparty.external_identifier" in c]
    customer_cols = [c for c in result.columns if "customer.external_identifier" in c]

    def _any_nonempty(cols):
        if not cols:
            return pd.Series(False, index=result.index)
        filled = pd.concat(
            [result[c].notna() & (result[c].astype(str).str.strip() != "") for c in cols],
            axis=1,
        )
        return filled.any(axis=1)

    has_counterparty = _any_nonempty(counterparty_cols)
    has_customer = _any_nonempty(customer_cols)

    remove_mask = ~has_counterparty | ~has_customer
    removed = int(remove_mask.sum())
    if removed:
        print(
            f"Removed {removed} row(s) missing a counterparty.external_identifier or customer.external_identifier.",
            file=sys.stderr,
        )
        result = result[~remove_mask]

    populated = [col for col in BANK_OUTPUT_COLUMNS if col in result.columns and result[col].notna().any()]
    return result[populated]


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def convert(
    input_path: Path,
    sheet: "str | None" = None,
    prefix: str = "",
    fmt: "str | None" = None,
) -> tuple[pd.DataFrame, str]:
    """Read *input_path* and return (converted_df, detected_format).

    *fmt* overrides auto-detection when set to 'card' or 'bank'.
    """
    df = pd.read_excel(input_path, sheet_name=sheet or 0)

    source_type = fmt if fmt in ("card", "bank") else detect_source_type(df)
    print(f"Source format: {source_type.upper()}", file=sys.stderr)

    if source_type == "card":
        return convert_card(df, prefix=prefix), "card"
    else:
        return convert_bank(df, prefix=prefix), "bank"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Convert FDJ Excel export (card or bank) to the transaction format."
    )
    parser.add_argument("input", help="Path to the input Excel file")
    parser.add_argument(
        "--output", "-o",
        help="Output file path; extension determines format (.csv or .xlsx, default: .csv)",
        default=None,
    )
    parser.add_argument(
        "--sheet", "-s",
        help="Sheet name or index to read (default: first sheet)",
        default=None,
    )
    parser.add_argument(
        "--prefix", "-p",
        help="String prepended to customer/account identifier columns",
        default="",
    )
    parser.add_argument(
        "--format", "-f",
        dest="fmt",
        choices=["card", "bank"],
        help="Force input format (default: auto-detect from columns / Type d’opération)",
        default=None,
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.is_file():
        print(f"Error: '{input_path}' is not a valid file.", file=sys.stderr)
        sys.exit(1)

    output_path = Path(args.output) if args.output else input_path.with_name(f"{input_path.stem}_converted.csv")

    if output_path.suffix.lower() not in (".csv", ".xlsx"):
        print(f"Error: unsupported output extension '{output_path.suffix}' (use .csv or .xlsx).", file=sys.stderr)
        sys.exit(1)

    print(f"Reading:  {input_path.resolve()}")
    df, detected_fmt = convert(input_path, sheet=args.sheet, prefix=args.prefix, fmt=args.fmt)
    print(f"Format: {detected_fmt}  |  Rows: {len(df):,}  |  Output columns: {len(df.columns)}")

    if output_path.suffix.lower() == ".xlsx":
        df.to_excel(output_path, index=False)
    else:
        df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"Saved:    {output_path.resolve()}")


if __name__ == "__main__":
    main()
