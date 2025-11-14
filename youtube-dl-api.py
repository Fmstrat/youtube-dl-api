#!/usr/bin/env python3
from http.server import BaseHTTPRequestHandler, HTTPServer
import logging
from urllib.parse import parse_qs
import os
import re
from pathlib import Path
from subprocess import Popen, PIPE, STDOUT
from time import sleep

# -----------------------------
# CONFIG / ENVIRONMENT
# -----------------------------
port = int(os.environ.get("PORT", 8080))
hosttoken = os.environ.get("TOKEN", "mytoken")
exthost = os.environ.get("EXTHOST", "http://localhost")
dlformat = os.environ.get("FORMAT", "%(title)s - %(uploader)s - %(id)s.%(ext)s")
youtubecookiefile = os.environ.get("YOUTUBE_COOKIE_FILE", "")

# -----------------------------
# HTML TEMPLATES
# -----------------------------
def success():
    return (
        "Video added successfully."
    )

def failed():
    return (
        "Video failed to add."
    )

def unknown():
    return (
        "Video did not download for unknown reason."
    )

def bookmarklet():
    return (
        "<head><title>Watch Later</title></head>"
        "<body>"
        f"<a href='javascript:location.href=\"{exthost}?token={hosttoken}&url=\"+encodeURIComponent(location.href)'>Watch Later</a>"
        "</body>"
    )

def download_page():
    return (
        "<!DOCTYPE html>"
        "<html>"
        "<head><title>Downloading...</title></head>"
        "<body>"
        "<div id='output'>Starting download...</div>"
        "<script>"
        "   const url = new URL(window.location.href);"
        "   const params = new URLSearchParams(url.search);"
        "   const token = params.get('token');"
        "   const videoUrl = params.get('url');"
        "   const output = document.getElementById('output');"
        "   const eventSource = new EventSource(`/download?token=${token}&url=${videoUrl}`);"
        "   eventSource.onmessage = function(event) {"
        "   output.innerHTML += '<br>' + event.data;"
        "   document.scrollingElement.scrollTo({"
        "       top: document.scrollingElement.scrollHeight,"
        "       behavior: 'smooth'"
        "   });"
        "};"
        "eventSource.onerror = function(event) {"
        "  output.innerHTML += '<br>Connection closed.';"
        "};"
        "</script>"
        "</body>"
        "</html>"
    )


# -----------------------------
# HTTP HANDLER WITH STREAMING
# -----------------------------
class S(BaseHTTPRequestHandler):

    # Send a chunk for chunked-transfer encoding
    def send_chunk(self, text):
        if not isinstance(text, str):
            text = str(text)

        chunk = text + "\n"
        try:
            size = f"{len(chunk):X}\r\n"
            self.wfile.write(size.encode("utf-8"))
            self.wfile.write(chunk.encode("utf-8"))
            self.wfile.write(b"\r\n")
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass

    # Finish chunked stream
    def end_chunks(self):
        self.wfile.write(b"0\r\n\r\n")
        self.wfile.flush()

    def do_GET(self):
        try:
            logging.info("GET %s", self.path)

            clean_path = self.path
            if self.path.startswith('/download?'):
                clean_path = clean_path[len('/download?'):]
            else:
                clean_path = clean_path[2:]
            data = parse_qs(clean_path)
            logging.info("Data variable: %s", data)
            token = data.get("token", [""])[0]

            # -------------------------
            # AUTHENTICATION
            # -------------------------
            if token != hosttoken:
                self.send_response(403)
                self.end_headers()
                return

            # No URL → return bookmarklet
            if "url" not in data:
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(bookmarklet().encode())
                return

            url = data["url"][0]

            # -------------------------
            # HANDLE DOWNLOAD REQUEST
            # -------------------------
            if self.path.startswith("/download"):
                self.handle_download(data)
                return

            # -------------------------
            # SHOW DOWNLOAD PAGE
            # -------------------------
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(download_page().encode())
            return

        except (BrokenPipeError, ConnectionResetError):
            # Client disconnected before finishing
            logging.info("Client disconnected during streaming")
            # subprocess already terminated in inner except
            return

        except Exception as e:
            logging.info("Error: unexpected error during request")
            self.send_error(500)

    def handle_download(self, data):
        try:
            token = data.get("token", [""])[0]
            url = data["url"][0]

            # -------------------------
            # AUTHENTICATION
            # -------------------------
            if token != hosttoken:
                self.send_response(403)
                self.end_headers()
                return

            # -------------------------
            # BEGIN SERVER SENT EVENTS RESPONSE
            # -------------------------
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            def out(msg):
                try:
                    self.wfile.write(f"data: {msg}\n\n".encode("utf-8"))
                    self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    logging.info("Error: out")
                    raise  # will be caught by outer try

            out(f"Starting download for: {url}")

            # -------------------------
            # BUILD COMMAND
            # -------------------------
            cmd = [
                "youtube-dl",
                "--no-playlist",
                "--remote-components", "ejs:npm",
                "-o", dlformat,
                url
            ]

            # Add cookies if needed
            if "cookies" in data and data["cookies"][0] == "true":
                if "youtube.com" in url and youtubecookiefile:
                    cmd += ["--cookies", youtubecookiefile]
                    out("Using YouTube cookies file")

            out("Executing: " + " ".join(cmd))

            # -------------------------
            # RUN PROCESS AND STREAM OUTPUT
            # -------------------------
            process = Popen(cmd, stdout=PIPE, stderr=STDOUT, text=True)

            for line in process.stdout:
                try:
                    print(f'yt-dlp: ' + line.rstrip(), flush=True)
                    out(line.rstrip())
                except (BrokenPipeError, ConnectionResetError):
                    # client disconnected, kill process and exit cleanly
                    logging.info("Error: output")
                    if process.poll() is None:
                        process.terminate()
                    return

            ret = process.wait()

            # -------------------------
            # DETERMINE FINAL STATUS
            # -------------------------
            if ret == 0:
                out("STATUS: SUCCESS")
                final_page = success()
            else:
                out("STATUS: FAILED")
                final_page = failed()

            # Stream final message
            out("")
            out(final_page)

        except (BrokenPipeError, ConnectionResetError):
            # Client disconnected during streaming
            print(f'Client disconnected during streaming', flush=True)
            return

        except Exception as e:
            print(f'Error: unexpected error during request', flush=True)
            self.send_error(500)

# -----------------------------
# SERVER STARTUP
# -----------------------------
def run(server_class=HTTPServer, handler_class=S):
    logging.basicConfig(level=logging.INFO)
    server_address = ("", port)
    httpd = server_class(server_address, handler_class)
    logging.info(f"Starting httpd at port {port}...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    logging.info("Stopping httpd...")

if __name__ == "__main__":
    run()
