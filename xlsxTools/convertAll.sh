INPUT_DIR="./FDJ"
OUTPUT_DIR="./FDJConverted"

mkdir -p "$OUTPUT_DIR"

for file in "$INPUT_DIR"/*.xlsx; do
    filename=$(basename "$file")
    echo $filename
    python3 convertHeaders.py "$file" --output "$OUTPUT_DIR/$filename" --prefix run1
done