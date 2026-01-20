import pandas as pd
import json
import os
import re
import argparse
import sys
from tqdm import tqdm

def normalize_text(text):
    """
    Consistent normalization logic with the StrictMedicalChatbot.
    This version returns the 'keyword version' which is used as the primary lookup key.
    """
    if not isinstance(text, str):
        return ""
    
    # Lowercase
    text = text.lower().strip()
    
    # Remove special characters
    text = re.sub(r'[^\w\s]', '', text)
    
    # Common fillers to ignore for better matching
    fillers = [
        "doctor", "please", "help", "me", "with", "i", "have", "a", "an", "the", 
        "tell", "me", "about", "what", "is", "can", "you", "give", "advice", "on"
    ]
    
    words = text.split()
    # The key is the normalized version (no fillers)
    normalized_words = [w for w in words if w not in fillers]
    
    return " ".join(normalized_words)

def validate_response_lines(response):
    """Check if the response has 5-6 lines."""
    if not isinstance(response, str):
        return False, 0
    lines = [line for line in response.split('\n') if line.strip()]
    count = len(lines)
    return 5 <= count <= 6, count

def bulk_load(input_file, output_file="medical_data.json", append=True, batch_size=10000, strict_lines=False):
    print(f"\n🚀 Starting Bulk Medical Data Loader")
    print(f"------------------------------------")
    print(f"Input File:  {input_file}")
    print(f"Output File: {output_file}")
    print(f"Mode:        {'Append' if append else 'Overwrite'}")
    print(f"Batch Size:  {batch_size}")
    print(f"------------------------------------\n")
    
    # Check file extension
    ext = os.path.splitext(input_file)[1].lower()
    if ext not in ['.csv', '.xlsx', '.xls']:
        print(f"❌ Error: Unsupported file format {ext}. Use CSV or Excel.")
        return

    # Load existing data if appending
    existing_data = {}
    if append and os.path.exists(output_file):
        try:
            print(f"📂 Loading existing dataset...")
            with open(output_file, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
            print(f"✅ Loaded {len(existing_data)} existing entries.")
        except Exception as e:
            print(f"⚠️  Could not load existing {output_file}: {e}")
            print("   Starting with fresh dataset.")

    new_count = 0
    duplicate_count = 0
    line_mismatch_count = 0
    invalid_row_count = 0

    try:
        # Determine total rows for progress bar (optional, can be slow for huge files)
        # For 200k, it's fast enough.
        total_rows = 0
        if ext == '.csv':
            total_rows = sum(1 for _ in open(input_file, encoding='utf-8', errors='ignore')) - 1
        
        # Use iterator for memory efficiency
        if ext == '.csv':
            reader = pd.read_csv(input_file, chunksize=batch_size)
        else:
            # Excel doesn't support chunksize directly in read_excel as easily,
            # but usually Excel files aren't 200k+ rows. If they are, it might take RAM.
            # We'll read the whole thing for Excel.
            df_full = pd.read_excel(input_file)
            reader = [df_full]
            total_rows = len(df_full)

        with tqdm(total=total_rows, desc="Processing rows") as pbar:
            for chunk in reader:
                # Basic validation: ensure required columns exist
                required_cols = ['query', 'response']
                if not all(col in chunk.columns for col in required_cols):
                    print(f"\n❌ Error: Chunk missing required columns: {required_cols}")
                    return

                for _, row in chunk.iterrows():
                    query = row['query']
                    response = row['response']
                    
                    if pd.isna(query) or pd.isna(response):
                        invalid_row_count += 1
                        pbar.update(1)
                        continue
                        
                    # Normalize the query to use as key
                    key = normalize_text(str(query))
                    if not key:
                        invalid_row_count += 1
                        pbar.update(1)
                        continue
                        
                    # Line count validation
                    is_valid_lines, actual_lines = validate_response_lines(str(response))
                    if not is_valid_lines:
                        line_mismatch_count += 1
                        if strict_lines:
                            pbar.update(1)
                            continue
                    
                    # Deduplication
                    if key in existing_data:
                        duplicate_count += 1
                        pbar.update(1)
                        continue
                    
                    # Store entry
                    existing_data[key] = {
                        "output": str(response).strip().replace('\r\n', '\n')
                    }
                    new_count += 1
                    pbar.update(1)

    except Exception as e:
        print(f"\n❌ Error during processing: {e}")
        return

    # Save to JSON
    try:
        print(f"\n💾 Saving to {output_file}...")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, indent=2, ensure_ascii=False)
        
        print(f"🎉 SUCCESS: Bulk Load Complete!")
        print(f"------------------------------------")
        print(f"✅ New entries added:    {new_count}")
        print(f"👯 Duplicates skipped:   {duplicate_count}")
        print(f"❌ Invalid rows skipped: {invalid_row_count}")
        print(f"⚠️  Line mismatches:     {line_mismatch_count}")
        print(f"📊 Total entries now:    {len(existing_data)}")
        print(f"------------------------------------\n")
        
    except Exception as e:
        print(f"❌ Error saving JSON: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verified Medical Dataset Bulk Loader")
    parser.add_argument("input", help="Path to input CSV or Excel file")
    parser.add_argument("--output", default="medical_data.json", help="Path to output JSON (default: medical_data.json)")
    parser.add_argument("--no-append", action="store_false", dest="append", help="Overwrite instead of appending")
    parser.add_argument("--batch-size", type=int, default=10000, help="Number of rows to process per chunk (default: 10000)")
    parser.add_argument("--strict", action="store_true", help="Only load entries that strictly have 5-6 lines")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        print(f"❌ Error: Input file '{args.input}' not found.")
        sys.exit(1)
        
    bulk_load(args.input, args.output, args.append, args.batch_size, args.strict)
