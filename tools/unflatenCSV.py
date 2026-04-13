import csv
import json
import argparse

def csv_to_json(csv_filepath, json_filepath):
    """Converts a CSV file to a JSON array of objects and dumps it to a file.

    Args:
        csv_filepath: Path to the CSV file.
        json_filepath: Path to the output JSON file.
    """

    try:
        with open(csv_filepath, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            data = []
            for row in reader:
                new_row = {}
                for key, value in row.items():
                    new_key = key.replace('.', '_')  # Replace . with _ for valid JSON keys
                    new_row[new_key] = value.strip()  # Strip whitespace
                data.append(new_row)

        with open(json_filepath, 'w', encoding='utf-8') as jsonfile:
            json.dump(data, jsonfile, indent=4, ensure_ascii=False)  # Indent for readability

        print(f"Successfully converted {csv_filepath} to {json_filepath}")

    except FileNotFoundError:
        print(f"Error: CSV file not found at {csv_filepath}")
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert CSV to JSON.")
    parser.add_argument("csv_filepath", help="Path to the input CSV file")
    # Removed the json_filepath argument and hardcoded the output file
    args = parser.parse_args()

    output_file = "result.json"  # Hardcoded output file name
    csv_to_json(args.csv_filepath, output_file)