from tornado.escape import json_encode, json_decode

from checkio_referee.exceptions import EditorPacketStructureError


RESULT_ACTION_CHECK = 'check'
RESULT_ACTION_TRY_IT = 'try_it'
RESULT_ACTION_RUN = 'run'


class PacketBase(object):

    AVAILABLE_METHODS = []

    def __init__(self, method, data, request_id=None):
        if method not in self.AVAILABLE_METHODS:
            raise EditorPacketStructureError('Packet method {} not allowed'.format(method))
        self.method = method
        self.data = data
        self.request_id = request_id

    def get_all_data(self):
        return {
            'method': self.method,
            'data': self.data,
            'request_id': self.request_id
        }

    def encode(self):
        return json_encode(self.get_all_data()).encode()

    @classmethod
    def decode(cls, data):
        data = json_decode(data.decode('utf-8'))
        return cls(data.get('method'), data.get('data'), data.get('request_id'))


class OutPacket(PacketBase):
    METHOD_SELECT = 'select'
    METHOD_STDOUT = 'stdout'
    METHOD_STDERR = 'stderr'
    METHOD_RESULT = 'result'
    METHOD_ERROR = 'error'
    METHOD_STATUS = 'status'
    METHOD_SET = 'set'
    METHOD_PRE_TEST = 'pre_test'
    METHOD_POST_TEST = 'post_test'
    METHOD_CUSTOM = 'custom'

    AVAILABLE_METHODS = (METHOD_SELECT, METHOD_STDOUT, METHOD_STDERR, METHOD_RESULT, METHOD_ERROR,
                         METHOD_STATUS, METHOD_SET, METHOD_PRE_TEST, METHOD_POST_TEST,
                         METHOD_CUSTOM)


class InPacket(PacketBase):
    METHOD_SELECT_RESULT = 'select_result'
    METHOD_GET_STATUS = 'get_status'
    METHOD_CANCEL = 'cancel'

    AVAILABLE_METHODS = (METHOD_SELECT_RESULT, METHOD_GET_STATUS, METHOD_CANCEL)
