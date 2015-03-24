from tornado import gen

from checkio_referee import exceptions


class EnvironmentClient(object):

    def __init__(self, stream, environment_id):
        self._stream = stream
        self._on_stop_callback = None
        self._is_stopping = None
        self.environment_id = environment_id

    def set_on_stop_callback(self, callback):
        self._on_stop_callback = callback

    @gen.coroutine
    def write(self, data):
        yield self._stream.write(data)

    @gen.coroutine
    def read_message(self):
        return (yield self._stream.read_message())

    @gen.coroutine
    def _request(self, data):
        yield self.write(data)
        response = yield self.read_message()
        if response.get('status') != 'success':
            raise exceptions.EnvironmentRunFail(response)
        return response

    @gen.coroutine
    def run_code(self, code):
        result = yield self._request({
            'action': 'run_code',
            'code': code,
        })
        return result

    @gen.coroutine
    def run_func(self, function_name, params):
        result = yield self._request({
            'action': 'run_function',
            'function_name': function_name,
            'function_args': params
        })
        return result

    @gen.coroutine
    def run_code_and_function(self, code, function_name, args):
        result = yield self._request({
            'action': 'run_code_and_function',
            'code': code,
            'function_name': function_name,
            'function_args': args
        })
        return result

    @gen.coroutine
    def run_in_console(self, code):
        result = yield self._request({
            'action': 'run_in_console',
            'code': code,
        })
        return result

    @gen.coroutine
    def set_config(self, env_config):
        result = yield self._request({
            'action': 'config',
            'env_config': env_config
        })
        return result

    @gen.coroutine
    def stop(self):
        if self._is_stopping:
            return
        self._is_stopping = True
        result = yield self.write({
            'action': 'stop'
        })
        if self._on_stop_callback is not None:
            self._on_stop_callback(self.environment_id)
        return result
