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

// Historical calibration supplies the unchanged low-score branch.
static double referenceScore(double r) {
    return r <= 1.0 ? 0.6 * r : 0.6 + 0.02 * std::log(r);
}

#include <bits/stdc++.h>
using namespace std;

static const int MAX_N = 400;
static const int MAX_M = 25;

static inline string trim_str(const string &s) {
    size_t l = 0, r = s.size();
    while (l < r && isspace((unsigned char)s[l])) l++;
    while (r > l && isspace((unsigned char)s[r - 1])) r--;
    return s.substr(l, r - l);
}

int main(int argc, char* argv[]) {
    registerInteraction(argc, argv);

    // Read N and M from input file
    int N = inf.readInt(1, MAX_N, "N");
    int M = inf.readInt(1, MAX_M, "M");

    int total = N * M;

    // Read colors for each dango (1-indexed in problem, but stored 0-indexed in array)
    vector<int> color(total + 1);
    for (int i = 1; i <= total; i++) {
        color[i] = inf.readInt(1, N, format("color[%d]", i));
    }

    // Send N and M to contestant
    cout << N << " " << M << endl;
    cout.flush();

    long long query_count = 0;
    vector<bool> used(total + 1, false);
    int sticks_reported = 0;

    // Interactive loop
    while (sticks_reported < M) {
        // Read non-empty line, skip blanks and lines starting with '#'
        string line;
        do {
            // testlib's unbuffered reader retains every consumed character in
            // an int vector. Large query transcripts therefore exhausted the
            // interactor memory limit. Keep only the current protocol line.
            if (!std::getline(cin, line)) {
                quitf(_wa, "Participant output ended after %d of %d sticks", sticks_reported, M);
            }
            line = trim_str(line);
        } while (line.empty() || line[0] == '#');

        if (line[0] == '?') {
            // Query
            query_count++;

            istringstream iss(line.substr(1));
            int k;
            if (!(iss >> k)) {
                quitf(_wa, "invalid query format: missing k");
            }

            if (k < 0 || k > total) {
                quitf(_wa, "invalid query: k=%d out of range [0, %d]", k, total);
            }

            vector<int> indices(k);
            set<int> seen;
            for (int i = 0; i < k; i++) {
                if (!(iss >> indices[i])) {
                    quitf(_wa, "invalid query format: expected %d indices, got %d", k, i);
                }
                if (indices[i] < 1 || indices[i] > total) {
                    quitf(_wa, "invalid query: index %d out of range [1, %d]", indices[i], total);
                }
                if (seen.count(indices[i])) {
                    quitf(_wa, "invalid query: duplicate index %d", indices[i]);
                }
                seen.insert(indices[i]);
            }

            // Compute maximum number of sticks that can be formed
            // For each color, count how many dangos of that color are in the subset
            // The answer is the minimum count across all colors
            vector<int> cnt(N + 1, 0);
            for (int idx : indices) {
                cnt[color[idx]]++;
            }

            int max_sticks = INT_MAX;
            for (int c = 1; c <= N; c++) {
                max_sticks = min(max_sticks, cnt[c]);
            }
            if (max_sticks == INT_MAX) max_sticks = 0;

            cout << max_sticks << endl;
            cout.flush();

        } else if (line[0] == '!') {
            // Answer
            istringstream iss(line.substr(1));
            vector<int> stick_indices;
            int idx;
            while (iss >> idx) {
                stick_indices.push_back(idx);
            }

            if ((int)stick_indices.size() != N) {
                quitf(_wa, "stick %d has %d dangos, expected %d", sticks_reported + 1, (int)stick_indices.size(), N);
            }

            // Check validity
            set<int> colors_used;
            for (int i : stick_indices) {
                if (i < 1 || i > total) {
                    quitf(_wa, "invalid stick: index %d out of range [1, %d]", i, total);
                }
                if (used[i]) {
                    quitf(_wa, "invalid stick: dango %d already used in a previous stick", i);
                }
                if (colors_used.count(color[i])) {
                    quitf(_wa, "invalid stick: duplicate color %d in stick %d", color[i], sticks_reported + 1);
                }
                colors_used.insert(color[i]);
            }

            if ((int)colors_used.size() != N) {
                quitf(_wa, "invalid stick %d: does not contain all colors (got %d colors)", sticks_reported + 1, (int)colors_used.size());
            }

            // Mark as used
            for (int i : stick_indices) {
                used[i] = true;
            }

            sticks_reported++;

        } else {
            quitf(_wa, "invalid command: expected '?' or '!', got '%c'", line[0]);
        }
    }

    // Scoring based on query count
    // L = N * M (full score threshold)
    // Limit = 5 * N * M (zero score threshold)
    // If Q <= L: 100 points
    // If Q >= Limit: 0 points
    // Otherwise: floor(100 * (Limit - Q) / (Limit - L))

    long long L = (long long)N * M;
    long long Limit = 5LL * N * M;

    // Read baseline and best from .ans file
    long long baseline_query = ans.readLong();  // Limit (0 points threshold)
    long long best_query = ans.readLong();       // L (full points threshold)

    ensuref(0 <= best_query && best_query < baseline_query, "Invalid query reference/baseline");
    double r = max(0.0, double(baseline_query - query_count) / double(baseline_query - best_query));
    double score_ratio = referenceScore(r);
    score_ratio = natural_log_score(100.0L * (score_ratio), query_count, best_query, true) / 100.0;
    double unbounded_ratio = score_ratio;

    quitp(score_ratio, "Queries: %lld. Ratio: %.12f, RatioUnbounded: %.12f", query_count, score_ratio, unbounded_ratio);
    return 0;
}
