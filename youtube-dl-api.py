#!/usr/bin/env python3
from http.server import BaseHTTPRequestHandler, HTTPServer
import logging
from urllib.parse import parse_qs
from os import popen, environ
import threading

port = int(environ['PORT'])
hosttoken = environ['TOKEN']
exthost = environ['EXTHOST']

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
                        cmd = 'youtube-dl -qs --no-warnings "' + url + '" |grep ERROR'
                        result = popen('DATA=$('+cmd+');echo -n $DATA').read()
                        if result == "":
                            threading.Thread(target=download, args=(url,)).start()
                            self.wfile.write(success().encode('utf-8'))
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

def bookmarklet():
    html = ""
    html += "<head><title>Watch Later</title></head>"
    html += "<body>"
    html += "<a href='javascript:location.href=\""+exthost+"?token="+hosttoken+"&url=\"+encodeURIComponent(location.href)'>Watch Later</a>"
    html += "</body>"
    return html

def download(url):
    cmd = 'cd /data;youtube-dl -q --no-warnings --no-mtime -o "%(title)s - %(uploader)s - %(id)s.%(ext)s" "' + url + '"'
    popen(cmd)

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
    popen("pip3 install youtube-dl --upgrade > /dev/null")
    run()
