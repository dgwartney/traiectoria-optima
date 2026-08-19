import matplotlib

# Use a non-interactive backend so plotting code under test never tries to
# open a GUI window during the test run.
matplotlib.use("Agg")
