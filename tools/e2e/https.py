import http.server, ssl, os
os.chdir("/tmp/e2e")
s = http.server.HTTPServer(("127.0.0.1", 8443), http.server.SimpleHTTPRequestHandler)
ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); ctx.load_cert_chain("c.pem", "k.pem")
s.socket = ctx.wrap_socket(s.socket, server_side=True); s.serve_forever()
