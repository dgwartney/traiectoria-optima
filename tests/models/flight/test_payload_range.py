import matplotlib.pyplot as plt

from payload_range import plot_payload_range_diagram


def test_plot_payload_range_diagram_runs_without_error(monkeypatch):
    # The Agg backend from conftest.py already prevents a GUI window; also
    # stub out show() so the test doesn't block or require a display.
    monkeypatch.setattr(plt, "show", lambda: None)

    plot_payload_range_diagram()

    assert plt.gcf().get_axes()
    plt.close("all")
