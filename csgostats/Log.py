import base64
import hmac
import pickle
from dataclasses import dataclass
from typing import Union, List


@dataclass
class LogInfo:
    server: str
    map: str
    max_rounds: Union[int, None]
    steam_ids: List[int]
    caller: int = None

    def to_web_request(self, key: bytes, caller: int):
        self.caller = int(caller)
        obj = pickle.dumps(self, protocol=pickle.HIGHEST_PROTOCOL)
        key = hmac.digest(key, obj, digest='sha256')
        b64_key = base64.urlsafe_b64encode(key).decode('ascii')
        b64_obj = base64.urlsafe_b64encode(obj).decode('ascii')
        return {'object': b64_obj, 'key': b64_key}
