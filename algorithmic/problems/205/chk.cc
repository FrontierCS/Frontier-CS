#include <cmath>
#include <algorithm>

// Keep historical scores through 60; above the anchor, compare physical objectives.
static double natural_log_score(long double old_points, long double value,
                                long double anchor, bool minimize) {
    if (minimize && value == 0.0L) return 100.0;
    if (old_points <= 60.0L) return (double)std::max(0.0L, old_points);
    if (!(value > 0.0L) || !(anchor > 0.0L))
        return (double)std::clamp(old_points, 0.0L, 100.0L);
    const long double improvement = minimize
        ? std::log(anchor) - std::log(value)
        : std::log(value) - std::log(anchor);
    return (double)std::clamp(60.0L + improvement, 0.0L, 100.0L);
}

#include <cmath>
#include <algorithm>
#include "testlib.h"
#include <vector>
#include <string>
#include <cstdint>
#include <cmath>

// Historical calibration supplies the unchanged low-score branch.
static double calibrated(double r) {
    r = std::max(0.0, r);
    return r <= 1.0 ? 0.6 * r : 0.6 + 0.02 * std::log(r);
}

using namespace std;

int n;

// Find matching closing parenthesis
int findMatch(const string& s, int pos) {
    if (pos < 0 || pos >= (int)s.length() || s[pos] != '(') {
        return -1;
    }
    int depth = 0;
    for (int i = pos; i < (int)s.length(); i++) {
        if (s[i] == '(') depth++;
        else depth--;
        if (depth == 0) return i;
    }
    return -1;
}

// Extract substring from pos1 to pos2 inclusive
string extract(const string& s, int start, int end) {
    if (start < 0 || end >= (int)s.length() || start > end) return "";
    return s.substr(start, end - start + 1);
}

// Check if string is a valid parenthesis sequence
bool isValid(const string& s) {
    int balance = 0;
    for (char c : s) {
        if (c == '(') balance++;
        else if (c == ')') balance--;
        else return false;
        if (balance < 0) return false;
    }
    return balance == 0;
}

// Try to apply operation 1: p(((A)B)C)q -> p((A)B)(C)q
bool tryOp1(string& s, int pos, string& err) {
    // Pattern: (((A)B)C)
    // At pos, we should have '('
    if (pos < 0 || pos >= (int)s.length() || s[pos] != '(') {
        err = "Op 1: Invalid position";
        return false;
    }

    int m1 = findMatch(s, pos);  // Outer (...)
    if (m1 < 0 || pos + 1 >= (int)s.length() || s[pos+1] != '(') {
        err = "Op 1: Pattern mismatch";
        return false;
    }

    int m2 = findMatch(s, pos+1);  // ((A)B)
    if (m2 < 0 || m2 > m1 - 1 || pos + 2 >= (int)s.length() || s[pos+2] != '(') {
        err = "Op 1: Pattern mismatch";
        return false;
    }

    int m3 = findMatch(s, pos+2);  // (A)
    if (m3 < 0 || m3 > m2 - 1) {
        err = "Op 1: Pattern mismatch";
        return false;
    }

    // Extract A, B, C (can be empty)
    string A = extract(s, pos+3, m3-1);
    string B = extract(s, m3+1, m2-1);
    string C = extract(s, m2+1, m1-1);

    // Build result: ((A)B)(C)
    string replacement = "((" + A + ")" + B + ")(" + C + ")";
    s = s.substr(0, pos) + replacement + s.substr(m1+1);
    return true;
}

// Try to apply operation 2: p((A)(B)C)q -> p((A)B)(C)q
bool tryOp2(string& s, int pos, string& err) {
    if (pos < 0 || pos >= (int)s.length() || s[pos] != '(') {
        err = "Op 2: Invalid position";
        return false;
    }

    int m1 = findMatch(s, pos);
    if (m1 < 0 || pos + 1 >= (int)s.length() || s[pos+1] != '(') {
        err = "Op 2: Pattern mismatch";
        return false;
    }

    int m2 = findMatch(s, pos+1);  // (A)
    if (m2 < 0 || m2 >= m1 || m2 + 1 >= (int)s.length() || s[m2+1] != '(') {
        err = "Op 2: Pattern mismatch";
        return false;
    }

    int m3 = findMatch(s, m2+1);  // (B)
    if (m3 < 0 || m3 > m1 - 1) {
        err = "Op 2: Pattern mismatch";
        return false;
    }

    string A = extract(s, pos+2, m2-1);
    string B = extract(s, m2+2, m3-1);
    string C = extract(s, m3+1, m1-1);

    string replacement = "((" + A + ")" + B + ")(" + C + ")";
    s = s.substr(0, pos) + replacement + s.substr(m1+1);
    return true;
}

