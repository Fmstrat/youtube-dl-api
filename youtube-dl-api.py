#!/usr/bin/env python3
from http.server import BaseHTTPRequestHandler, HTTPServer
import logging
from urllib.parse import parse_qs
from time import sleep
import threading
import os
from pathlib import Path

port = 8080
hosttoken = "mytoken"
exthost = "http://localhost"
dlformat = "%(title)s - %(uploader)s - %(id)s.%(ext)s"

if "PORT" in os.environ:
    port = int(os.environ['PORT'])
if "TOKEN" in os.environ:
    hosttoken = os.environ['TOKEN']
if "EXTHOST" in os.environ:
    exthost = os.environ['EXTHOST']
if "FORMAT" in os.environ:
    dlformat = os.environ['FORMAT']

class S(BaseHTTPRequestHandler):
    def _set_response(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_GET(self):
        logging.info("GET request - Path: %s|Headers:%s\n", str(self.path), str(self.headers))
        data = parse_qs(str(self.path)[2:])
        self._set_response()
        if "token" in data:
            token = data["token"][0]
            if token == hosttoken:
                if "url" in data:
                    url = data["url"][0]
                    if '"' not in url:
                        cmd = 'youtube-dl --no-playlist -qs --no-warnings "' + url + '" |grep ERROR'
                        result = os.popen('DATA=$('+cmd+');echo -n $DATA').read()
                        if result == "":
                            cmd = 'youtube-dl --no-playlist -qs --no-warnings --get-filename -o "' + dlformat + '" "' + url + '"'
                            filename = os.popen('DATA=$('+cmd+');echo -n $DATA').read()
                            threading.Thread(target=download, args=(url,)).start()
                            sleep(6)
                            found = False
                            search = os.path.splitext(filename)[0] + "*"
                            if search == "*":
                                self.wfile.write(failed().encode('utf-8'))
                            else:
                                print('Checking for file: ' + search, flush=True)
                                for path in Path("/data/").glob(search):
                                    print('Found file: ' + search, flush=True)
                                    found = True
                                    break
                                if found:
                                    self.wfile.write(success().encode('utf-8'))
                                else:
                                    self.wfile.write(unknown().encode('utf-8'))
                        else:
                            self.wfile.write(failed().encode('utf-8'))
                    else:
                        self.wfile.write("".encode('utf-8'))
                else:
                        self.wfile.write(bookmarklet().encode('utf-8'))
            else:
                self.wfile.write("".encode('utf-8'))
        else:
            self.wfile.write("".encode('utf-8'))

    def do_POST(self):
        self._set_response()
        self.wfile.write("")

def success():
    html = ""
    html += "<head><title>Watch Later</title></head>"
    html += "<body>"
    html += "<center>Video added successfully.</center>"
    html += "</body>"
    return html

def failed():
    html = ""
    html += "<head><title>Watch Later</title></head>"
    html += "<body>"
    html += "<center>Video failed to add.</center>"
    html += "</body>"
    return html

def unknown():
    html = ""
    html += "<head><title>Watch Later</title></head>"
    html += "<body>"
    html += "<center>Video did not download for unknown reason.</center>"
    html += "</body>"
    return html

def bookmarklet():
    html = ""
    html += "<head><title>Watch Later</title></head>"
    html += "<body>"
    html += "<a href='javascript:location.href=\""+exthost+"?token="+hosttoken+"&url=\"+encodeURIComponent(location.href)'>Watch Later</a>"
    html += "</body>"
    return html

def download(url):
    cmd = 'cd /data;youtube-dl --no-playlist -q --no-warnings --no-mtime -o "' + dlformat + '" "' + url + '"'
    os.popen(cmd)

def run(server_class=HTTPServer, handler_class=S):
    logging.basicConfig(level=logging.INFO)
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    logging.info('Starting httpd...\n')
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    logging.info('Stopping httpd...\n')

if __name__ == '__main__':
    run()

