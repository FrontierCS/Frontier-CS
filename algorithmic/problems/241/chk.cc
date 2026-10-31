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

#include "testlib.h"
#include <string>
#include <vector>
#include <algorithm>
#include <cmath>
#include <iostream>
#include <limits>

using namespace std;

// Calibrate a feasible performance reference to 60 percent.
static double referenceScore(double ratio) {
    return ratio <= 1.0 ? 0.6 * ratio : (0.6 + 0.02 * std::log(ratio));
}

// Use unsigned long long for bit compression, storing 64 bits per block
typedef unsigned long long u64;

struct BitVector {
    vector<u64> blocks;
    int length;  // Actual bit length

    void init(int n) {
        length = 1 << n;
        int blockCount = (length + 63) / 64;
        blocks.assign(blockCount, 0);
    }

    // Set the value of a specific bit
    void set(int idx, bool val) {
        if (val) {
            blocks[idx / 64] |= (1ULL << (idx % 64));
        } else {
            blocks[idx / 64] &= ~(1ULL << (idx % 64));
        }
    }

    // Get the value of a specific bit (for final comparison)
    bool get(int idx) const {
        return (blocks[idx / 64] >> (idx % 64)) & 1;
    }
};

// Expression tree node
struct Node {
    enum Type { CONST, VAR, OP } type;
    bool boolVal;   // For CONST type
    int varIdx;     // For VAR type
    char opType;    // For OP type
    Node *left = nullptr, *right = nullptr;

    Node(bool v) : type(CONST), boolVal(v) {}
    Node(int idx) : type(VAR), varIdx(idx) {}
    Node(char op, Node* l, Node* r) : type(OP), opType(op), left(l), right(r) {}

    ~Node() {
        if (left) delete left;
        if (right) delete right;
    }
};

string exprStr;
int pos;
int maxDepth;
int currentDepth;
int opCount;
int N;  // Current test case's n

// Precompute truth tables for all variables to avoid repeated calculations
// varMasks[i] stores the truth table for variable i (0='a')
vector<BitVector> varMasks;

void parseError(string msg) {
    quitf(_wa, "Invalid expression format: %s", msg.c_str());
}

// Parser
Node* parse() {
    if (pos >= exprStr.length()) parseError("Unexpected end of string");

    char c = exprStr[pos];
    currentDepth++;
    maxDepth = max(maxDepth, currentDepth);
    Node* node = nullptr;

    if (c == 'T') {
        node = new Node(true);
        pos++;
    } else if (c == 'F') {
        node = new Node(false);
        pos++;
    } else if (c >= 'a' && c <= 'z') {
        int idx = c - 'a';
        if (idx >= N) parseError("Variable index out of range for this N");
        node = new Node(idx);
        pos++;
    } else if (c == '(') {
        pos++;
        Node* left = parse();
        if (pos >= exprStr.length()) parseError("Missing operator");
        char op = exprStr[pos];
        if (op != '&' && op != '|') parseError("Expected & or |");
        opCount++;
        pos++;
        Node* right = parse();
        if (pos >= exprStr.length() || exprStr[pos] != ')') parseError("Missing closing parenthesis");
        pos++;
        node = new Node(op, left, right);
    } else {
        parseError("Unexpected character");
    }
    currentDepth--;
    return node;
}

// Evaluate the entire tree in parallel
// Returns a BitVector containing 2^n results
BitVector evaluate_parallel(Node* node) {
    BitVector res;
    res.init(N);  // Allocate space

    if (node->type == Node::CONST) {
        // If constant, all 0s or all 1s
        u64 val = node->boolVal ? ~0ULL : 0ULL;
        for (size_t i = 0; i < res.blocks.size(); i++) {
            res.blocks[i] = val;
        }
    } else if (node->type == Node::VAR) {
        // Directly return precomputed variable truth table
        return varMasks[node->varIdx];
    } else {
        BitVector l = evaluate_parallel(node->left);
        BitVector r = evaluate_parallel(node->right);

        // Parallel bitwise operations
        for (size_t i = 0; i < res.blocks.size(); i++) {
            if (node->opType == '&') {
                res.blocks[i] = l.blocks[i] & r.blocks[i];
            } else {
                res.blocks[i] = l.blocks[i] | r.blocks[i];
            }
        }
    }
    return res;
}

