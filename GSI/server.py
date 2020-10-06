from http.server import BaseHTTPRequestHandler, HTTPServer
from operator import attrgetter
from threading import Thread
import json
from time import time

from GSI import gamestate
from GSI import payloadparser


class GSIServer(HTTPServer):
    def __init__(self, server_address, auth_token):
        super(GSIServer, self).__init__(server_address, RequestHandler)

        self.auth_token = auth_token
        self.gamestate = gamestate.GameState()
        self.parser = payloadparser.PayloadParser()

        self.running = False

    def start_server(self, timeout: int = 20):
        start = time()
        try:
            thread = Thread(target=self.serve_forever)
            thread.start()
            # first_time = True
            while not self.running:
                if time() - start > timeout and not self.running:
                    print('Failed to start server')
                    break
                elif self.running:
                    break
        except:
            print("\nCould not start server.")

    def get_info(self, target, *argv):
        try:
            if len(argv) == 0:
                state = attrgetter(f"{target}")(self.gamestate)
            elif len(argv) == 1:
                state = attrgetter(f"{target}.{argv[0]}")(self.gamestate)
            elif len(argv) == 2:
                state = attrgetter(f"{target}.{argv[0]}")(self.gamestate)[f"{argv[1]}"]
            else:
                print("\nToo many arguments.")
                return False
            if "object" in str(state):
                return vars(state)
            else:
                return state
        except Exception as E:
            print('')
            print(E)
            return False


class RequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers["Content-Length"])
        body = self.rfile.read(length).decode("utf-8")

        payload = json.loads(body)

        if not self.authenticate_payload(payload):
            print("\nauth_token does not match.")
            return False
        else:
            self.server.running = True

        self.server.parser.parse_payload(payload, self.server.gamestate)

    def authenticate_payload(self, payload):
        if "auth" in payload and "token" in payload["auth"]:
            return payload["auth"]["token"] == self.server.auth_token
        else:
            return False
