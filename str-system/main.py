import os
import sys
import json
import argparse

# Add the 'code' directory to path to import the original parser
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../code')))

try:
    from parser import parse_xml_file
except ImportError:
    print("Warning: Could not import 'parser' from '../code/parser.py'. Ensure it exists.")
    def parse_xml_file(filepath):
        return None

from src.pipeline.pipeline import run_pipeline

def process_file(filepath: str, output_dir: str):
    print(f"Processing: {filepath}")
    
    parsed_data = parse_xml_file(filepath)
    if not parsed_data:
        print(f"Failed to parse or missing data in {filepath}")
        return
        
    result = run_pipeline(parsed_data)
    
    if result == "insufficient_information":
        print(f"[{filepath}] Result: Insufficient information to score.")
        return
    elif result == "insufficient_evidence_to_score":
        print(f"[{filepath}] Result: Insufficient evidence to score.")
        return
        
    report_id = result.get("report_id", os.path.basename(filepath))
    score = result.get("final_utility_score", 0.0)
    
    print(f"[{report_id}] Final Utility Score: {score:.4f}")
    
    # Save output to JSON
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, f"{report_id}_score.json")
    with open(out_path, 'w') as f:
        json.dump(result, f, indent=2)
    print(f"Saved detailed results to {out_path}")

def main():
    parser = argparse.ArgumentParser(description="STR Signal vs Noise Detection System")
    parser.add_argument("--file", "-f", type=str, help="Path to a single XML file to process")
    parser.add_argument("--dir", "-d", type=str, help="Path to a directory of XML files to process")
    parser.add_argument("--out", "-o", type=str, default="outputs", help="Output directory for JSON results")
    
    args = parser.parse_args()
    
    if not args.file and not args.dir:
        parser.print_help()
        return
        
    if args.file:
        process_file(args.file, args.out)
        
    if args.dir:
        for filename in os.listdir(args.dir):
            if filename.endswith(".xml"):
                process_file(os.path.join(args.dir, filename), args.out)

if __name__ == "__main__":
    main()
