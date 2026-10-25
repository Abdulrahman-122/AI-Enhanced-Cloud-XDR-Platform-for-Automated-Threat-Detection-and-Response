"""
demo_server.py  --  a tiny, completely HARMLESS local test site.

It imitates the *behaviours* a real scam page shows so you can watch the analyzer
catch them without ever visiting a real malicious site:

  http://localhost:8001/safe     a well-configured, boring page
  http://localhost:8001/gift     a fake "free gift card" page that
        - redirects through several hops (and across two "domains": localhost and 127.0.0.1)
        - loads an ancient jQuery 1.12.4 stub
        - loads a stub whose text contains a miner brand name (it does nothing)
        - runs eval(atob(...)) on a string that just prints to the console
        - has a hidden 0x0 iframe
        - has a password form that posts to a different origin over plain HTTP
        - shows a scareware-style alert()
        - auto-downloads "giftcard.exe" which is just a text file

Nothing here is real malware. Run:   python demo_server.py
"""
import base64

from flask import Flask, Response, redirect, request

app = Flask(__name__, static_folder=None)
PORT = 8001

SAFE_HEADERS = {
    "Content-Security-Policy": "default-src 'self'; style-src 'self' 'unsafe-inline'",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
}


@app.route("/")
def index():
    return """<h1>Demo targets</h1><ul>
    <li><a href="/safe">/safe</a> - clean page</li>
    <li><a href="/gift">/gift</a> - fake scam page (harmless)</li></ul>"""


@app.route("/safe")
def safe():
    html = """<!doctype html><html><head><title>Acme Docs</title>
    <style>body{font-family:sans-serif;max-width:640px;margin:60px auto}</style></head>
    <body><h1>Acme Documentation</h1><p>A plain, well-behaved page with sensible security headers.</p></body></html>"""
    resp = Response(html, mimetype="text/html", headers=SAFE_HEADERS)
    resp.set_cookie("sid", "abc123", httponly=True, samesite="Lax")
    return resp


@app.route("/gift")
def gift():
    return redirect("http://127.0.0.1:%d/offer?step=1" % PORT, code=302)


@app.route("/offer")
def offer():
    if request.args.get("step") == "1":
        return redirect("/offer?step=2", code=302)
    return redirect("/landing", code=302)


@app.route("/landing")
def landing():
    payload = base64.b64encode(b"console.log('demo: decoded payload ran')").decode()
    html = """<!doctype html><html><head><title>CONGRATULATIONS - Claim your $500 gift card</title>
    <style>body{font-family:sans-serif;background:#fffbe6;max-width:560px;margin:50px auto;text-align:center}</style>
    <script src="http://localhost:%(port)d/static/jquery-1.12.4.min.js"></script>
    <script src="http://localhost:%(port)d/static/miner.js"></script>
    </head><body>
    <h1>You won a $500 gift card!</h1>
    <p>Log in to verify your account and claim your prize.</p>
    <form action="http://localhost:%(port)d/collect" method="post">
      <input name="email" placeholder="Email"><br>
      <input name="password" type="password" placeholder="Password"><br>
      <button>Claim now</button>
    </form>
    <iframe src="http://localhost:%(port)d/pixel" width="0" height="0" style="border:0"></iframe>
    <script>
      eval(atob("%(payload)s"));
      alert("WARNING: Your device may be infected! Call support immediately.");
      var a = document.createElement('a');
      a.href = '/giftcard.exe'; a.download = 'giftcard.exe';
      document.body.appendChild(a); a.click();
    </script></body></html>""" % {"port": PORT, "payload": payload}
    resp = Response(html, mimetype="text/html")
    resp.set_cookie("tracker", "demo-visitor-1")  # no flags on purpose
    return resp


@app.route("/static/jquery-1.12.4.min.js")
def jquery_stub():
    return Response("/*! jQuery v1.12.4 | (c) jQuery Foundation | jquery.org/license */\nwindow.jQuery=function(){};",
                    mimetype="application/javascript")


@app.route("/static/miner.js")
def miner_stub():
    return Response("/* harmless demo stub */\nvar demo = {brand: 'CoinHive'};\n"
                    "console.log('demo: a real miner would start here');",
                    mimetype="application/javascript")


@app.route("/giftcard.exe")
def fake_exe():
    return Response("This is a harmless text file pretending to be an installer.\n",
                    mimetype="application/octet-stream",
                    headers={"Content-Disposition": 'attachment; filename="giftcard.exe"'})


@app.route("/collect", methods=["POST"])
def collect():
    return ("", 204)


@app.route("/pixel")
def pixel():
    return "<!doctype html><title>pixel</title>"


if __name__ == "__main__":
    print("Demo site on http://localhost:%d  (/safe and /gift)" % PORT)
    app.run(host="127.0.0.1", port=PORT, threaded=True)
