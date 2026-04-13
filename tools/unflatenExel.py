import pandas as pd
import json
import argparse
import numpy as np

def excel_to_json(excel_filepath, json_filepath):
    """Converts Excel to JSON, handling nested keys and special values."""

    try:
        df = pd.read_excel(excel_filepath)

        def convert_value(value):
            if isinstance(value, pd.Timestamp):
                return value.isoformat()  # Use ISO format for datetime strings
            elif pd.isna(value):
                return None
            elif isinstance(value, float) and (np.isinf(value) or np.isnan(value)):
                return None
            return value

        df = df.applymap(convert_value) # Apply the value conversion

        data = []
        for _, row in df.iterrows():
            item = {}
            for key, value in row.items():
                nested_keys = key.split('.')
                current_level = item
                for nested_key in nested_keys[:-1]:
                    if nested_key not in current_level:
                        current_level[nested_key] = {}
                    current_level = current_level[nested_key]
                current_level[nested_keys[-1]] = value
            data.append(item)


        with open(json_filepath, 'w', encoding='utf-8') as jsonfile:
            json.dump(data, jsonfile, indent=4, ensure_ascii=False, default=str) # Key change here!

        print(f"Successfully converted {excel_filepath} to {json_filepath}")

    except FileNotFoundError:
        print(f"Error: Excel file not found at {excel_filepath}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert Excel to JSON.")
    parser.add_argument("excel_filepath", help="Path to the input Excel file")
    args = parser.parse_args()

    output_file = "result.json"
    excel_to_json(args.excel_filepath, output_file)