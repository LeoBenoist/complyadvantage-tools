INPUT_DIR="./SourceSample"
OUTPUT_DIR="./SampleConverted"

mkdir -p "$OUTPUT_DIR"

for file in "$INPUT_DIR"/*.xlsx; do
    filename=$(basename "$file")
    echo $filename
    python3 convertHeaders.py "$file" --output "$OUTPUT_DIR/$filename" --prefix test3
    python mergeXlsx.py ./SampleConverted -o mergedSamples.xlsx --split 500000
done