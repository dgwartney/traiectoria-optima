"""The lookup errors, and the backward compatibility that let them be adopted.

The bases on these classes are deliberately wide. Before they existed, one
mistake -- a mistyped IATA code -- surfaced as `KeyError` from `Catalog`,
`ValueError` from `FlightPlanner`, and `None` from `find_airport`. The tests
below pin the property that made the change safe: every convention that
previously worked still works.
"""

import pytest

from flight_planner.errors import (
    AirportNotFoundError,
    AmbiguousRouteError,
    FlightPlannerError,
    RouteNotFoundError,
)

MESSAGE = "no airport 'ZZZ' in this catalog (3387 airports in scope)"


class TestBackwardCompatibleBases:
    """Adopting these errors must not break a caller written against the old types."""

    @pytest.mark.parametrize(
        "caught_as", [FlightPlannerError, KeyError, LookupError, ValueError, Exception]
    )
    def test_airport_not_found_is_catchable_as(self, caught_as):
        with pytest.raises(caught_as):
            raise AirportNotFoundError(MESSAGE)

    @pytest.mark.parametrize(
        "caught_as", [FlightPlannerError, KeyError, LookupError, Exception]
    )
    def test_route_not_found_is_catchable_as(self, caught_as):
        with pytest.raises(caught_as):
            raise RouteNotFoundError("no route SFO -> BOS in this catalog")

    @pytest.mark.parametrize(
        "caught_as",
        [RouteNotFoundError, FlightPlannerError, KeyError, LookupError, Exception],
    )
    def test_ambiguous_route_is_catchable_as(self, caught_as):
        with pytest.raises(caught_as):
            raise AmbiguousRouteError("3 routes fly SFO -> BOS")

    def test_one_except_covers_every_lookup_failure(self):
        """The whole point: a script needs one `except`, not three."""
        for error in (
            AirportNotFoundError(MESSAGE),
            RouteNotFoundError("no route"),
            AmbiguousRouteError("3 routes"),
        ):
            with pytest.raises(FlightPlannerError):
                raise error


class TestMessageRendering:
    """`KeyError` renders its message with repr, which puts quotes around it."""

    def test_airport_not_found_prints_without_stray_quotes(self):
        assert str(AirportNotFoundError(MESSAGE)) == MESSAGE

    def test_a_plain_keyerror_would_have_added_them(self):
        # Documents why the __str__ override exists at all.
        assert str(KeyError(MESSAGE)) != MESSAGE
        assert str(KeyError(MESSAGE)).startswith('"')

    def test_route_not_found_prints_without_stray_quotes(self):
        message = "no route SFO -> BOS in this catalog"
        assert str(RouteNotFoundError(message)) == message

    def test_empty_error_renders_as_empty_string(self):
        assert str(AirportNotFoundError()) == ""
