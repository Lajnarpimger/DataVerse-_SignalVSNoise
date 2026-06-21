import os
import json
from http.server import SimpleHTTPRequestHandler, HTTPServer

class ReportHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        # API Endpoint to fetch and sort all JSON reports
        if self.path == '/api/reports':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            reports = []
            outputs_dir = os.path.join(os.path.dirname(__file__), 'outputs')
            if os.path.exists(outputs_dir):
                for filename in os.listdir(outputs_dir):
                    if filename.endswith('_score.json'):
                        with open(os.path.join(outputs_dir, filename), 'r') as f:
                            try:
                                reports.append(json.load(f))
                            except:
                                pass
                                
            # Satisfy the "ranked list" requirement: sort descending by score
            reports.sort(key=lambda x: x.get('final_utility_score', 0), reverse=True)
            self.wfile.write(json.dumps(reports).encode())
        elif self.path.startswith('/api/xml/'):
            report_id = self.path.split('/')[-1]
            # Extract the numeric part (e.g., from 'RPT-2026-000030' to '000030')
            id_num = report_id.split('-')[-1] if '-' in report_id else report_id
            filename = f"report_{id_num}.xml"
            
            xml_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'code', 'data', 'reports', filename))
            if os.path.exists(xml_path):
                self.send_response(200)
                self.send_header('Content-type', 'application/xml')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                with open(xml_path, 'r', encoding='utf-8') as f:
                    self.wfile.write(f.read().encode('utf-8'))
            else:
                self.send_response(404)
                self.end_headers()
        else:
            # Route root to the UI folder
            if self.path == '/':
                self.path = '/ui/index.html'
            super().do_GET()

if __name__ == '__main__':
    port = 8080
    server = HTTPServer(('', port), ReportHandler)
    print(f"UI Server running on http://localhost:{port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
