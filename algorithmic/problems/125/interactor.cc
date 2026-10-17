#include <cmath>
#include <algorithm>

// Scores are in points here. Preserve the previous lower band, and compare
// the original objective with its 60-point anchor using the natural logarithm.
static double natural_log_score(double old_points, long double value,
                                long double anchor, bool minimize) {
    if (minimize && value == 0.0L) return 100.0;
    if (old_points <= 60.0) return old_points;
    // A zero reference or a flat legacy score has no positive logarithmic anchor.
    if (!(value > 0.0L) || !(anchor > 0.0L)) return old_points;
    const long double gain = minimize ? std::log(anchor) - std::log(value)
                                      : std::log(value) - std::log(anchor);
    return static_cast<double>(std::min(100.0L, 60.0L + gain));
}

#include "testlib.h"

static double referenceScore(double r) {
    return r <= 1.0 ? 0.6 * r : 0.6 + 0.02 * std::log(r);
}

#include <bits/stdc++.h>
using namespace std;

// ---------- helpers ----------
static inline bool parse_ll(const string& s, long long& x) {
    if (s.empty()) return false;
    size_t i = 0;
    if (s[0] == '+' || s[0] == '-') i = 1;
    if (i == s.size()) return false;
    for (; i < s.size(); ++i) if (s[i] < '0' || s[i] > '9') return false;
    try {
        size_t pos = 0; long long v = stoll(s, &pos, 10);
        if (pos != s.size()) return false; x = v; return true;
    } catch (...) { return false; }
}
static inline bool parse_int32(const string& s, int& x) {
    long long t; if (!parse_ll(s, t)) return false;
    if (t < INT_MIN || t > INT_MAX) return false; x = (int)t; return true;
}

