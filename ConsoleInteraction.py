import random
import telnetlib
import threading
import time
import queue
from typing import Optional


# needs csgo launch option:
# -netconport [port]


class TelNetConsoleReader(threading.Thread):
    def __init__(self, ip: str, port: int):
        super(TelNetConsoleReader, self).__init__()
        self.received = queue.Queue()
        self.send_queue = queue.Queue()
        self.daemon = True
        self.name = 'ConsoleReader'
        self.ip = ip
        self.port = port
        self.tl = None
        self.closed: Optional[bool] = None

    @staticmethod
    def create_msg(message: str) -> bytes:
        msg = message.strip().encode('utf-8')
        return msg + b'\n'

    def close(self):
        self.closed = True

    def send(self, message: str):
        self.send_queue.put(message)

    def run(self) -> None:
        try:
            self.tl = telnetlib.Telnet(self.ip, self.port)
        except ConnectionRefusedError:
            self.closed = True
            return

        self.closed = False

        while True:
            try:
                data = self.tl.read_very_eager()
            except EOFError:
                self.closed = True
                break

            if data != b'':
                text = data.decode('utf-8', errors='replace').strip().splitlines()
                for line in text:
                    self.received.put(line)

            while not self.send_queue.empty():
                send = self.send_queue.get()
                self.tl.write(self.create_msg(send))

            if self.closed is True:
                self.tl.close()
                self.tl = None
                break
            time.sleep(0.1)
        return


def main():
    tl_thread = TelNetConsoleReader('127.0.0.1', 1234)
    tl_thread.start()

    while True:
        if tl_thread.closed is False:
            break
        elif tl_thread.closed is True:
            print(f'Failed to connect to the csgo client')
            return
        time.sleep(0.2)

    while True:
        while not tl_thread.received.empty():
            message = tl_thread.received.get_nowait()
            print(message)
        if random.randint(0, 20) == 1:
            tl_thread.send('status')
            print('send status command')
        time.sleep(1)


if __name__ == '__main__':
    main()