// Try to apply operation 3: p(A)((B)C)q -> p((A)B)(C)q
bool tryOp3(string& s, int pos, string& err) {
    if (pos < 0 || pos >= (int)s.length() || s[pos] != '(') {
        err = "Op 3: Invalid position";
        return false;
    }

    int m1 = findMatch(s, pos);  // (A)
    if (m1 < 0 || m1 + 1 >= (int)s.length() || s[m1+1] != '(') {
        err = "Op 3: Pattern mismatch";
        return false;
    }

    int m2 = findMatch(s, m1+1);  // ((B)C)
    if (m2 < 0 || m1 + 2 >= (int)s.length() || s[m1+2] != '(') {
        err = "Op 3: Pattern mismatch";
        return false;
    }

    int m3 = findMatch(s, m1+2);  // (B)
    if (m3 < 0 || m3 > m2 - 1) {
        err = "Op 3: Pattern mismatch";
        return false;
    }

    string A = extract(s, pos+1, m1-1);
    string B = extract(s, m1+3, m3-1);
    string C = extract(s, m3+1, m2-1);

    string replacement = "((" + A + ")" + B + ")(" + C + ")";
    s = s.substr(0, pos) + replacement + s.substr(m2+1);
    return true;
}

// Try to apply operation 4: p(A)(B)(C)q -> p((A)B)(C)q
bool tryOp4(string& s, int pos, string& err) {
    if (pos < 0 || pos >= (int)s.length() || s[pos] != '(') {
        err = "Op 4: Invalid position";
        return false;
    }

    int m1 = findMatch(s, pos);  // (A)
    if (m1 < 0 || m1 + 1 >= (int)s.length() || s[m1+1] != '(') {
        err = "Op 4: Pattern mismatch - no (B) after (A)";
        return false;
    }

    int m2 = findMatch(s, m1+1);  // (B)
    if (m2 < 0 || m2 + 1 >= (int)s.length() || s[m2+1] != '(') {
        err = "Op 4: Pattern mismatch - no (C) after (B)";
        return false;
    }

    int m3 = findMatch(s, m2+1);  // (C)
    if (m3 < 0) {
        err = "Op 4: Pattern mismatch - invalid (C)";
        return false;
    }

    string A = extract(s, pos+1, m1-1);
    string B = extract(s, m1+2, m2-1);
    string C = extract(s, m2+2, m3-1);

    string replacement = "((" + A + ")" + B + ")(" + C + ")";
    s = s.substr(0, pos) + replacement + s.substr(m3+1);
    return true;
}

