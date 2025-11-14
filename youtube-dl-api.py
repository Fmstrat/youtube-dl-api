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
            # print(f'Error: send_chunk', flush=True)
            # raise
            pass

    # Finish chunked stream
    def end_chunks(self):
        self.wfile.write(b"0\r\n\r\n")
        self.wfile.flush()

    def do_GET(self):
        try:
            logging.info("GET %s", self.path)

            data = parse_qs(self.path[2:])  # strip /?
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
            # BEGIN STREAMING RESPONSE
            # -------------------------
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()

            def out(msg):
                try:
                    self.send_chunk(msg)
                except (BrokenPipeError, ConnectionResetError):
                    print(f'Error: out', flush=True)
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
                    print(f'yt-dlp: ' + line.rstrip())
                    out(line.rstrip())
                except (BrokenPipeError, ConnectionResetError):
                    # client disconnected, kill process and exit cleanly
                    print(f'Error: output', flush=True)
                    # if process.poll() is None:
                    #     process.terminate()
                    # return

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

            # Stream final HTML
            out("")
            out(final_page)

            # Close chunked stream
            self.end_chunks()

        except (BrokenPipeError, ConnectionResetError):
            # Client disconnected before finishing
            print(f'Client disconnected during streaming', flush=True)
            # subprocess already terminated in inner except
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
