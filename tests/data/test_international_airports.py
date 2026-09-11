import pandas as pd

from international_airports import InternationalAirportsBuilder


class TestCodeNormalisation:
    """Wikipedia footnote markers must not leak into IATA codes.

    Cited table cells render as `<sup class="reference">[1]</sup>`, which the
    scraper captures with the cell's text. `MHH[1]` then matches nothing in
    OurAirports, and the airport is silently reported unresolved.
    """

    def test_footnote_marker_is_stripped(self):
        assert InternationalAirportsBuilder.normalise_code("MHH[1]") == "MHH"
        assert InternationalAirportsBuilder.normalise_code("YXE[2]") == "YXE"

    def test_multi_digit_and_repeated_markers_are_stripped(self):
        assert InternationalAirportsBuilder.normalise_code("ABC[12]") == "ABC"
        assert InternationalAirportsBuilder.normalise_code("ABC[1][2]") == "ABC"

    def test_ordinary_codes_are_untouched(self):
        assert InternationalAirportsBuilder.normalise_code(" mhh ") == "MHH"

    def test_nadi_is_not_mistaken_for_a_missing_value(self):
        # Nadi's IATA code is literally NAN; the module documents this trap.
        assert InternationalAirportsBuilder.normalise_code("NAN") == "NAN"

    def test_missing_values_become_empty(self):
        assert InternationalAirportsBuilder.normalise_code(None) == ""
        assert InternationalAirportsBuilder.normalise_code("") == ""

    def test_series_normalisation_strips_footnotes_too(self):
        codes = pd.Series(["MHH[1]", " yxe ", None, "NAN"])

        result = list(InternationalAirportsBuilder.normalise(codes))

        assert result == ["MHH", "YXE", "", "NAN"]


class TestMultiCodeCells:
    """One cell can list several codes for the same airport.

    EuroAirport Basel-Mulhouse-Freiburg is listed once per country and its
    cell reads `BSL/MLH/EAP`. OurAirports lists the field under BSL, which
    `data/reference/iata_code_overrides.csv` already records.
    """

    def test_first_code_is_taken(self):
        assert InternationalAirportsBuilder.normalise_code("BSL/MLH/EAP") == "BSL"

    def test_whitespace_around_separators_is_handled(self):
        assert InternationalAirportsBuilder.normalise_code(" bsl / mlh ") == "BSL"

    def test_combined_with_a_footnote_marker(self):
        assert InternationalAirportsBuilder.normalise_code("BSL[3]/MLH") == "BSL"

    def test_series_takes_the_first_code_too(self):
        codes = pd.Series(["BSL/MLH/EAP", "MHH[1]", "NAN"])

        assert list(InternationalAirportsBuilder.normalise(codes)) == ["BSL", "MHH", "NAN"]
