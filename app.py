from flask import Flask, send_from_directory, render_template_string
import os

SAVE_DIR = "data"
app = Flask(__name__)

@app.route("/")
def home():
    files = [f for f in os.listdir(SAVE_DIR) if f.endswith(".sql")]
    files.sort(reverse=True)
    
    html = """
    <html>
    <head>
        <title>Reddit SQL Exporter</title>
        <style>
            body { font-family: Arial; text-align: center; margin: 40px; }
            table { margin: 0 auto; border-collapse: collapse; }
            th, td { border: 1px solid #ccc; padding: 8px 12px; }
            th { background-color: #f2f2f2; }
            a { text-decoration: none; color: #007BFF; }
            a:hover { text-decoration: underline; }
        </style>
    </head>
    <body>
        <h2>Reddit SQL Exporter</h2>
        <p>Hệ thống tự crawl và lưu dữ liệu Reddit. Click để tải file SQL.</p>
        <table>
            <tr><th>File SQL</th><th>Download</th></tr>
            {% for f in files %}
            <tr>
                <td>{{ f }}</td>
                <td><a href="/download/{{ f }}">Tải xuống</a></td>
            </tr>
            {% endfor %}
        </table>
    </body>
    </html>
    """
    return render_template_string(html, files=files)

@app.route("/download/<filename>")
def download_file(filename):
    return send_from_directory(SAVE_DIR, filename, as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
