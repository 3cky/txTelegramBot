
class MessagePlugin(object):
    priority = 100

    def __init__(self):
        self._bot = None

    def startPlugin(self):
        pass

    def stopPlugin(self):
        pass

    def on_update(self, update):
        pass

    def send_method(self, method):
        return self._bot is not None and self._bot.send_method(method)
