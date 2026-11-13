"""Relé del control remoto de la presentación (solo biblioteca estándar, sin dependencias).

La presentación publica su estado (diapositiva actual y notas) y las páginas de control publican
órdenes (siguiente, anterior, ir a). Todo viaja por *long polling*: el cliente pide y el servidor
retiene la respuesta hasta ~20 s o hasta que haya algo nuevo. Se usa esto y no SSE porque los
túneles rápidos de Cloudflare (trycloudflare.com) retienen los eventos y nunca llegan.

  GET  /estado?id=I&v=V&f=F   (controles) responde cuando cambia la versión (V) o la firma de conectados (F)
  GET  /ordenes?id=I&desde=N  (presentación) responde cuando hay órdenes con id > N
  POST /estado                la presentación publica su estado
  POST /orden                 un control manda una orden

Todas las peticiones llevan la cabecera X-Clave. La clave sale de CONTROL_CLAVE; si no está definida
se genera una al azar y se imprime en el log. "Conectado" = preguntó en los últimos 35 s.
"""

from __future__ import annotations

import hmac
import json
import os
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

CLAVE = os.getenv("CONTROL_CLAVE") or secrets.token_urlsafe(6)
PUERTO = int(os.getenv("PUERTO", "8091"))
ACCIONES = {"siguiente", "anterior", "ir"}
ESPERA_MAX = 20      # segundos que se retiene un pedido largo
VENTANA_VISTO = 35   # un cliente cuenta como conectado si preguntó en los últimos 35 s
INSTANCIA = secrets.token_hex(4)  # cambia al reiniciar el relé: la presentación vuelve a publicar su estado

_cond = threading.Condition()
_estado: dict | None = None
_version = 0
_ordenes: list[dict] = []
_sig_orden = int(time.time())  # crece siempre, también entre reinicios
_vistos: dict[str, dict[str, float]] = {"control": {}, "presentador": {}}
# Presentador activo: el último que se conectó. Si hay dos pestañas de presentación abiertas, solo cuenta
# el estado de esta; así el control no salta entre dos posiciones distintas.
_activo: str | None = None


def _marcar(rol: str, ident: str) -> None:
    """Anota que este cliente está vivo (con _cond tomado). Avisa a los demás si es nuevo."""
    nuevo = ident not in _vistos[rol]
    _vistos[rol][ident] = time.time()
    if nuevo:
        _cond.notify_all()


def _contar(rol: str) -> int:
    ahora = time.time()
    vistos = _vistos[rol]
    for k in [k for k, t in vistos.items() if ahora - t > VENTANA_VISTO]:
        del vistos[k]
    return len(vistos)


def _entero(valor: str, defecto: int) -> int:
    try:
        return int(valor)
    except ValueError:
        return defecto


class Manejador(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):  # sin ruido por pedido
        pass

    def _clave_ok(self) -> bool:
        candidata = self.headers.get("X-Clave") or ""
        return hmac.compare_digest(candidata.encode(), CLAVE.encode())

    def _responder(self, codigo: int, cuerpo: dict | None = None) -> None:
        datos = json.dumps(cuerpo or {}, ensure_ascii=False).encode()
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(datos)))
        self.end_headers()
        self.wfile.write(datos)

    def do_GET(self):
        partes = urlsplit(self.path)
        q = {k: v[0] for k, v in parse_qs(partes.query).items()}
        if partes.path not in ("/estado", "/ordenes"):
            return self._responder(404, {"error": "no existe"})
        if not self._clave_ok():
            return self._responder(401, {"error": "clave incorrecta"})
        ident = (q.get("id") or "anonimo")[:64]
        try:
            if partes.path == "/estado":
                self._estado_largo(ident, _entero(q.get("v", "-1"), -1), q.get("f", ""))
            else:
                self._ordenes_largo(ident, _entero(q.get("desde", "-1"), -1))
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _estado_largo(self, ident: str, version: int, firma: str) -> None:
        fin = time.time() + ESPERA_MAX
        with _cond:
            _marcar("control", ident)
            while True:
                actual = f"{_contar('control')}-{_contar('presentador')}"
                if _version != version or actual != firma or time.time() >= fin:
                    break
                _cond.wait(timeout=2)
                _vistos["control"][ident] = time.time()
            cuerpo = {"version": _version, "firma": actual, "estado": _estado,
                      "conectados": _contar("control"), "presentador": _contar("presentador") > 0}
        self._responder(200, cuerpo)

    def _ordenes_largo(self, ident: str, desde: int) -> None:
        global _activo
        fin = time.time() + ESPERA_MAX
        with _cond:
            _marcar("presentador", ident)
            if desde < 0:
                _activo = ident  # la presentación que acaba de abrirse pasa a ser la que manda
            # desde < 0: primera consulta, solo informa el último id para no repetir órdenes viejas
            while desde >= 0 and _sig_orden <= desde and time.time() < fin:
                _cond.wait(timeout=2)
                _vistos["presentador"][ident] = time.time()
            nuevas = [o for o in _ordenes if o["id"] > desde] if desde >= 0 else []
            cuerpo = {"instancia": INSTANCIA, "ultimo": _sig_orden, "ordenes": nuevas}
        self._responder(200, cuerpo)

    def do_POST(self):
        global _estado, _version, _sig_orden, _ordenes, _activo
        if not self._clave_ok():
            return self._responder(401, {"error": "clave incorrecta"})
        largo = _entero(self.headers.get("Content-Length") or "0", 0)
        if largo > 256_000:
            return self._responder(413, {"error": "demasiado grande"})
        try:
            cuerpo = json.loads(self.rfile.read(largo) or b"{}")
        except json.JSONDecodeError:
            return self._responder(400, {"error": "JSON inválido"})

        if self.path == "/estado":
            with _cond:
                if _activo is None:
                    _activo = cuerpo.get("id")  # relé recién reiniciado: manda quien publique primero
                elif cuerpo.get("id") != _activo:
                    return self._responder(200, {"ok": True, "ignorado": True})
                _estado = cuerpo
                _version += 1
                _cond.notify_all()
        elif self.path == "/orden":
            if cuerpo.get("accion") not in ACCIONES:
                return self._responder(400, {"error": "acción inválida"})
            with _cond:
                _sig_orden += 1
                _ordenes = (_ordenes + [{"id": _sig_orden, "accion": cuerpo["accion"],
                                         "indice": cuerpo.get("indice")}])[-50:]
                _cond.notify_all()
        else:
            return self._responder(404, {"error": "no existe"})
        self._responder(200, {"ok": True})


if __name__ == "__main__":
    print(f"Control remoto listo en el puerto {PUERTO}. Clave: {CLAVE}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PUERTO), Manejador).serve_forever()
