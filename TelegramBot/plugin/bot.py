# -*- coding: utf-8 -*-
import time
import six

from twisted.python import log, failure
from twisted.internet import reactor, defer

from TelegramBot.plugin import UpdatePlugin

from TelegramBotAPI.types import sendMessage
from TelegramBotAPI.types.methods import Method


class BotPlugin(UpdatePlugin):

    MESSAGE_SEND_DELAY = 0.5  # message send delay (in seconds)

    def __init__(self):
        UpdatePlugin.__init__(self)
        self._last_message_send = 0.

    @defer.inlineCallbacks
    def send_method(self, method):
        if self._bot is None:
            defer.returnValue(False)

        # throttle method send, if needed
        last_message_send_elapsed = time.time() - self._last_message_send
        if last_message_send_elapsed < self.MESSAGE_SEND_DELAY:
            yield self.sleep(self.MESSAGE_SEND_DELAY - last_message_send_elapsed)
        self._last_message_send = time.time()

        # do method send
        res = yield self._bot.send_method(method)
        defer.returnValue(res)

    @defer.inlineCallbacks
    def send_message(self, chat_id, message):
        # do message send with markdown enabled
        m = sendMessage()
        m.chat_id = chat_id
        m.text = message
        m.parse_mode = 'Markdown'
        m.disable_web_page_preview = True
        res = yield self.send_method(m)
        defer.returnValue(res)

    @staticmethod
    def sleep(secs):
        d = defer.Deferred()
        reactor.callLater(secs, d.callback, None)  # @UndefinedVariable
        return d

    @defer.inlineCallbacks
    def on_update(self, update):
        update_handled = False

        if hasattr(update, 'message'):
            message = getattr(update, 'message')
            update_handled = yield self.on_message(message)
        elif hasattr(update, 'inline_query'):
            inline_query = getattr(update, 'inline_query')
            update_handled = yield self.on_inline_query(inline_query)
        elif hasattr(update, 'callback_query'):
            callback_query = getattr(update, 'callback_query')
            update_handled = yield self.on_callback_query(callback_query)

        defer.returnValue(update_handled)

    @defer.inlineCallbacks
    def on_message(self, msg):
        if not hasattr(msg, 'text') or not hasattr(msg, 'entities'):
            defer.returnValue(False)

        cmd_entity = next((e for e in getattr(msg, 'entities') if e.type == 'bot_command'), None)

        if cmd_entity is None:
            defer.returnValue(False)

        cmd_start = cmd_entity.offset+1
        cmd_end = cmd_start+cmd_entity.length-1

        cmd = msg.text[cmd_start:cmd_end]
        cmd_args = msg.text[cmd_end:].strip()

        amp_index = cmd.find('@')
        cmd = cmd if (amp_index < 0) else cmd[:amp_index]

        if not cmd_args:
            cmd_args = None

        try:
            cmd_result = yield self.on_command(cmd, cmd_args, msg)
        except Exception as e:
            f = failure.Failure()
            log.err(f, 'Error while handling command \'%s %s\': %s' %
                    (cmd, cmd_args if cmd_args else '', e,))
            cmd_result = 'ERROR: [%s] (see log file for details)' % str(e)

        message_handled = True

        if isinstance(cmd_result, six.string_types):
            yield self.send_message(msg.chat.id, cmd_result)
        elif isinstance(cmd_result, Method):
            yield self.send_method(cmd_result)
        else:
            message_handled = False

        defer.returnValue(message_handled)

    @defer.inlineCallbacks
    def on_command(self, cmd, cmd_args=None, cmd_msg=None):
        cmd_method = "on_command_" + cmd
        if hasattr(self, cmd_method):
            cmd_result = yield defer.maybeDeferred(getattr(self, cmd_method), cmd_args, cmd_msg)
        else:
            cmd_result = yield defer.maybeDeferred(self.on_unknown_command, cmd)

        defer.returnValue(cmd_result)

    def on_unknown_command(self, cmd):
        return "Unknown command: /%s" % cmd

    def on_command_start(self, _cmd_args, _cmd_msg):
        return "Hello, I'm *Twisted Telegram bot*."

    @defer.inlineCallbacks
    def on_inline_query(self, _inline_query):
        r = yield defer.succeed(False)
        return r

    @defer.inlineCallbacks
    def on_callback_query(self, _callback_query):
        r = yield defer.succeed(False)
        return r
