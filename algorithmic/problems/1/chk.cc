#include <cmath>
#include <algorithm>

// Natural-log calibration above the previous 60-point threshold.
// Keep validation and low scores; an exact zero minimization cost earns 100.
static double natural_log_score(double old_points, long double value,
                                long double anchor, bool minimize) {
    if (minimize && value == 0.0L) return 100.0;
    if (old_points <= 60.0 || !(value > 0.0L) || !(anchor > 0.0L))
        return old_points;
    const long double delta = minimize ? std::log(anchor) - std::log(value)
                                       : std::log(value) - std::log(anchor);
    return (double)std::min(100.0L, 60.0L + delta);
}

#include "testlib.h"
#include <vector>
#include <string>
#include <map>
#include <charconv>

using namespace std;

// Read JSON punctuation independently of whitespace. Stream-local errors turn
// malformed contestant JSON into PE, while malformed judge data remains FAIL.
void skipWhitespace(InStream& stream) {
    while (!stream.eof() && isspace((unsigned char)stream.curChar())) stream.readChar();
}
void expectChar(InStream& stream, char expected) {
    skipWhitespace(stream);
    if (stream.eof() || stream.readChar() != expected)
        stream.quitf(_pe, "Expected JSON character '%c'", expected);
}
string readQuotedString(InStream& stream) {
    expectChar(stream, '"');
    string value;
    while (!stream.eof()) {
        unsigned char c = stream.readChar();
        if (c == '"') return value;
        if (c < 32) stream.quitf(_pe, "Unescaped control character in JSON key");
        if (c == '\\') {
            if (stream.eof()) stream.quitf(_pe, "Unterminated JSON escape");
            c = stream.readChar();
            if (c == 'u') {
                int code = 0;
                for (int i = 0; i < 4; ++i) {
                    if (stream.eof()) stream.quitf(_pe, "Incomplete Unicode escape");
                    char h = stream.readChar();
                    int digit = h >= '0' && h <= '9' ? h - '0' :
                                h >= 'a' && h <= 'f' ? h - 'a' + 10 :
                                h >= 'A' && h <= 'F' ? h - 'A' + 10 : -1;
                    if (digit < 0) stream.quitf(_pe, "Invalid Unicode escape");
                    code = code * 16 + digit;
                }
                // Category names in this problem are ASCII. Non-ASCII keys
                // cannot match a category in the input.
                if (code > 127) stream.quitf(_wa, "Non-ASCII category name");
                c = code;
            } else if (c == 'b') c = '\b';
            else if (c == 'f') c = '\f';
            else if (c == 'n') c = '\n';
            else if (c == 'r') c = '\r';
            else if (c == 't') c = '\t';
            else if (c != '"' && c != '\\' && c != '/') stream.quitf(_pe, "Invalid JSON escape");
        }
        value += c;
        if (value.size() > 100) stream.quitf(_wa, "Category name exceeds 100 characters");
    }
    stream.quitf(_pe, "Unterminated JSON key");
}
long long readJsonInteger(InStream& stream) {
    skipWhitespace(stream);
    string token;
    if (!stream.eof() && stream.curChar() == '-') token += stream.readChar();
    while (!stream.eof() && stream.curChar() >= '0' && stream.curChar() <= '9') {
        token += stream.readChar();
        if (token.size() > 20) stream.quitf(_pe, "JSON integer is out of range");
    }
    size_t first = !token.empty() && token[0] == '-' ? 1 : 0;
    if (first == token.size() || (token[first] == '0' && token.size() > first + 1))
        stream.quitf(_pe, "Expected JSON integer without leading zeroes");
    long long value;
    auto parsed = from_chars(token.data(), token.data() + token.size(), value);
    if (parsed.ec != errc() || parsed.ptr != token.data() + token.size())
        stream.quitf(_pe, "JSON integer is out of range");
    return value;
}
map<string, vector<long long>> read_input_json(InStream& stream) {
    map<string, vector<long long>> data;
    expectChar(stream, '{');
    for (int i = 0; i < 12; ++i) {
        if (i) expectChar(stream, ',');
        string key = readQuotedString(stream);
        if (data.count(key)) stream.quitf(_pe, "Duplicate JSON key");
        expectChar(stream, ':');
        expectChar(stream, '[');
        vector<long long> values;
        for (int j = 0; j < 4; ++j) {
            if (j) expectChar(stream, ',');
            values.push_back(readJsonInteger(stream));
        }
        expectChar(stream, ']');
        data[key] = values;
    }
    expectChar(stream, '}');
    if (!stream.seekEof()) stream.quitf(_pe, "Extra data after JSON object");
    return data;
}
map<string, long long> read_output_json(InStream& stream) {
    map<string, long long> data;
    expectChar(stream, '{');
    for (int i = 0; i < 12; ++i) {
        if (i) expectChar(stream, ',');
        string key = readQuotedString(stream);
        if (data.count(key)) stream.quitf(_pe, "Duplicate JSON key");
        expectChar(stream, ':');
        data[key] = readJsonInteger(stream);
    }
    expectChar(stream, '}');
    if (!stream.seekEof()) stream.quitf(_pe, "Extra data after JSON object");
    return data;
}

// --- Checker Main Logic ---
int main(int argc, char* argv[]) {
    registerTestlibCmd(argc, argv);
    auto items = read_input_json(inf);
    auto participant_counts = read_output_json(ouf);
    long long baseline_value = ans.readLong();
    long long best_value = ans.readLong();
    long long total_mass = 0, total_volume = 0, participant_value = 0;
    if (participant_counts.size() != 12) quitf(_wa, "Output must contain exactly 12 keys");
    for (auto const& [key, count] : participant_counts) {
        if (items.find(key) == items.end()) quitf(_wa, "Unknown key: %s", key.c_str());
        if (count < 0) quitf(_wa, "Negative items for %s", key.c_str());
        if (count > items[key][0]) quitf(_wa, "Too many items for %s", key.c_str());
        participant_value += count * items[key][1];
        total_mass += count * items[key][2];
        total_volume += count * items[key][3];
    }
    long long max_mass = 20000000, max_volume = 25000000;
    if (total_mass > max_mass) quitf(_wa, "Total mass exceeds limit");
    if (total_volume > max_volume) quitf(_wa, "Total volume exceeds limit");
    if (best_value <= baseline_value)
        quitf(_fail, "Reference value must exceed baseline value");
    double r = max(0.0, (double)(participant_value - baseline_value) /
                        (double)(best_value - baseline_value));
    double score_ratio = r <= 1.0 ? 0.6 * r : (0.6 + 0.02 * log(r));
    score_ratio = natural_log_score(100.0 * score_ratio, participant_value, best_value, false) / 100.0;
    double unbounded_ratio = score_ratio;
    quitp(score_ratio, "Value: %lld. Ratio: %.12f, RatioUnbounded: %.12f", participant_value, score_ratio, unbounded_ratio);
}
