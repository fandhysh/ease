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
    try:
        with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
            ydl.extract_info(url, download=False)
        return True
    except:
        return False


@app.route("/download", methods=["POST"])
def download():
    data = request.get_json()
    url = data.get("url")
    download_id = data.get("id")
    format_type = data.get("format", "mp4")

    if not url or not download_id:
        return jsonify({"error": "URL dan ID diperlukan"}), 400

    if download_id in download_processes:
        return jsonify({"error": "Download sedang berlangsung"}), 400

    output_ext = "mp4" if format_type == "mp4" else "mp3"

    # Perbaikan Logika Command
    # Tambahkan --no-playlist agar tidak mengunduh seluruh list YouTube Mix
    if format_type == "mp4":
        command = [
            "yt-dlp",
            "--no-playlist",  # <--- TAMBAHKAN INI
            "-o",
            f"{DOWNLOAD_FOLDER}/%(title)s.%(ext)s",
            "-f",
            "bestvideo+bestaudio/best",
            "--merge-output-format",
            "mp4",
            "--downloader",
            "aria2c",
            "--downloader-args",
            "aria2c:-x 16 -s 16 -k 1M",
            url,
        ]
    else:
        command = [
            "yt-dlp",
            "--no-playlist",  # <--- TAMBAHKAN INI
            "-o",
            f"{DOWNLOAD_FOLDER}/%(title)s.%(ext)s",
            "-f",
            "bestaudio",
            "--extract-audio",
            "--audio-format",
            "mp3",
            "--downloader",
            "aria2c",
            "--downloader-args",
            "aria2c:-x 16 -s 16 -k 1M",
            url,
        ]

    try:
        # Menjalankan proses di background agar bisa di-cancel nanti
        if sys.platform == "win32":
            process = subprocess.Popen(
                command, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            )
        else:
            process = subprocess.Popen(command, preexec_fn=os.setsid)

        download_processes[download_id] = process
        process.wait()  # Menunggu proses selesai

        # Mencari file hasil download
        files = glob.glob(f"{DOWNLOAD_FOLDER}/*.{output_ext}")
        if not files:
            files = glob.glob(
                f"{DOWNLOAD_FOLDER}/*.mkv"
            )  # Backup jika format merge meleset

        latest_file = max(files, key=os.path.getctime) if files else None

        if latest_file:
            downloaded_files[download_id] = latest_file
            return jsonify(
                {
                    "message": "Download selesai",
                    "id": download_id,
                    "file": os.path.basename(latest_file),
                }
            )

        return jsonify({"error": "Gagal mengunduh video"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if download_id in download_processes:
            del download_processes[download_id]


@app.route("/files/<download_id>", methods=["GET"])
def get_file(download_id):
    if download_id not in downloaded_files:
        return jsonify({"error": "File tidak ditemukan"}), 404
    return send_file(downloaded_files[download_id], as_attachment=True)


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

        process.wait()
    except Exception as e:
        return jsonify({"error": f"Gagal membatalkan: {str(e)}"}), 500

    if download_id in download_processes:
        del download_processes[download_id]

    return jsonify({"message": "Download dibatalkan"})


if __name__ == "__main__":
    # Pastikan host 0.0.0.0 agar bisa diakses lewat NAT VPS
    app.run(host="0.0.0.0", port=10000)