// An implicit treap stores the sequence plus prefix-balance minima. Matching a
// parenthesis and moving a character both take expected O(log n), instead of
// scanning/copying a length-2n string for each of up to 3n operations.
class ParenSequence {
    struct Node {
        int left = 0, right = 0, size = 1, sum, minimum, value;
        uint32_t priority;
    };
    vector<Node> nodes;
    uint32_t random_state = 0x9e3779b9U;
    int root = 0;
    int sizeOf(int id) const { return id ? nodes[id].size : 0; }
    int sumOf(int id) const { return id ? nodes[id].sum : 0; }
    int minimumOf(int id) const { return id ? nodes[id].minimum : 1000000000; }
    void update(int id) {
        auto& node = nodes[id];
        int prefix = sumOf(node.left) + node.value;
        node.size = sizeOf(node.left) + 1 + sizeOf(node.right);
        node.sum = prefix + sumOf(node.right);
        node.minimum = min({minimumOf(node.left), prefix, prefix + minimumOf(node.right)});
    }
    int create(char value) {
        random_state ^= random_state << 13;
        random_state ^= random_state >> 17;
        random_state ^= random_state << 5;
        int balance = value == '(' ? 1 : -1;
        nodes.push_back({0, 0, 1, balance, balance, balance, random_state});
        return (int)nodes.size() - 1;
    }
    int merge(int left, int right) {
        if (!left || !right) return left ? left : right;
        if (nodes[left].priority > nodes[right].priority) {
            nodes[left].right = merge(nodes[left].right, right);
            update(left);return left;
        }
        nodes[right].left = merge(left, nodes[right].left);
        update(right);return right;
    }
    void split(int id, int count, int& left, int& right) {
        if (!id) { left = right = 0;return; }
        if (sizeOf(nodes[id].left) >= count) {
            right = id;
            split(nodes[id].left, count, left, nodes[id].left);
        } else {
            left = id;
            split(nodes[id].right, count - sizeOf(nodes[id].left) - 1, nodes[id].right, right);
        }
        update(id);
    }
    int firstClosing(int id, int balance) const {
        if (!id || balance + minimumOf(id) > 0) return -1;
        const auto& node = nodes[id];
        if (node.left && balance + minimumOf(node.left) <= 0) return firstClosing(node.left, balance);
        balance += sumOf(node.left) + node.value;
        if (balance <= 0) return sizeOf(node.left);
        int next = firstClosing(node.right, balance);
        return next < 0 ? -1 : sizeOf(node.left) + 1 + next;
    }
    void append(int id, string& output) const {
        if (!id) return;
        append(nodes[id].left, output);
        output += nodes[id].value == 1 ? '(' : ')';
        append(nodes[id].right, output);
    }
public:
    explicit ParenSequence(const string& source) {
        nodes.reserve(source.size() + 16);
        nodes.push_back({0, 0, 0, 0, 1000000000, 0, 0});
        for (char c : source) root = merge(root, create(c));
    }
    int length() const { return sizeOf(root); }
    char operator[](int position) const {
        if (position < 0 || position >= length()) return '\0';
        int id = root;
        while (true) {
            int left = sizeOf(nodes[id].left);
            if (position < left) id = nodes[id].left;
            else if (position == left) return nodes[id].value == 1 ? '(' : ')';
            else { position -= left + 1; id = nodes[id].right; }
        }
    }
    int match(int position) {
        if ((*this)[position] != '(') return -1;
        int left, right;split(root, position, left, right);
        int offset = firstClosing(right, 0);
        root = merge(left, right);
        return offset < 0 ? -1 : position + offset;
    }
    void move(int from, int to) {
        int left, tail, item, right;
        split(root, from, left, tail);split(tail, 1, item, right);
        root = merge(left, right);
        split(root, to, left, right);root = merge(merge(left, item), right);
    }
    void insertPair(int position) {
        int a = create('('), b = create(')'), left, right;
        int pair = merge(a, b);
        split(root, position, left, right);root = merge(merge(left, pair), right);
    }
    void erasePair(int position) {
        int left, tail, removed, right;
        split(root, position, left, tail);split(tail, 2, removed, right);
        root = merge(left, right);
    }
    string str() const { string output;output.reserve(length());append(root, output);return output; }
};

bool fastTransform(ParenSequence& s, int type, int pos, string& error) {
    auto reject = [&]() { error = "Op " + to_string(type) + ": Pattern mismatch";return false; };
    int m1 = s.match(pos);
    if (m1 < 0) return reject();
    if (type == 1 || type == 2) {
        if (s[pos + 1] != '(') return reject();
        int m2 = s.match(pos + 1);
        if (m2 < 0 || m2 >= m1) return reject();
        if (type == 1) {
            if (s[pos + 2] != '(') return reject();
            int m3 = s.match(pos + 2);
            if (m3 < 0 || m3 >= m2) return reject();
            s.move(pos + 2, m2);
        } else {
            if (s[m2 + 1] != '(') return reject();
            int m3 = s.match(m2 + 1);
            if (m3 < 0 || m3 >= m1) return reject();
            s.move(m2 + 1, m3);
        }
    } else {
        if (s[m1 + 1] != '(') return reject();
        int m2 = s.match(m1 + 1);
        if (m2 < 0) return reject();
        if (type == 3) {
            if (s[m1 + 2] != '(') return reject();
            int m3 = s.match(m1 + 2);
            if (m3 < 0 || m3 >= m2) return reject();
            s.move(m1 + 1, pos + 1);s.move(m1 + 2, m3);
        } else {
            if (s[m2 + 1] != '(' || s.match(m2 + 1) < 0) return reject();
            s.move(m1 + 1, pos + 1);
        }
    }
    return true;
}

