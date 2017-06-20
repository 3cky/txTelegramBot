# -*- coding: utf-8 -*-

from twisted.application import service

from twisted.internet import defer
from twisted.python import log

from TelegramBot.plugin import UpdatePlugin
from pyplugin import PluginLoader


class BotService(service.Service):
    _client = None
    _plugins = None

    def __init__(self, plugin_filespec=None, plugins=[]):
        self._plugins = plugins
        self._plugin_filespec = plugin_filespec

    @defer.inlineCallbacks
    def startService(self):
        self._client = self.parent.getServiceNamed('telegrambot_client')

        if self._plugin_filespec is not None:
            plugins = PluginLoader(UpdatePlugin, self._plugin_filespec)
            log.msg([p for p in plugins])
            self._plugins.extend([p() for p in plugins])

        self._plugins.sort(key=lambda p: p.priority)

        for plugin in self._plugins:
            plugin._bot = self
            yield defer.maybeDeferred(plugin.startPlugin)

    @defer.inlineCallbacks
    def stopService(self):
        for plugin in self._plugins:
            yield defer.maybeDeferred(plugin.stopPlugin)

    @defer.inlineCallbacks
    def on_update(self, update):
        for plugin in self._plugins:
            handled = yield defer.maybeDeferred(plugin.on_update, update)
            if handled:
                break

    def send_method(self, method):
        return self._client.send_method(method)
