from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

import _globals


class TokenCallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if "/callback" in self.path:
            query = parse_qs(urlparse(self.path).query)
            if "token" in query:
                _globals.auth_token = query["token"][0]
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(
                b"<h1>Authentication Successful!</h1><p>You may close this tab and return to the application.</p>"
            )
