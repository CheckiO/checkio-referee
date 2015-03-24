class RefereeException(Exception):
    pass


class RefereeExecuteFailed(RefereeException):
    def __init__(self, points=None, description=None, additional_data=None, *args, **kwargs):
        self._additional_data = additional_data or {}
        self.points = points
        self.description = points
        super().__init__(*args, **kwargs)

    @property
    def additional_data(self):
        self._additional_data['description'] = self.description
        return self._additional_data


class RefereeTestFailed(RefereeExecuteFailed):
    pass


class RefereeCodeRunFailed(RefereeExecuteFailed):
    pass


class CheckioEnvironmentError(Exception):
    pass


class EnvironmentRunFail(CheckioEnvironmentError):
    pass


class EditorError(Exception):
    pass


class EditorPacketStructureError(EditorError):
    pass
