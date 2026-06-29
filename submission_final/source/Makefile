CXX ?= g++
CXXFLAGS ?= -O3 -std=c++17 -Wall -Wextra -pedantic -pthread
CPPFLAGS := -Iinclude $(EXTRA_CPPFLAGS)

BUILD_DIR := build
APPROX_OBJS := $(BUILD_DIR)/sbox_corr.o $(BUILD_DIR)/linear_layer.o $(BUILD_DIR)/beam_search.o
EXACT_OBJS := $(APPROX_OBJS) $(BUILD_DIR)/exact.o
EXACT_DYADIC_OBJS := $(BUILD_DIR)/sbox_corr.o $(BUILD_DIR)/linear_layer.o \
	$(BUILD_DIR)/exact_cartesian.o $(BUILD_DIR)/exact_dyadic.o

.PHONY: all clean test

# Package-safe target set: final rebuild, scoring, exact-way2, and bounded way-1 validation tools only.
# Historical candidate-discovery helpers are intentionally excluded from the final competition package.
all: estimator estimator_exact recompute_frozen_exact exact_oracle exact_batch_mt exact_batch_current exact_batch_grouped_u exact_batch_grouped_uv reduce_exact_parts enumerate_r1_positive score

$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

$(BUILD_DIR)/%.o: src/%.cpp | $(BUILD_DIR)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -c -o $@ $<

estimator: apps/estimator.cpp $(APPROX_OBJS)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -o $@ $^

estimator_exact: apps/estimator_exact.cpp $(EXACT_DYADIC_OBJS)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -o $@ $^

recompute_frozen_exact: apps/recompute_frozen_exact.cpp $(EXACT_DYADIC_OBJS)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -o $@ $^

exact_oracle: apps/exact_oracle.cpp $(EXACT_OBJS)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -o $@ $^

exact_batch_mt: apps/exact_batch_mt.cpp $(EXACT_OBJS)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -o $@ $^

exact_batch_current: apps/exact_batch_current.cpp $(EXACT_OBJS)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -Iapps -o $@ $^

exact_batch_grouped_u: apps/exact_batch_grouped_u.cpp $(EXACT_OBJS)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -Iapps -o $@ $^

exact_batch_grouped_uv: apps/exact_batch_grouped_uv.cpp $(EXACT_OBJS)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -Iapps -o $@ $^

reduce_exact_parts: apps/reduce_exact_parts.cpp
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -o $@ $^

enumerate_r1_positive: apps/enumerate_r1_positive.cpp $(BUILD_DIR)/sbox_corr.o $(BUILD_DIR)/linear_layer.o
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -o $@ $^

score: apps/score.cpp $(APPROX_OBJS)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -o $@ $^

test: all
	@test "$$(sha256sum ../submit.txt | cut -d' ' -f1)" = "7b0f638ba8678462ee8d6c12bc0c5b89d7354b4a095b31330f3ba495acfe2e2e"

clean:
	rm -rf $(BUILD_DIR)
	rm -f estimator estimator_exact recompute_frozen_exact exact_oracle exact_batch_mt exact_batch_current exact_batch_grouped_u exact_batch_grouped_uv reduce_exact_parts enumerate_r1_positive score
