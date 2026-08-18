PROCESSED_DATA_DIR=data/processed
FLIGHT_DATA_DB=flight_data.db

SRC_DIR=src
SRC_DATA_DIR=$(SRC_DIR)/data
SRC_FLIGHT_DATA_DB=$(SRC_DATA_DIR)/flight_data.py

# Start a jupyter lab session from the install virtual
# environment setup by `uv`
notebook:
	uv run jupyter lab

flight_data: 
	uv run python $(SRC_FLIGHT_DATA_DB)

clean:
	$(RM) $(PROCESSED_DATA_DIR)/$(FLIGHT_DATA_DB)
