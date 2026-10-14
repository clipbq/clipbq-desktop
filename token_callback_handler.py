from http.server import BaseHTTPRequestHandler


class TokenCallbackHandler(BaseHTTPRequestHandler):
    auth_callback_token = None

    def do_GET(self):
        global auth_callback_token
        if "/callback" in self.path:
            from urllib.parse import urlparse, parse_qs

            query = parse_qs(urlparse(self.path).query)
            if "token" in query:
                auth_callback_token = query["token"][0]
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(
                b"<h1>Authentication Successful!</h1><p>You may close this tab and return to the application.</p>"
            )
