CXX ?= g++
CXXFLAGS ?= -O3 -std=c++17 -Wall -Wextra -pedantic -pthread
CPPFLAGS := -Iinclude $(EXTRA_CPPFLAGS)

BUILD_DIR := build
APPROX_OBJS := $(BUILD_DIR)/sbox_corr.o $(BUILD_DIR)/linear_layer.o $(BUILD_DIR)/beam_search.o
EXACT_OBJS := $(APPROX_OBJS) $(BUILD_DIR)/exact.o
EXACT_DYADIC_OBJS := $(BUILD_DIR)/sbox_corr.o $(BUILD_DIR)/linear_layer.o \
	$(BUILD_DIR)/exact_cartesian.o $(BUILD_DIR)/exact_dyadic.o

.PHONY: all clean test smoke

all: estimator estimator_exact exact_oracle exact_batch_mt exact_batch_current exact_batch_grouped_u exact_batch_grouped_uv reduce_exact_parts search_candidates candidate_miner_approx enumerate_r1_positive score test_core test_linear_mask_basis test_exact_cartesian test_exact_dyadic test_exact_batch_grouping
all: recompute_frozen_exact

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

test_linear_mask_basis: tests/test_linear_mask_basis.cpp $(BUILD_DIR)/linear_layer.o
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -o $@ $^

test_exact_cartesian: tests/test_exact_cartesian.cpp $(BUILD_DIR)/exact_cartesian.o $(BUILD_DIR)/sbox_corr.o
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -o $@ $^

test_exact_dyadic: tests/test_exact_dyadic.cpp $(EXACT_DYADIC_OBJS)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -o $@ $^

test_exact_batch_grouping: tests/test_exact_batch_grouping.cpp $(EXACT_OBJS)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -o $@ $^

test: test_core test_linear_mask_basis test_exact_cartesian test_exact_dyadic test_exact_batch_grouping estimator_exact recompute_frozen_exact exact_batch_current exact_batch_grouped_u exact_batch_grouped_uv score
	@test "$$(sha256sum submit.txt | cut -d' ' -f1)" = "7b0f638ba8678462ee8d6c12bc0c5b89d7354b4a095b31330f3ba495acfe2e2e"
	./test_core
	./test_linear_mask_basis
	./test_exact_cartesian
	./test_exact_dyadic
	./test_exact_batch_grouping
	@tmp=$$(mktemp); \
	  ./estimator_exact --r 2 --u 0x00002000 --v 0x08880000 --backend cpp_int --out $$tmp; \
	  grep -F '"certified_exact_dyadic": true' $$tmp >/dev/null; \
	  grep -F '"parseval_pass": true' $$tmp >/dev/null; \
	  rm -f $$tmp; \
	  failed=$$(mktemp); rm -f $$failed; \
	  ! ./estimator_exact --r 2 --u 0x00002000 --v 0x08880000 --backend cpp_int --max-transitions 1 --out $$failed; \
	  test ! -e $$failed
	python3 tests/test_score.py ./score
	python3 -X utf8 tests/test_freeze_baseline.py
	python3 -X utf8 tests/test_audit_schema.py
	python3 -X utf8 tests/test_submission_integrity.py
	PYTHONDONTWRITEBYTECODE=1 python3 -X utf8 tests/test_package_source_metadata.py
	PYTHONDONTWRITEBYTECODE=1 python3 -X utf8 tests/test_release_package_metadata.py
	python3 -X utf8 tests/test_official_spec.py
	python3 -X utf8 tests/test_walsh_spectrum.py
	python3 -X utf8 tests/test_dyadic_bounds.py
	python3 -X utf8 tests/test_exact_shard_reduction.py
	python3 -X utf8 tests/test_exact_decimal_parser.py
	python3 -X utf8 tests/test_exact_selector.py
	python3 -X utf8 tests/test_full_exact_selection.py
	PYTHONDONTWRITEBYTECODE=1 python3 -X utf8 tests/test_full_build_reproducibility.py
	PYTHONDONTWRITEBYTECODE=1 python3 -X utf8 tests/test_full_exact_authorization.py
	PYTHONDONTWRITEBYTECODE=1 python3 -X utf8 tests/test_full_exact_small_pipeline.py
	python3 -X utf8 tests/test_committed_full_exact_artifacts.py
	python3 -X utf8 tests/test_frozen_exact_pipeline.py
	python3 -X utf8 tests/test_exact_resume.py
	python3 -X utf8 tests/test_exact_artifact_gate.py
	python3 -X utf8 tests/test_committed_exact_pilot_artifacts.py
	python3 -X utf8 tests/test_way1_benchmark_protocol.py
	python3 -X utf8 tests/test_way1_query_families.py
	python3 -X utf8 tests/test_way1_stage_a0.py
	python3 -X utf8 tests/test_way1_stage_a1.py
	python3 -X utf8 tests/test_way1_stage_a2.py
	python3 -X utf8 tests/test_way1_stage_toolchain.py
	python3 -X utf8 tests/test_stage_a_closeout_provenance.py
	python3 -X utf8 tests/test_stage_a_compact_package.py
	python3 -X utf8 tests/test_strategy_b_stage_a_artifacts.py
	python3 -X utf8 tests/test_final_package_hardening.py
	@test "$$(sha256sum submit.txt | cut -d' ' -f1)" = "7b0f638ba8678462ee8d6c12bc0c5b89d7354b4a095b31330f3ba495acfe2e2e"

smoke: all
	./estimator --r 1 --u 0x10000000 --top 8 --beam 10000 --trans 10000
	@tmp=$$(mktemp -d); \
	  (cd $$tmp && $(CURDIR)/search_candidates --r-start 1 --r-end 1 --max-active 1 --max-u 4 --top-v 4 --one-round-fast-vt --beam 10000 --trans 10000 --out candidates_r1.csv && test -s candidates_r1.csv && test ! -e submit.txt); \
	  rm -rf $$tmp

clean:
	rm -rf $(BUILD_DIR)
	rm -f estimator estimator_exact recompute_frozen_exact exact_oracle exact_batch_mt exact_batch_current exact_batch_grouped_u exact_batch_grouped_uv reduce_exact_parts search_candidates candidate_miner_approx enumerate_r1_positive score test_core test_linear_mask_basis test_exact_cartesian test_exact_dyadic test_exact_batch_grouping
	rm -f candidates.csv candidates_approx.csv exact_verified.csv exact_part_*.csv smoke_*.csv submit_r1_full.txt
