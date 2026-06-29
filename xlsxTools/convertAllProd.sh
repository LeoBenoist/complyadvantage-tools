INPUT_DIR="./FDJ"
OUTPUT_DIR="./FDJConverted"

mkdir -p "$OUTPUT_DIR"

for file in "$INPUT_DIR"/*.xlsx; do
    filename=$(basename "$file")
    echo $filename
    python convertHeaders.py "$file" --output "$OUTPUT_DIR/$filename" --prefix run0629
done

python mergeXlsx.py ./FDJConverted -o run0629merged.xlsx --split 400000
