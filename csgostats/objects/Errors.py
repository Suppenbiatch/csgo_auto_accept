class PlayerNotFoundError(BaseException):
    def __init__(self, steam_id):
        super().__init__(f'{steam_id} not found')
        self.id = steam_id


class UnknownProfileError(BaseException):
    def __init__(self, steam_id):
        super().__init__(f'{steam_id} has an unknown csgostats profile structure')
