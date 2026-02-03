from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp
import os
import subprocess
import glob
import signal
import sys

app = Flask(__name__)
CORS(app)

DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

download_processes = {}  # Menyimpan proses download aktif
downloaded_files = {}  # Menyimpan path file hasil download


def is_supported_url(url):
    """Memeriksa apakah URL didukung oleh yt-dlp"""
    try:
        with yt_dlp.YoutubeDL() as ydl:
            ydl.extract_info(url, download=False)
        return True
    except yt_dlp.utils.DownloadError:
        return False


@app.route("/download", methods=["POST"])
def download():
    data = request.get_json()
    url = data.get("url")
    download_id = data.get("id")
    format_type = data.get("format", "mp4")  # Default ke MP4 jika tidak dipilih

    if not url or not download_id:
        return jsonify({"error": "URL dan ID diperlukan"}), 400

    if not is_supported_url(url):
        return jsonify({"error": "URL tidak didukung"}), 400

    if download_id in download_processes:
        return jsonify({"error": "Download sedang berlangsung"}), 400

    output_ext = "mp4" if format_type == "mp4" else "mp3"
    format_flag = "bestvideo+bestaudio/best" if format_type == "mp4" else "bestaudio"

    output_path = f"{DOWNLOAD_FOLDER}/%(title)s.{output_ext}"
    command = ["yt-dlp", "-o", output_path, "-f", format_flag, url]

    try:
        if sys.platform == "win32":
            process = subprocess.Popen(
                command, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            )
        else:
            process = subprocess.Popen(command, preexec_fn=os.setsid)

        download_processes[download_id] = process
        process.wait()  # Tunggu hingga proses selesai

        files = glob.glob(f"{DOWNLOAD_FOLDER}/*.{output_ext}")
        latest_file = max(files, key=os.path.getctime) if files else None

        if latest_file:
            downloaded_files[download_id] = latest_file
            return jsonify(
                {"message": "Download selesai", "id": download_id, "file": latest_file}
            )

        return jsonify({"error": "Gagal mengunduh video"}), 500
    except Exception as e:
        return jsonify({"error": f"Terjadi kesalahan: {str(e)}"}), 500


@app.route("/files/<download_id>", methods=["GET"])
def get_file(download_id):
    if download_id not in downloaded_files:
        return jsonify({"error": "File tidak ditemukan"}), 404

    file_path = downloaded_files[download_id]
    return send_file(file_path, as_attachment=True)


@app.route("/cancel", methods=["POST"])
def cancel_download():
    data = request.get_json()
    download_id = data.get("id")

    if not download_id or download_id not in download_processes:
        return jsonify({"error": "ID tidak valid atau tidak ada download aktif"}), 400

    process = download_processes[download_id]

    try:
        if sys.platform == "win32":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(process.pid)], check=True
            )
        else:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)

        process.wait()  # Tunggu hingga proses benar-benar berhenti
    except Exception as e:
        return jsonify({"error": f"Gagal membatalkan: {str(e)}"}), 500

    del download_processes[download_id]  # Hapus dari daftar proses aktif
    return jsonify({"message": "Download dibatalkan"})


if __name__ == "__main__":
    app.run(debug=True, port=60040)
