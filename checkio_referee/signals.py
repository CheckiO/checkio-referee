import threading


def _make_id(target):
    if hasattr(target, '__func__'):
        return (id(target.__self__), id(target.__func__))
    return id(target)


class Signal(object):

    def __init__(self, providing_args):
        self.receivers = {}
        if providing_args is None:
            providing_args = []
        self.providing_args = set(providing_args)
        self.lock = threading.Lock()

    def connect(self, receiver, dispatch_uid=None):
        lookup_key = _make_id(receiver) if dispatch_uid is None else dispatch_uid
        with self.lock:
            if lookup_key not in self.receivers.keys():
                self.receivers[lookup_key] = receiver

    def disconnect(self, receiver=None, dispatch_uid=None):
        lookup_key = _make_id(receiver) if dispatch_uid is None else dispatch_uid
        with self.lock:
            if lookup_key in self.receivers.keys():
                del self.receivers[lookup_key]

    def send(self, **named):
        responses = []
        if not self.receivers:
            return responses

        for receiver in self.receivers.values():
            response = receiver(signal=self, **named)
            responses.append((receiver, response))
        return responses

    def send_robust(self, **named):
        responses = []
        if not self.receivers:
            return responses

        for receiver in self.receivers.values():
            try:
                response = receiver(signal=self, **named)
            except Exception as err:
                responses.append((receiver, err))
            else:
                responses.append((receiver, response))
        return responses


def receiver(signal, **kwargs):
    """
    A decorator for connecting receivers to signals. Used by passing in the
    signal (or list of signals) and keyword arguments to connect::

        @receiver(post_save)
        def signal_receiver(**kwargs):
            ...

        @receiver([post_save, post_delete])
        def signals_receiver(**kwargs):
            ...
    """
    def _decorator(func):
        if isinstance(signal, (list, tuple)):
            for s in signal:
                s.connect(func, **kwargs)
        else:
            signal.connect(func, **kwargs)
        return func
    return _decorator