bool applyOperations(const string& s1, const string& s2,
                     const vector<pair<int, int>>& ops,
                     int& op5_count, int& op6_count, string& errorMsg) {
    ParenSequence current(s1);

    for (size_t i = 0; i < ops.size(); i++) {
        int opType = ops[i].first;
        int pos = ops[i].second;

        if (opType == 5) {
            op5_count++;
            if (pos < 0 || pos > (int)current.length()) {
                errorMsg = "Op 5: Invalid position " + to_string(pos);
                return false;
            }
            current.insertPair(pos);

        } else if (opType == 6) {
            op6_count++;
            if (pos < 0 || pos >= (int)current.length() - 1) {
                errorMsg = "Op 6: Invalid position " + to_string(pos);
                return false;
            }
            if (current[pos] != '(' || current[pos + 1] != ')') {
                errorMsg = "Op 6: No '()' at position " + to_string(pos);
                return false;
            }
            current.erasePair(pos);

        } else if (opType >= 1 && opType <= 4) {
            bool success = fastTransform(current, opType, pos, errorMsg);

            if (!success) {
                errorMsg = "Step " + to_string(i+1) + ": " + errorMsg;
                return false;
            }
        } else {
            errorMsg = "Invalid operation type: " + to_string(opType);
            return false;
        }
    }

    string final = current.str();
    if (final != s2) {
        errorMsg = "Final mismatch. Expected: " + s2 + ", Got: " + final;
        return false;
    }

    return true;
}

int main(int argc, char* argv[]) {
    registerTestlibCmd(argc, argv);

    n = inf.readInt();
    string s1 = inf.readToken();
    string s2 = inf.readToken();

    if (!isValid(s1) || !isValid(s2)) {
        quitf(_fail, "Invalid input sequences");
    }

    int Q = ouf.readInt();
    if (Q < 0 || Q > 3 * n) {
        quitf(_wa, "Invalid Q: %d (must be 0 to %d)", Q, 3 * n);
    }

    vector<pair<int, int>> operations;
    for (int i = 0; i < Q; i++) {
        int opType = ouf.readInt();
        int pos = ouf.readInt();

        if (opType < 1 || opType > 6) {
            quitf(_wa, "Invalid operation type: %d", opType);
        }

        operations.push_back({opType, pos});
    }

    int op5_count = 0, op6_count = 0;
    string errorMsg;
    bool success = applyOperations(s1, s2, operations, op5_count, op6_count, errorMsg);

    if (op5_count > 2) {
        quitf(_wa, "Too many Op 5: %d (max: 2)", op5_count);
    }
    if (op6_count > 2) {
        quitf(_wa, "Too many Op 6: %d (max: 2)", op6_count);
    }

    if (!success) {
        quitf(_wa, "%s", errorMsg.c_str());
    }

    // Calculate score
    double threshold_full = 1.9 * n;  // Full score threshold
    double threshold_zero = 3.0 * n;  // Zero score threshold

    // Calculate raw score using linear interpolation
    // Raw score can be > 1.0 (when Q < threshold_full) or < 0.0 (when Q > threshold_zero)
    double raw_score = (threshold_zero - Q) / (threshold_zero - threshold_full);

    // Unbounded score: allow values > 1.0, but clip at 0.0
    double unbounded_score = calibrated(raw_score);

    // Bounded score: clip to [0.0, 1.0] for submission score
    double score = unbounded_score;
    score = natural_log_score(100.0L * (score), Q, threshold_full, true) / 100.0;
    unbounded_score = score;

    quitp(score, "Operations: %d, Ratio: %.12lf, RatioUnbounded: %.12lf", Q, score, unbounded_score);

    return 0;
}
