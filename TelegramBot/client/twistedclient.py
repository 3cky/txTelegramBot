from TelegramBotAPI.client.baseclient import BaseClient
from TelegramBotAPI.types.methods import getUpdates

from twisted.application import service
from twisted.internet import reactor, defer
from twisted.python import log, failure
from twisted.web import http

import treq

class RequestError(Exception):
    def __init__(self, value, err_code=-1):
        self.value = value
        self.err_code = err_code
    def __str__(self):
        s = repr(self.value)
        if self.err_code > 0:
            s = "HTTP Error: " + str(self.err_code) + "\n" + s
        return s

class TwistedClient(service.Service, BaseClient):
    name = 'telegrambot_client'

    _request_timeout = 120
    _limit = 10
    _poll_timeout = 30
    _poll = True
    _offset = None
    _poll_backoff = 0

    def __init__(self, token, on_update, proxy=None, debug=False):
        super(TwistedClient, self).__init__(token, debug)
        self._token = token
        self._proxy = proxy
        self._debug = debug
        assert callable(on_update)
        self._on_update = on_update

    def startService(self):
        reactor.callLater(0, self._poll_updates_loop)

    def stopService(self):
        self._poll = False

    @defer.inlineCallbacks
    def send_method(self, method):
        try:
            url = self._get_post_url(method)
            params, data = self.__get_post_params_and_data(method)

            resp = yield treq.post(url, params=params, data=data, timeout=self._request_timeout)

            if resp.code != http.OK:
                err_info = yield treq.content(resp)
                raise RequestError(str(err_info), resp.code)

            value = yield treq.json_content(resp)

            defer.returnValue(self._interpret_response(value, method))
        except Exception as e:
            if isinstance(e, RequestError):
                raise e
            raise RequestError(e)

    def __get_post_params_and_data(self, method):
        params = method._to_raw()
        data = {}
        for k in list(params.keys()):
            from io import BufferedReader
            if isinstance(params[k], BufferedReader):
                import os
                data[k] = (os.path.split(params[k].name)[1], params[k])
                del params[k]
        return params, data

    @defer.inlineCallbacks
    def _poll_updates_loop(self, _=None):
        while self._poll:
            yield self._poll_updates()
            if self._poll_backoff:
                log.msg('Backing off updates poll for %s second(s)' % self._poll_backoff)
            d = defer.Deferred()
            reactor.callLater(self._poll_backoff, d.callback, None)
            self._poll_backoff = 0
            yield d

    @defer.inlineCallbacks
    def _poll_updates(self):
        m = getUpdates()
        m.timeout = self._poll_timeout
        m.limit = self._limit
        if self._offset is not None:
            m.offset = self._offset
        try:
            updates = yield self.send_method(m)
            reactor.callFromThread(self._handle_updates_result, updates)
        except Exception as e:
            self._handle_updates_error(e)
            # import traceback
            # log.msg(traceback.format_exc())

    @defer.inlineCallbacks
    def _handle_updates_result(self, updates):
        if updates:
            for update in updates:
                self._offset = update.update_id + 1
                try:
                    yield defer.maybeDeferred(self._on_update, update)
                except Exception as e:
                    # import traceback
                    # log.msg(traceback.format_exc())
                    f = failure.Failure()
                    log.err(f, e)
                    pass

    def _handle_updates_error(self, e):
        if self._poll:
            f = failure.Failure()
            log.err(f, "Updates fetching error: %s" % e)
            self._poll_backoff = 5
