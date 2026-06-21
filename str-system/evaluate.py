import os
import sys
import json
import glob
import time

# Add the 'code' directory to path to import the original parser
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../code')))

try:
    from parser import parse_xml_file
except ImportError:
    print("Warning: Could not import 'parser' from '../code/parser.py'. Ensure it exists.")
    def parse_xml_file(filepath):
        return None

from src.pipeline.pipeline import run_pipeline

def evaluate_system():
    reports_dir = os.path.join("..", "code", "data", "reports")
    output_dir = "outputs"
    
    xml_files = sorted(glob.glob(os.path.join(reports_dir, "*.xml")))[:30]
    
    metrics = {
        "final_score": [],
        "coverage_score": [],
        "validation_score": [],
        "signal_score": [],
        "noise_score": []
    }
    
    print(f"Starting evaluation of {len(xml_files)} reports...")
    start_time = time.time()
    
    processed_count = 0
    
    for filepath in xml_files:
        print(f"Processing: {os.path.basename(filepath)}")
        parsed_data = parse_xml_file(filepath)
        if not parsed_data:
            print(f"Failed to parse {filepath}")
            continue
            
        result = run_pipeline(parsed_data)
        if isinstance(result, str):
            print(f"Skipped {filepath}: {result}")
            continue
            
        report_id = result.get("report_id", os.path.basename(filepath))
        
        # Save output
        os.makedirs(output_dir, exist_ok=True)
        out_path = os.path.join(output_dir, f"{report_id}_score.json")
        with open(out_path, 'w') as f:
            json.dump(result, f, indent=2)
            
        # Collect metrics
        metrics["final_score"].append(result.get("final_utility_score", 0.0))
        comps = result.get("components", {})
        metrics["coverage_score"].append(comps.get("coverage_score", 0.0))
        metrics["validation_score"].append(comps.get("validation_score", 0.0))
        metrics["signal_score"].append(comps.get("signal_score", 0.0))
        metrics["noise_score"].append(comps.get("noise_score", 0.0))
        
        processed_count += 1
        
    end_time = time.time()
    duration = end_time - start_time
    
    if processed_count == 0:
        print("No reports processed.")
        return
        
    def avg(lst): return sum(lst) / len(lst) if lst else 0.0
    def vmin(lst): return min(lst) if lst else 0.0
    def vmax(lst): return max(lst) if lst else 0.0
    
    md_content = f"""# STR System Evaluation Report

**Total Reports Processed:** {processed_count}
**Time Taken:** {duration:.2f} seconds
**Average Processing Time:** {duration/processed_count:.2f} sec/report

## Aggregate Metrics

| Metric | Average | Minimum | Maximum |
|--------|---------|---------|---------|
| **Final Utility Score** | `{avg(metrics['final_score']):.4f}` | `{vmin(metrics['final_score']):.4f}` | `{vmax(metrics['final_score']):.4f}` |
| **Coverage Score** | `{avg(metrics['coverage_score']):.4f}` | `{vmin(metrics['coverage_score']):.4f}` | `{vmax(metrics['coverage_score']):.4f}` |
| **Validation Score** | `{avg(metrics['validation_score']):.4f}` | `{vmin(metrics['validation_score']):.4f}` | `{vmax(metrics['validation_score']):.4f}` |
| **Signal Score** | `{avg(metrics['signal_score']):.4f}` | `{vmin(metrics['signal_score']):.4f}` | `{vmax(metrics['signal_score']):.4f}` |
| **Noise Score** | `{avg(metrics['noise_score']):.4f}` | `{vmin(metrics['noise_score']):.4f}` | `{vmax(metrics['noise_score']):.4f}` |

## Summary
These metrics reflect the deterministic parser's accuracy and the LLM's analytical consistency across {processed_count} reports.
"""

    print("\n" + md_content)
    
    md_path = os.path.join(output_dir, "evaluation_metrics.md")
    with open(md_path, "w") as f:
        f.write(md_content)
    print(f"Evaluation report saved to {md_path}")

if __name__ == "__main__":
    evaluate_system()