int main(int argc, char* argv[]) {
    setName("Mineral Pairing interactor (stdout version; WA on violations; ratio on AC; queries allowed after first '!')");
    registerInteraction(argc, argv);

    // ---- Problem constraints ----
    const int N_MIN = 1;
    const int N_MAX = 43000;
    const int QUERY_LIMIT = 1000000; // hard limit for answered '?' queries

    // ---- Read hidden instance from 'inf' ----
    int n = inf.readInt(N_MIN, N_MAX, "n");
    const int m = 2 * n;

    vector<int> kind(m + 1);
    for (int x = 1; x <= m; ++x) {
        kind[x] = inf.readInt(1, n, format("kind[%d]", x).c_str());
    }
    {
        vector<int> cnt(n + 1, 0);
        for (int x = 1; x <= m; ++x) ++cnt[kind[x]];
        for (int k = 1; k <= n; ++k) {
            ensuref(cnt[k] == 2, "Kind %d occurs %d times (expected exactly 2).", k, cnt[k]);
        }
    }

    // ---- Read optimal #queries from '.ans' ----
    int optimal_queries = ans.readInt(0, QUERY_LIMIT, "optimal_queries");

    // ---- Public output: announce n and FLUSH ----
    cout << n << '\n' << flush;

    // ---- Device state ----
    int queries = 0;                   // number of answered '?' queries
    vector<char> present(m + 1, 0);    // present[x] ? 1 : 0
    vector<int>  have(n + 1, 0);       // how many slices of kind k are present (0..2)
    int distinctKinds = 0;             // # of kinds k with have[k] > 0

    auto toggle = [&](int x) -> int {
        int k = kind[x];
        if (!present[x]) {
            present[x] = 1;
            if (have[k] == 0) ++distinctKinds;
            ++have[k];
        } else {
            present[x] = 0;
            --have[k];
            if (have[k] == 0) --distinctKinds;
        }
        return distinctKinds;
    };

    auto compute_ratio_unbounded = [&](int q_used, int q_opt) -> double {
        long long denom = 1000000LL - (long long)q_opt;
        long long numer = 1000000LL - (long long)q_used;
        if (denom <= 0) return 1000001.0 / (q_used + 1.0);
        double r = (double)numer / (double)denom;
        if (r < 0.0) r = 0.0;
        // if (r > 1.0) r = 1.0;
        return r;
    };

    auto accept_with_ratio = [&](int q_used) {
        double ratio_unbounded = compute_ratio_unbounded(q_used, optimal_queries);
        double ratio = optimal_queries == 0 ? ratio_unbounded : referenceScore(ratio_unbounded);
    ratio = natural_log_score(100.0 * ratio, q_used, optimal_queries == 0 ? 400000.0L : (long double)optimal_queries, true) / 100.0;
        ratio_unbounded = ratio;

        long long your_score = 1000000LL - (long long)q_used;
        long long opt_score  = 1000000LL - (long long)optimal_queries;
        quitp(ratio,
              "Accepted. Queries used: %d. Your score = 1000000 - %d = %lld. "
              "Optimal queries: %d. Optimal score = 1000000 - %d = %lld. Ratio: %.12f, RatioUnbounded: %.12f",
              q_used, q_used, your_score,
              optimal_queries, optimal_queries, opt_score, ratio, ratio_unbounded);
    };

    // ---- Final answer tracking ----
    vector<char> used(m + 1, 0);
    int answered_pairs = 0;

    try {
        while (true) {
            string cmd = ouf.readToken();

            if (cmd == "?") {
                string sx = ouf.readToken();
                int x = 0;
                if (!parse_int32(sx, x)) {
                    quitf(_pe, "Invalid query: expected integer for x, got '%s'.",
                          compress(sx).c_str());
                }
                if (x < 1 || x > m) {
                    quitf(_wa, "Query out of bounds: x=%d (valid range is [1,%d]).", x, m);
                }
                if (queries >= QUERY_LIMIT) {
                    quitf(_wa, "Too many queries: %d >= %d.", queries, QUERY_LIMIT);
                }
                int r = toggle(x);
                cout << r << '\n' << flush;
                ++queries;
            }
            else if (cmd == "!") {
                string sa = ouf.readToken();
                string sb = ouf.readToken();
                int a = 0, b = 0;
                if (!parse_int32(sa, a) || !parse_int32(sb, b)) {
                    quitf(_pe, "Invalid answer line: expected integers for a and b, got '%s' and '%s'.",
                          compress(sa).c_str(), compress(sb).c_str());
                }
                if (a < 1 || a > m || b < 1 || b > m) {
                    quitf(_wa, "Answer out of bounds: a=%d, b=%d (valid range is [1,%d]).", a, b, m);
                }
                if (a == b) {
                    quitf(_wa, "Wrong Answer: pair has identical indices (%d,%d). Queries used: %d.",
                          a, b, queries);
                }
                if (used[a] || used[b]) {
                    quitf(_wa, "Wrong Answer: repeated slice index in answers "
                               "(a=%d used=%d, b=%d used=%d). Queries used: %d.",
                          a, (int)used[a], b, (int)used[b], queries);
                }
                if (kind[a] != kind[b]) {
                    quitf(_wa, "Wrong Answer: slices %d and %d are different kinds (%d != %d). "
                               "Queries used: %d.",
                          a, b, kind[a], kind[b], queries);
                }

                used[a] = used[b] = 1;
                ++answered_pairs;

                if (answered_pairs == n) {
                    // Ensure every index covered exactly once
                    for (int x = 1; x <= m; ++x) {
                        if (!used[x]) {
                            quitf(_wa, "Wrong Answer: slice %d not covered by any pair. Queries used: %d.",
                                  x, queries);
                        }
                    }
                    // Accepted only here
                    accept_with_ratio(queries);
                }
            }
            else {
                quitf(_pe, "Expected '?' or '!' but got '%s'.", compress(cmd).c_str());
            }
        }
    } catch (const exception&) {
        // If stream ended before giving n pairs, that's a WA by statement.
        if (answered_pairs < n) {
            quitf(_wa, "Wrong number of answers: expected %d pairs, got %d.", n, answered_pairs);
        }
        throw;
    }
}
