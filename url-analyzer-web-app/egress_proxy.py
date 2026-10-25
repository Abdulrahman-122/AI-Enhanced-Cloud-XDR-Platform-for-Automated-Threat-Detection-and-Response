"""
egress_proxy.py  --  the "restricted network" of the sandbox, in ~100 lines.

A tiny local forward proxy that the detonation browser is forced to use. For EVERY
connection (first request, each redirect hop, sub-resources, WebSockets) it:

  1. resolves the destination hostname itself,
  2. refuses the connection if ANY resolved address is non-public
     (private ranges, loopback, link-local/cloud-metadata 169.254.x.x, ...),
  3. connects to the exact IP it validated  ->  immune to DNS-rebinding tricks.

Why not just check URLs inside the browser? Because HTTP redirects are followed by
the browser's network stack and never reach Playwright's route handler, so a public
URL could redirect straight to http://169.254.169.254/ unnoticed. A proxy sees
everything.

In Kubernetes you would enforce the same rule with a NetworkPolicy / egress gateway;
this proxy gives you identical behaviour on a plain VM or laptop.
"""
import asyncio
import ipaddress
import socket
import threading
from urllib.parse import urlsplit, urlunsplit


def default_blocked(host, ip):
    a = ipaddress.ip_address(ip.split("%")[0])
    return (not a.is_global) or a.is_multicast


class EgressProxy:
    def __init__(self, blocked=None):
        self.blocked = blocked or default_blocked
        self.blocked_log = []          # URLs/hosts that were refused
        self.port = None
        self._loop = None
        self._server = None
        self._thread = None
        self._ready = threading.Event()

    # ---- lifecycle -------------------------------------------------------
    def start(self):
        def run():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._server = self._loop.run_until_complete(asyncio.start_server(self._handle, "127.0.0.1", 0))
            self.port = self._server.sockets[0].getsockname()[1]
            self._ready.set()
            self._loop.run_forever()

        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()
        if not self._ready.wait(5):
            raise RuntimeError("egress proxy failed to start")
        return self

    async def _shutdown(self):
        self._server.close()
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        asyncio.get_running_loop().stop()

    def stop(self):
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._shutdown(), self._loop)
            self._thread.join(timeout=3)
            if not self._loop.is_running():
                self._loop.close()

    # ---- request handling ------------------------------------------------
    @staticmethod
    async def _pipe(src, dst):
        try:
            while True:
                data = await src.read(65536)
                if not data:
                    break
                dst.write(data)
                await dst.drain()
        except Exception:
            pass
        finally:
            try:
                dst.close()
            except Exception:
                pass

    async def _handle(self, reader, writer):
        async def refuse(code, text, note=None):
            if note:
                self.blocked_log.append(note[:300])
            try:
                writer.write(("HTTP/1.1 %d %s\r\nConnection: close\r\nContent-Length: 0\r\n\r\n" % (code, text)).encode())
                await writer.drain()
            except Exception:
                pass
            writer.close()

        try:
            head = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), 15)
            lines = head.decode("latin-1").split("\r\n")
            method, target, _ = lines[0].split(" ", 2)
            if method.upper() == "CONNECT":
                host, _, port = target.rpartition(":")
                port, url_form = int(port), "https://%s" % target
            else:
                u = urlsplit(target)
                host, port, url_form = u.hostname, u.port or 80, target
            host = (host or "").strip("[]")
            if not host:
                return await refuse(400, "Bad Request")
        except Exception:
            writer.close()
            return

        try:
            infos = await asyncio.get_running_loop().getaddrinfo(host, port, type=socket.SOCK_STREAM)
            ips = [i[4][0] for i in infos]
        except Exception:
            return await refuse(502, "Bad Gateway")

        if any(self.blocked(host, ip) for ip in ips):
            return await refuse(403, "Forbidden", "BLOCKED %s -> %s" % (url_form, ",".join(sorted(set(ips)))))

        try:
            up_r, up_w = await asyncio.open_connection(ips[0], port)   # connect to the IP we validated
        except Exception:
            return await refuse(502, "Bad Gateway")

        if method.upper() == "CONNECT":
            writer.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
            await writer.drain()
        else:
            # plain HTTP: send in origin-form, one request per connection
            u = urlsplit(target)
            path = urlunsplit(("", "", u.path or "/", u.query, ""))
            hdrs = [l for l in lines[1:] if l and not l.lower().startswith(("proxy-connection:", "connection:"))]
            up_w.write(("%s %s HTTP/1.1\r\n" % (method, path) + "\r\n".join(hdrs + ["Connection: close", "", ""])).encode("latin-1"))
            await up_w.drain()

        await asyncio.gather(self._pipe(reader, up_w), self._pipe(up_r, writer))
