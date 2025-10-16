from flask import Flask, send_from_directory
import os

app = Flask(__name__)

@app.route("/")
def home():
    return "Crawler is running!"

@app.route("/download/<filename>")
def download_file(filename):
    return send_from_directory("data", filename)
    
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
