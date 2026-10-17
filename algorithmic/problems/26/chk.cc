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

#include<bits/stdc++.h>
#include <ext/rope>
#include "testlib.h"
using namespace std;

// Calibrate a feasible performance reference to 60 percent.
static double referenceScore(double ratio) {
    return ratio <= 1.0 ? 0.6 * ratio : (0.6 + 0.02 * std::log(ratio));
}

int n;
// A balanced rope supports moves without copying the whole permutation.
// The former vector erase/insert implementation took O(n * number_of_moves),
// causing checker TLE on valid answers for the released n=300000 cases.
bool validateMoves(const vector<int>& perm, const vector<pair<int, int>>& moves, long long& totalCost) {
    __gnu_cxx::rope<int> sequence(perm.data(), perm.size());
    totalCost = 0;
    for (const auto& move : moves) {
        int x = move.first, y = move.second;
        if (x < 1 || x > (int)perm.size() || y < 1 || y > (int)perm.size()) return false;
        int element = sequence[x - 1];
        sequence.erase(x - 1, 1);
        // y is the position after removal, exactly as in the original checker.
        sequence.insert(y - 1, element);
        totalCost += y;
    }
    int expected = 1;
    for (auto it = sequence.const_begin(); it != sequence.const_end(); ++it) {
        if (*it != expected++) return false;
    }
    return true;
}

int main(int argc, char* argv[]) {
    registerTestlibCmd(argc, argv);
    n = inf.readInt();
    vector<int> original_perm(n);
    for (int i = 0; i < n; i++) {
        original_perm[i] = inf.readInt();
    }
    long long best_answer = ans.readLong();
    if (best_answer <= 0) quitf(_fail, "Reference cost must be positive");
    long long participant_cost;
    int len_moves;
    vector<pair<int, int>> moves;
    if (ouf.seekEof()) {
        quitf(_wa, "No output provided");
    }
    participant_cost = ouf.readLong();
    len_moves = ouf.readInt();
    if (len_moves < 0) {
        quitf(_wa, "Number of moves cannot be negative: %d", len_moves);
    }
    for (int i = 0; i < len_moves; i++) {
        if (ouf.seekEof()) {
            quitf(_wa, "Expected %d moves, but only found %d", len_moves, i);
        }
        int x = ouf.readInt();
        int y = ouf.readInt();
        if (x < 1 || x > n || y < 1 || y > n) {
            quitf(_wa, "Invalid move %d: x=%d, y=%d (must be between 1 and %d)", i+1, x, y, n);
        }
        moves.push_back({x, y});
    }
    if (!ouf.seekEof()) {
        quitf(_wa, "Extra output found after %d moves", len_moves);
    }
    long long actual_cost;
    if (!validateMoves(original_perm, moves, actual_cost)) {
        quitf(_wa, "The given sequence of moves does not sort the permutation");
    }
    if ((__int128)(actual_cost + 1) * ((long long)len_moves + 1) != participant_cost) {
        quitf(_wa, "Claimed cost %lld does not match actual cost %lld from moves", participant_cost, actual_cost);
    }
    double score_ratio = referenceScore((double)best_answer / participant_cost);
    score_ratio = natural_log_score(100.0 * score_ratio, participant_cost, best_answer, true) / 100.0;
    double unbounded_score_ratio = score_ratio;
    quitp(score_ratio, "Cost: %lld. Ratio: %.12f, RatioUnbounded: %.12f", participant_cost, score_ratio, unbounded_score_ratio);
    return 0;
}
