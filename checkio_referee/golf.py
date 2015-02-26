from checkio_referee import RefereeBase


class RefereeCodeGolf(RefereeBase):
    BASE_LENGTHS = {
        "python_2": 1000,
        "python_3": 1000,
        "javascript": 1000,
    }
    BASE_POINTS = 0

    def count_code_length(self):
        return len(self.user_data['code'])

    def success(self):
        result_points = self.BASE_POINTS + max(self.BASE_LENGTHS[self.CURRENT_ENV] - self.count_code_length(), 0)
        return (yield self.user.post_check_success(data={"points": result_points}))
