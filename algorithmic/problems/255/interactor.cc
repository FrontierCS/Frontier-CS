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
#include <cmath>

static double referenceScore(double r) {
    return r <= 1.0 ? 0.6 * r : 0.6 + 0.02 * std::log(r);
}

#include <vector>
#include <iostream>
#include <cmath>
#include <algorithm>
#include <string>
#include <set>
#include <numeric>

using namespace std;

// Value mapping: N -> 1, S -> -1, - -> 0
int get_mag_val(char c) {
    if (c == 'N') return 1;
    if (c == 'S') return -1;
    return 0; // c == '-'
}

int main(int argc, char* argv[]) {
    // Initialize testlib
    setName("Interactor for Magnets Problem with Independent & Unbounded Scoring");
    registerInteraction(argc, argv);

    // Read number of test cases
    int t = inf.readInt(1, 100, "t");
    cout << t << endl;

    // Global accumulators for final quitp
    long long tot_moves = 0;
    double total_bounded_score = 0.0;
    double total_unbounded_score = 0.0;

    for (int case_idx = 0; case_idx < t; ++case_idx) {
        // --- Read Case Data ---
        int n = inf.readInt(3, 2000, "n");
        string s = inf.readToken("[NS-]{3,2000}", "s");

        cout << n << endl;

        // --- Define Dynamic Bounds for this Case ---
        // K_base: Limit for full score (and starting point for bonus)
        // K_zero: Limit for zero score

        double k_base = (double)(n / 2);
        double k_zero = (double)(2 * n);

        // Parse magnet types
        vector<int> vals(n + 1);
        vector<int> expected_ans;
        for (int i = 0; i < n; ++i) {
            vals[i + 1] = get_mag_val(s[i]);
            if (s[i] == '-') {
                expected_ans.push_back(i + 1);
            }
        }

        bool solved = false;
        long long case_queries = 0;

        // --- Interaction Loop ---
        while (!solved) {
            string type = ouf.readToken("[?!]");

            if (type == "?") {
                case_queries++;

                int l = ouf.readInt(1, n - 1, "l");
                int r = ouf.readInt(1, n - 1, "r");

                if (l + r > n) {
                    quitf(_wa, "Test case %d: Invalid query sizes l=%d, r=%d, n=%d", case_idx + 1, l, r, n);
                }

                vector<int> left_indices(l);
                set<int> used_indices;
                int sum_left = 0;

                for (int i = 0; i < l; ++i) {
                    left_indices[i] = ouf.readInt(1, n, "left_idx");
                    if (used_indices.count(left_indices[i])) {
                        quitf(_wa, "Test case %d: Duplicate index %d in left set", case_idx + 1, left_indices[i]);
                    }
                    used_indices.insert(left_indices[i]);
                    sum_left += vals[left_indices[i]];
                }

                int sum_right = 0;
                for (int i = 0; i < r; ++i) {
                    int idx = ouf.readInt(1, n, "right_idx");
                    if (used_indices.count(idx)) {
                        quitf(_wa, "Test case %d: Index %d appears in both sets or duplicates", case_idx + 1, idx);
                    }
                    used_indices.insert(idx);
                    sum_right += vals[idx];
                }

                long long force = (long long)sum_left * sum_right;

                if (abs(force) > 1) {
                    quitf(_wa, "Test case %d: Machine crashed! Force was %lld", case_idx + 1, force);
                }

                cout << force << endl;

            } else if (type == "!") {
                int k = ouf.readInt(0, n, "k");
                vector<int> user_ans;
                for(int i = 0; i < k; ++i) {
                    user_ans.push_back(ouf.readInt(1, n, "ans_idx"));
                }

                sort(user_ans.begin(), user_ans.end());

                if (user_ans.size() != expected_ans.size()) {
                    quitf(_wa, "Test case %d: Wrong number of magnets. Expected %d, found %d",
                          case_idx + 1, (int)expected_ans.size(), (int)user_ans.size());
                }

                for(size_t i = 0; i < expected_ans.size(); ++i) {
                    if (user_ans[i] != expected_ans[i]) {
                         quitf(_wa, "Test case %d: Incorrect magnets found.", case_idx + 1);
                    }
                }

                solved = true;
            }
        }

        tot_moves += case_queries;

        // --- Calculate Independent Score for Case ---

        // Prepare term: (K_zero - Q) / (K_zero - K_base)
        double q = (double)case_queries;
        double term = 0.0;
        double den = k_zero - k_base;
        if (den < 1e-9) den = 1.0; // Safety

        if (q < k_zero) {
            term = (k_zero - q) / den;
        } else {
            term = 0.0;
        }

        double case_bounded = referenceScore(term * term);
        case_bounded = natural_log_score(100.0L * (case_bounded), case_queries, k_base, true) / 100.0;
        double case_unbounded = case_bounded;

        total_bounded_score += case_bounded;
        total_unbounded_score += case_unbounded;
    }

    // --- Final Verdict ---
    // Average scores over all test cases
    double score_ratio = total_bounded_score / (double)t;
    double unbounded_score_ratio = total_unbounded_score / (double)t;

    // Strict quitp format as requested
    quitp(score_ratio, "Queries: %lld. Ratio: %.12f, RatioUnbounded: %.12f", tot_moves, score_ratio, unbounded_score_ratio);

    return 0;
}
