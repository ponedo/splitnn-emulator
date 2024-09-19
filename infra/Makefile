# Variables
BINARY_NAME := itl_test
BIN_DIR := bin
SRC_DIR := ./

# Default target to build the binary
all: build

# Build target
build:
	@echo "Building the project..."
	@mkdir -p $(BIN_DIR)
	@go build -o $(BIN_DIR)/$(BINARY_NAME) $(SRC_DIR)

# Clean target to remove binaries
clean:
	@echo "Cleaning up..."
	@rm -rf $(BIN_DIR)

# Run target to execute the binary
run: build
	@echo "Running the project..."
	@./$(BIN_DIR)/$(BINARY_NAME)

# Help target to show available commands
help:
	@echo "Available commands:"
	@echo "  make          - Build the project (default)"
	@echo "  make build    - Compile the project and place the binary in bin/"
	@echo "  make clean    - Remove the bin/ directory and binaries"
	@echo "  make run      - Build and run the project"
