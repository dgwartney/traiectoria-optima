"""Unit tests for `validation.measurement`."""

import json

import pytest

from validation.measurement import environment, median_ms


class TestEnvironment:
    """What a recorded timing has to say about where it came from."""

    def test_it_reports_the_five_fields_a_result_needs(self):
        described = environment()

        assert set(described) == {"cpu", "cores", "platform", "python", "colab"}

    def test_every_value_is_json_serializable(self):
        # It goes straight into results.json; an unserializable value would
        # fail the record *after* the experiment had done all its work.
        json.dumps(environment())

    def test_the_cpu_is_a_non_empty_string(self):
        assert environment()["cpu"].strip()

    def test_the_core_count_is_a_positive_integer(self):
        cores = environment()["cores"]

        assert isinstance(cores, int)
        assert cores >= 1

    def test_the_python_version_matches_the_running_interpreter(self):
        import platform

        assert environment()["python"] == platform.python_version()

    def test_colab_is_a_bool_and_false_off_colab(self):
        # The find_spec call raises ModuleNotFoundError rather than returning
        # None when `google` is absent, which is the normal local case.
        colab = environment()["colab"]

        assert isinstance(colab, bool)
        assert colab is False

    def test_repeated_calls_agree(self):
        assert environment() == environment()


class TestMedianMs:
    """Timing a callable without letting one hiccup set the number."""

    def test_it_returns_a_positive_duration(self):
        assert median_ms(lambda: sum(range(1000))) > 0.0

    def test_it_runs_the_work_once_more_than_it_times(self):
        # One untimed warm-up, then `repeats` timed runs.
        calls = []

        median_ms(lambda: calls.append(1), repeats=4)

        assert len(calls) == 5

    def test_the_default_is_five_timed_runs(self):
        calls = []

        median_ms(lambda: calls.append(1))

        assert len(calls) == 6

    def test_a_single_repeat_is_allowed(self):
        calls = []

        median_ms(lambda: calls.append(1), repeats=1)

        assert len(calls) == 2

    def test_zero_repeats_is_an_error_rather_than_a_nan(self):
        with pytest.raises(ValueError, match="at least 1"):
            median_ms(lambda: None, repeats=0)

    def test_the_return_value_of_the_work_is_discarded(self):
        assert isinstance(median_ms(lambda: "a string"), float)

    def test_slower_work_measures_slower(self):
        # A weak assertion on purpose: anything stronger is a flaky test on
        # shared CI hardware.
        fast = median_ms(lambda: sum(range(100)), repeats=7)
        slow = median_ms(lambda: sum(range(400_000)), repeats=7)

        assert slow > fast
