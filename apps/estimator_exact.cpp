#include <atomic>
#include <cctype>
#include <csignal>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <map>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

#include <unistd.h>

#include "cli_utils.hpp"
#include "exact_dyadic.hpp"
#include "packing.hpp"

using namespace hs;

namespace {

std::atomic<bool> interrupted{false};
constexpr const char* kCurrentRepository = "Roki-Xing/cryptomath-2026-problem3-final-submission";
constexpr const char* kPackageMetadataSchema = "package-source-metadata-v1";
constexpr const char* kPackageMetadataPath = "PACKAGE_SOURCE_COMMIT.txt";

void on_signal(int) {
    interrupted.store(true);
}

std::string trim(std::string value) {
    while (!value.empty() && (value.back() == '\n' || value.back() == '\r' || value.back() == ' ')) {
        value.pop_back();
    }
    std::size_t offset = 0;
    while (offset < value.size() && (value[offset] == ' ' || value[offset] == '\t')) {
        ++offset;
    }
    if (offset != 0) value.erase(0, offset);
    return value;
}

bool valid_commit_hash(const std::string& commit) {
    if (commit.size() != 40 && commit.size() != 64) return false;
    for (char ch : commit) {
        if (!std::isxdigit(static_cast<unsigned char>(ch))) return false;
    }
    return true;
}

bool valid_sha256(const std::string& value) {
    if (value.size() != 64) return false;
    for (char ch : value) {
        if (!std::isxdigit(static_cast<unsigned char>(ch))) return false;
    }
    return true;
}

bool valid_rfc3339_utc(const std::string& value) {
    if (value.size() != 20) return false;
    for (std::size_t index = 0; index < value.size(); ++index) {
        const char ch = value[index];
        const bool digit_position = index == 0 || index == 1 || index == 2 || index == 3 ||
                                    index == 5 || index == 6 || index == 8 || index == 9 ||
                                    index == 11 || index == 12 || index == 14 || index == 15 ||
                                    index == 17 || index == 18;
        if (digit_position) {
            if (!std::isdigit(static_cast<unsigned char>(ch))) return false;
            continue;
        }
        if ((index == 4 || index == 7) && ch != '-') return false;
        if (index == 10 && ch != 'T') return false;
        if ((index == 13 || index == 16) && ch != ':') return false;
        if (index == 19 && ch != 'Z') return false;
    }
    const auto parse_uint = [&](std::size_t offset, std::size_t width) -> int {
        int parsed = 0;
        for (std::size_t index = 0; index < width; ++index) {
            parsed = parsed * 10 + (value[offset + index] - '0');
        }
        return parsed;
    };
    const int year = parse_uint(0, 4);
    const int month = parse_uint(5, 2);
    const int day = parse_uint(8, 2);
    const int hour = parse_uint(11, 2);
    const int minute = parse_uint(14, 2);
    const int second = parse_uint(17, 2);
    if (year < 1 || year > 9999) return false;
    if (month < 1 || month > 12) return false;
    const bool leap = year % 4 == 0 && (year % 100 != 0 || year % 400 == 0);
    static const int month_days[] = {0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31};
    int max_day = month_days[month];
    if (month == 2 && leap) max_day = 29;
    if (day < 1 || day > max_day) return false;
    if (hour < 0 || hour > 23) return false;
    if (minute < 0 || minute > 59) return false;
    if (second < 0 || second > 59) return false;
    return true;
}

std::string read_command(const char* command) {
    std::string output;
    FILE* pipe = popen(command, "r");
    if (pipe == nullptr) return output;
    char buffer[256];
    while (fgets(buffer, sizeof(buffer), pipe) != nullptr) output += buffer;
    if (pclose(pipe) != 0) return "";
    return trim(output);
}

std::string sha256_text(const std::string& text) {
    char path[] = "/tmp/estimator_exact_sha256_XXXXXX";
    const int fd = mkstemp(path);
    if (fd < 0) throw std::runtime_error("cannot create SHA-256 temporary file");

    std::size_t offset = 0;
    while (offset < text.size()) {
        const ssize_t written = write(fd, text.data() + offset, text.size() - offset);
        if (written <= 0) {
            close(fd);
            std::remove(path);
            throw std::runtime_error("cannot write SHA-256 temporary file");
        }
        offset += static_cast<std::size_t>(written);
    }
    close(fd);

    const std::string command = std::string("sha256sum ") + path;
    const std::string output = read_command(command.c_str());
    std::remove(path);
    if (output.size() < 64) throw std::runtime_error("sha256sum did not return a digest");
    return output.substr(0, 64);
}

struct PackageMetadata {
    std::string schema;
    std::string repository;
    std::string release_ref;
    std::string release_commit;
    std::string package_generated_at_utc;
    std::string submit_source_commit;
    std::string submit_sha256;
};

std::optional<PackageMetadata> load_package_metadata(const std::string& path) {
    std::ifstream input(path);
    if (!input) return std::nullopt;

    std::map<std::string, std::string> rows;
    std::string line;
    while (std::getline(input, line)) {
        line = trim(line);
        if (line.empty()) continue;
        const std::size_t colon = line.find(':');
        if (colon == std::string::npos) {
            throw std::runtime_error("invalid PACKAGE_SOURCE_COMMIT: malformed line");
        }
        const std::string key = trim(line.substr(0, colon));
        const std::string value = trim(line.substr(colon + 1));
        if (key.empty()) throw std::runtime_error("invalid PACKAGE_SOURCE_COMMIT: empty key");
        if (rows.count(key) != 0) {
            throw std::runtime_error("invalid PACKAGE_SOURCE_COMMIT: duplicate key");
        }
        rows.emplace(key, value);
    }

    static const std::vector<std::string> required_keys = {
        "schema",
        "repository",
        "release_ref",
        "release_commit",
        "package_generated_at_utc",
        "submit_source_commit",
        "submit_sha256",
    };
    if (rows.size() != required_keys.size()) {
        throw std::runtime_error("invalid PACKAGE_SOURCE_COMMIT: unexpected field count");
    }
    for (const auto& key : required_keys) {
        if (rows.count(key) == 0) {
            throw std::runtime_error("invalid PACKAGE_SOURCE_COMMIT: missing key");
        }
    }
    for (const auto& [key, _] : rows) {
        bool known = false;
        for (const auto& expected : required_keys) {
            if (key == expected) {
                known = true;
                break;
            }
        }
        if (!known) throw std::runtime_error("invalid PACKAGE_SOURCE_COMMIT: unknown key");
    }

    PackageMetadata metadata{
        rows.at("schema"),
        rows.at("repository"),
        rows.at("release_ref"),
        rows.at("release_commit"),
        rows.at("package_generated_at_utc"),
        rows.at("submit_source_commit"),
        rows.at("submit_sha256"),
    };
    if (metadata.schema != kPackageMetadataSchema) {
        throw std::runtime_error("invalid PACKAGE_SOURCE_COMMIT: unexpected schema");
    }
    if (metadata.repository != kCurrentRepository) {
        throw std::runtime_error("invalid PACKAGE_SOURCE_COMMIT: unexpected repository");
    }
    if (metadata.release_ref.empty()) {
        throw std::runtime_error("invalid PACKAGE_SOURCE_COMMIT: empty release_ref");
    }
    if (!valid_commit_hash(metadata.release_commit)) {
        throw std::runtime_error("invalid PACKAGE_SOURCE_COMMIT: invalid release_commit");
    }
    if (!valid_rfc3339_utc(metadata.package_generated_at_utc)) {
        throw std::runtime_error("invalid PACKAGE_SOURCE_COMMIT: invalid package_generated_at_utc");
    }
    if (!valid_commit_hash(metadata.submit_source_commit)) {
        throw std::runtime_error("invalid PACKAGE_SOURCE_COMMIT: invalid submit_source_commit");
    }
    if (!valid_sha256(metadata.submit_sha256)) {
        throw std::runtime_error("invalid PACKAGE_SOURCE_COMMIT: invalid submit_sha256");
    }
    return metadata;
}

std::string resolve_git_commit() {
    const std::string commit = read_command("git rev-parse HEAD 2>/dev/null");
    if (commit.empty()) return "";
    if (!valid_commit_hash(commit)) {
        throw std::runtime_error("git rev-parse HEAD returned an invalid commit");
    }
    return commit;
}

std::string source_commit() {
    const auto metadata = load_package_metadata(kPackageMetadataPath);
    std::optional<std::string> macro_commit;
    std::optional<std::string> git_commit;
    std::optional<std::string> metadata_commit;
#ifdef HS_SOURCE_COMMIT
    const std::string build_time_commit = trim(HS_SOURCE_COMMIT);
    if (!valid_commit_hash(build_time_commit)) {
        throw std::runtime_error("invalid build-time HS_SOURCE_COMMIT");
    }
    macro_commit = build_time_commit;
#endif
    const std::string resolved_git_commit = resolve_git_commit();
    if (!resolved_git_commit.empty()) {
        git_commit = resolved_git_commit;
    }
    if (metadata.has_value()) metadata_commit = metadata->release_commit;

    auto require_equal = [](const std::string& lhs_name,
                            const std::string& lhs_value,
                            const std::string& rhs_name,
                            const std::string& rhs_value) {
        if (lhs_value != rhs_value) {
            throw std::runtime_error(lhs_name + " mismatch with " + rhs_name);
        }
    };
    if (macro_commit.has_value() && git_commit.has_value()) {
        require_equal("build-time HS_SOURCE_COMMIT", *macro_commit, "git HEAD", *git_commit);
    }
    if (macro_commit.has_value() && metadata_commit.has_value()) {
        require_equal("build-time HS_SOURCE_COMMIT", *macro_commit, "PACKAGE_SOURCE_COMMIT", *metadata_commit);
    }
    if (git_commit.has_value() && metadata_commit.has_value()) {
        require_equal("git HEAD", *git_commit, "PACKAGE_SOURCE_COMMIT", *metadata_commit);
    }

    if (macro_commit.has_value()) return *macro_commit;
    if (git_commit.has_value()) return *git_commit;
    if (metadata_commit.has_value()) return *metadata_commit;
    throw std::runtime_error("cannot determine source commit");
}

std::string bool_json(bool value) {
    return value ? "true" : "false";
}

std::string make_artifact(std::uint64_t row_id,
                          Mask v,
                          ExactNumericBackend backend,
                          const ExactDyadicResult& result,
                          const std::string& commit,
                          const std::string& input_sha,
                          const std::string& command_sha) {
    const auto state = result.states.find(v);
    const cpp_int numerator = state == result.states.end() ? cpp_int(0) : state->second;
    std::ostringstream output;
    output << "{\n"
           << "  \"row_id\": " << row_id << ",\n"
           << "  \"r\": " << result.rounds << ",\n"
           << "  \"u\": \"" << hex32(result.u) << "\",\n"
           << "  \"v\": \"" << hex32(v) << "\",\n"
           << "  \"numerator\": \"" << numerator << "\",\n"
           << "  \"denominator_exp2\": " << result.denominator_exp2 << ",\n"
           << "  \"value_fraction\": \"" << numerator << "/2^" << result.denominator_exp2
           << "\",\n"
           << "  \"numeric_backend\": \"" << exact_numeric_backend_name(backend) << "\",\n"
           << "  \"exact_cartesian_complete\": " << bool_json(result.exact_cartesian_complete)
           << ",\n"
           << "  \"no_state_pruning\": " << bool_json(result.no_state_pruning) << ",\n"
           << "  \"certified_no_truncation\": "
           << bool_json(result.certified_no_truncation) << ",\n"
           << "  \"certified_exact_dyadic\": "
           << bool_json(result.certified_exact_dyadic) << ",\n"
           << "  \"parseval_pass\": " << bool_json(result.parseval_pass) << ",\n"
           << "  \"state_count\": " << result.states.size() << ",\n"
           << "  \"sum_squares\": \"" << result.sum_squares << "\",\n"
           << "  \"expected_sum_squares\": \"" << result.expected_sum_squares << "\",\n"
           << "  \"expanded_states\": " << result.expanded_states << ",\n"
           << "  \"generated_transitions\": " << result.generated_transitions << ",\n"
           << "  \"source_commit\": \"" << commit << "\",\n"
           << "  \"input_sha256\": \"" << input_sha << "\",\n"
           << "  \"command_sha256\": \"" << command_sha << "\"\n"
           << "}\n";
    return output.str();
}

void write_atomic(const std::string& path, const std::string& content) {
    const std::string temporary = path + ".tmp." + std::to_string(getpid());
    {
        std::ofstream output(temporary, std::ios::binary);
        if (!output) throw std::runtime_error("cannot open temporary artifact: " + temporary);
        output << content;
        output.flush();
        if (!output) {
            output.close();
            std::remove(temporary.c_str());
            throw std::runtime_error("cannot serialize complete artifact");
        }
    }
    if (std::rename(temporary.c_str(), path.c_str()) != 0) {
        std::remove(temporary.c_str());
        throw std::runtime_error("cannot atomically publish artifact: " + path);
    }
}

void usage(const char* program) {
    std::cerr << "Usage: " << program
              << " --r R --u MASK --v MASK [--backend cpp_int|int128]"
                 " [--row-id N] [--max-states N] [--max-transitions N] [--out FILE]\n";
}

} // namespace

