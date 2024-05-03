class TestBase:
    """ Базовый класс для тестов """

    @classmethod
    def get_authorization_header(cls, token: str) -> dict:  # noqa: ANN102
        return {'Authorization': f'Bearer {token}'}
