# -*- coding: utf-8 -*-


class UpdatePlugin(object):
    priority = 100

    def __init__(self):
        self._bot = None

    def startPlugin(self):
        pass

    def stopPlugin(self):
        pass

    def on_update(self, update):
        pass
