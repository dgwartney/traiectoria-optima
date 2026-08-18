

# Start a jupyter lab session from the install virtual
# environment setup by `uv`
notebook:
	uv run jupyter lab

flight_data: 
	uv run python src/data/airport_data.py

clean:
	$(RM) flight_data.db
