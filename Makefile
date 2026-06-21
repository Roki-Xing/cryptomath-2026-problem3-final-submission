CXX ?= g++
CXXFLAGS ?= -O3 -std=c++17 -Wall -Wextra -pedantic -pthread
CPPFLAGS := -Iinclude

BUILD_DIR := build
APPROX_OBJS := $(BUILD_DIR)/sbox_corr.o $(BUILD_DIR)/linear_layer.o $(BUILD_DIR)/beam_search.o
EXACT_OBJS := $(APPROX_OBJS) $(BUILD_DIR)/exact.o

.PHONY: all clean test smoke

all: estimator exact_oracle exact_batch_mt reduce_exact_parts search_candidates candidate_miner_approx enumerate_r1_positive score test_core

$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

$(BUILD_DIR)/%.o: src/%.cpp | $(BUILD_DIR)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -c -o $@ $<

estimator: apps/estimator.cpp $(APPROX_OBJS)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -o $@ $^

exact_oracle: apps/exact_oracle.cpp $(EXACT_OBJS)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -o $@ $^

exact_batch_mt: apps/exact_batch_mt.cpp $(EXACT_OBJS)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -o $@ $^

reduce_exact_parts: apps/reduce_exact_parts.cpp
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -o $@ $^

search_candidates: apps/search_candidates.cpp $(EXACT_OBJS)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -o $@ $^

candidate_miner_approx: apps/candidate_miner_approx.cpp $(APPROX_OBJS)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -o $@ $^

enumerate_r1_positive: apps/enumerate_r1_positive.cpp $(BUILD_DIR)/sbox_corr.o $(BUILD_DIR)/linear_layer.o
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -o $@ $^

score: apps/score.cpp $(APPROX_OBJS)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -o $@ $^

test_core: tests/test_core.cpp $(EXACT_OBJS)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -o $@ $^

test: test_core score
	./test_core
	python3 tests/test_score.py ./score

smoke: all
	./estimator --r 1 --u 0x10000000 --top 8 --beam 10000 --trans 10000
	@tmp=$$(mktemp -d); \
	  (cd $$tmp && $(CURDIR)/search_candidates --r-start 1 --r-end 1 --max-active 1 --max-u 4 --top-v 4 --one-round-fast-vt --beam 10000 --trans 10000 --out candidates_r1.csv && $(CURDIR)/score submit.txt); \
	  rm -rf $$tmp

clean:
	rm -rf $(BUILD_DIR)
	rm -f estimator exact_oracle exact_batch_mt reduce_exact_parts search_candidates candidate_miner_approx enumerate_r1_positive score test_core
	rm -f candidates.csv candidates_approx.csv exact_verified.csv exact_part_*.csv smoke_*.csv submit_r1_full.txt