int countOps(const string& s) {
    int cnt = 0;
    for (char c : s) if (c == '&' || c == '|') cnt++;
    return cnt;
}

// Precompute truth tables for N variables
void precomputeVarMasks(int n) {
    varMasks.clear();
    varMasks.resize(n);
    int totalLen = 1 << n;

    for (int i = 0; i < n; i++) {
        varMasks[i].init(n);
        // Variable i has period 2^(i+1), with first 2^i being 0, next 2^i being 1
        int interval = 1 << i;
        for (int k = 0; k < totalLen; k++) {
            // Check if the i-th bit of k is 1
            bool val = (k >> i) & 1;
            varMasks[i].set(k, val);
        }
    }
}

int main(int argc, char* argv[]) {
    registerTestlibCmd(argc, argv);

    int T = inf.readInt();
    double minScoreRatio = numeric_limits<double>::infinity();

    for (int t = 1; t <= T; t++) {
        setTestCase(t);
        N = inf.readInt();
        string truthTable = inf.readToken();

        string userAns = ouf.readToken();
        string juryAns = ans.readToken();

        if (userAns != juryAns) {
            quitf(_wa, "Test case %d: Verdict mismatch.", t);
        }

        if (userAns == "No") {
            // This is a correctness-only case, not a performance reference.
            minScoreRatio = min(minScoreRatio, 1.0);
            continue;
        }

        string userExpr = ouf.readToken();
        string juryExpr = ans.readToken();

        // 1. Parse expression
        exprStr = userExpr;
        pos = 0; maxDepth = 0; currentDepth = 0; opCount = 0;

        Node* root = nullptr;
        try {
            root = parse();
            if (pos != exprStr.length()) {
                delete root;
                quitf(_wa, "Test case %d: Extra characters after expression", t);
            }
        } catch (...) {
            if (root) delete root;
            quitf(_wa, "Test case %d: Parser error", t);
        }

        if (maxDepth > 100) {
            delete root;
            quitf(_wa, "Test case %d: Expression depth %d exceeds maximum 100", t, maxDepth);
        }

        // 2. Precompute variable truth tables (O(n * 2^n)), very fast
        // For N=15, approximately 15 * 32768 operations, negligible
        precomputeVarMasks(N);

        // 3. Evaluate in parallel (O(|Expr| * 2^n / 64))
        BitVector resultMask = evaluate_parallel(root);
        delete root;

        // 4. Verify result against truth table
        int limit = 1 << N;
        for (int i = 0; i < limit; i++) {
            bool val = resultMask.get(i);
            int expected = truthTable[i] - '0';
            if (val != expected) {
                quitf(_wa, "Test case %d: Truth table mismatch at index %d (expected %d, got %d)", t, i, expected, val);
            }
        }

        // 5. Calculate score for this test case
        int userOps = opCount;
        int juryOps = countOps(juryExpr);
        double caseScore = 0.0;

        if (juryOps == 0) {
            caseScore = (userOps == 0) ? 1.0 : 0.0;
        } else {
            double ratio = max(0.0, (2.0 * juryOps - userOps) / juryOps);
            caseScore = referenceScore(ratio);
        }
        caseScore = natural_log_score(100.0L * (caseScore), userOps, juryOps, true) / 100.0;
        minScoreRatio = min(minScoreRatio, caseScore);
    }

    // Calculate final score ratio (minimum across all test cases)
    double score_ratio = minScoreRatio;
    double unbounded_ratio = score_ratio;

    // Use standard quitp format
    quitp(score_ratio, "Value: %.4f. Ratio: %.12f, RatioUnbounded: %.12f", score_ratio, score_ratio, unbounded_ratio);

    return 0;
}