int main(int argc, char** argv) {
    try {
        std::signal(SIGINT, on_signal);
        std::signal(SIGTERM, on_signal);

        ExactDyadicOptions options;
        Mask v = 0;
        bool have_rounds = false;
        bool have_u = false;
        bool have_v = false;
        std::uint64_t row_id = 1;
        std::optional<std::string> out_path;

        std::string command_material;
        for (int i = 0; i < argc; ++i) {
            if (i != 0) command_material.push_back('\0');
            command_material += argv[i];
        }

        for (int i = 1; i < argc; ++i) {
            const std::string option = argv[i];
            if (option == "--r") {
                options.rounds = std::stoi(require_arg(i, argc, argv, option));
                have_rounds = true;
            } else if (option == "--u") {
                options.u = parse_mask(require_arg(i, argc, argv, option));
                have_u = true;
            } else if (option == "--v") {
                v = parse_mask(require_arg(i, argc, argv, option));
                have_v = true;
            } else if (option == "--backend") {
                const std::string backend = require_arg(i, argc, argv, option);
                if (backend == "cpp_int") options.backend = ExactNumericBackend::CppInt;
                else if (backend == "int128") options.backend = ExactNumericBackend::Int128Checked;
                else throw std::invalid_argument("unknown exact backend: " + backend);
            } else if (option == "--row-id") {
                row_id = parse_u64(require_arg(i, argc, argv, option));
            } else if (option == "--max-states") {
                options.max_states = parse_u64(require_arg(i, argc, argv, option));
            } else if (option == "--max-transitions") {
                options.max_generated_transitions = parse_u64(require_arg(i, argc, argv, option));
            } else if (option == "--out") {
                out_path = require_arg(i, argc, argv, option);
            } else if (option == "--help" || option == "-h") {
                usage(argv[0]);
                return 0;
            } else {
                throw std::invalid_argument("unknown option: " + option);
            }
        }

        if (!have_rounds || !have_u || !have_v) {
            usage(argv[0]);
            return 2;
        }

        options.should_cancel = [] { return interrupted.load(); };
        const std::string commit = source_commit();
        if (commit.empty()) throw std::runtime_error("source commit is unavailable");
        const std::string input_material =
            "r=" + std::to_string(options.rounds) + "\nu=" + hex32(options.u) +
            "\nv=" + hex32(v) + "\nbackend=" + exact_numeric_backend_name(options.backend) + "\n";
        const auto result = compute_exact_dyadic(options);
        if (!result.certified_exact_dyadic || !result.parseval_pass) {
            throw std::runtime_error("exact run rejected: " + result.failure_reason);
        }

        const std::string artifact =
            make_artifact(row_id, v, options.backend, result, commit, sha256_text(input_material),
                          sha256_text(command_material));
        if (out_path.has_value()) {
            write_atomic(*out_path, artifact);
        } else {
            std::cout << artifact;
        }
    } catch (const std::exception& error) {
        std::cerr << "error: " << error.what() << '\n';
        return 1;
    }
    return 0;
}
