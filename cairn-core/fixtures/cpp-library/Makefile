CXX ?= g++
CXXFLAGS ?= -std=c++17 -Wall -Wextra -pedantic -Iinclude
BUILD_DIR ?= /tmp/cc-spec-cpp-library-build
TEST_BIN := $(BUILD_DIR)/test_math

.PHONY: build test clean

build: $(TEST_BIN)

$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

$(TEST_BIN): include/cc_spec_sample/math.hpp src/math.cpp tests/test_math.cpp | $(BUILD_DIR)
	$(CXX) $(CXXFLAGS) src/math.cpp tests/test_math.cpp -o $(TEST_BIN)

test: build
	$(TEST_BIN)

clean:
	rm -rf $(BUILD_DIR)
