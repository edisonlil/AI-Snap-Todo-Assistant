from src.aica.single_instance import ERROR_ALREADY_EXISTS, is_already_running


def test_is_already_running_when_mutex_exists():
    assert is_already_running(ERROR_ALREADY_EXISTS)


def test_is_not_already_running_for_other_error_codes():
    assert not is_already_running(0)
    assert not is_already_running(5)
