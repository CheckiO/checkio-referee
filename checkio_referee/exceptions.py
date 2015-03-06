class RefereeException(Exception):
    pass


class RefereeTestFailed(RefereeException):
    def __init__(self, points=None, additional_data=None, *args, **kwargs):
        self.additional_data = additional_data
        self.points = points
        super().__init__(*args, **kwargs)
