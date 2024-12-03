# Variables
BINARY_NAME := topo_setup_test
BIN_DIR := bin
SRC_DIR := code

# Default target to build the binary
all: build

# Build target
build:
	@echo "Building the project..."
	@mkdir -p $(BIN_DIR)
	@cd $(SRC_DIR); /usr/local/go/bin/go build -o ../$(BIN_DIR)/$(BINARY_NAME) ./
	@echo "Building cctr..."
	@gcc -O2 cctr.c -o $(BIN_DIR)/cctr

# Clean target to remove binaries
clean:
	@echo "Cleaning up..."
	@rm -rf $(BIN_DIR)

# Install cctr
install:
	@cp $(BIN_DIR)/cctr /usr/bin

uninstall:
	@rm /usr/bin/cctr

# Help target to show available commands
help:
	@echo "Available commands:"
	@echo "  make          - Build the project (default)"
	@echo "  make build    - Compile the project and place the binary in bin/"
	@echo "  make clean    - Remove the bin/ directory and binaries"