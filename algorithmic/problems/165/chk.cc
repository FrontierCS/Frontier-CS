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

static long long completed_cost = 0;
static bool objective_complete = false;

#include "testlib.h"
#include <bits/stdc++.h>
using namespace std;

struct InputData {
    int n, m;
    int si, sj;
    vector<string> a;
    vector<string> t;
};

static bool is_uppercase_str(const string& s) {
    for (char c : s) if (!(c >= 'A' && c <= 'Z')) return false;
    return true;
}

static long long compute_score(const InputData& in, const vector<pair<int,int>>& out) {
    long long cost = 0;
    int pr = in.si, pc = in.sj;
    string S;
    S.reserve(out.size());

    for (auto [r, c] : out) {
        cost += llabs(pr - r) + llabs(pc - c) + 1;
        pr = r; pc = c;
        S.push_back(in.a[r][c]);
    }

    int K = 0;
    for (const string& w : in.t) {
        if (S.find(w) != string::npos) ++K;
    }

    if (K == in.m) {
        objective_complete = true;
        completed_cost = cost;
        long long sc = 10000 - cost;
        if (sc < 1001) sc = 1001;
        return sc;
    } else {
        double val = 1000.0 * double(K + 1) / double(in.m);
        long long sc = llround(val);
        return sc;
    }
}

int main(int argc, char* argv[]) {
    registerTestlibCmd(argc, argv);

    // Parse input
    InputData in;
    in.n = inf.readInt();
    in.m = inf.readInt();
    in.si = inf.readInt(0, in.n - 1);
    in.sj = inf.readInt(0, in.n - 1);

    in.a.resize(in.n);
    for (int i = 0; i < in.n; ++i) {
        in.a[i] = inf.readToken();
        ensuref((int)in.a[i].size() == in.n, "Grid row %d must have length %d", i, in.n);
        ensuref(is_uppercase_str(in.a[i]), "Grid row %d must contain only uppercase letters", i);
    }

    in.t.resize(in.m);
    for (int k = 0; k < in.m; ++k) {
        in.t[k] = inf.readToken();
        ensuref((int)in.t[k].size() == 5, "t[%d] must have length 5", k);
        ensuref(is_uppercase_str(in.t[k]), "t[%d] must contain only uppercase letters", k);
    }

    // Parse output
    vector<pair<int,int>> out;
    out.reserve(5000);
    while (!ouf.seekEof()) {
        int r = ouf.readInt(0, in.n - 1);
        int c = ouf.readInt(0, in.n - 1);
        out.emplace_back(r, c);
        if (out.size() > 5000u) {
            quitf(_wa, "Too many output moves: %zu > 5000", out.size());
        }
    }

    // Compute score
    long long score = compute_score(in, out);

    long long baseline_value = ans.readLong();
    long long best_value = ans.readLong();

    // External calibration anchors do not limit the feasible raw objective.
    double gap = (double)best_value - (double)baseline_value;
    ensuref(gap > 0.0, "Invalid calibration anchors");
    double calibration_ratio = max(0.0, ((double)score - (double)baseline_value) / gap);
    double score_ratio = 0.6 * calibration_ratio;
    if (objective_complete && completed_cost == 0) score_ratio = 1.0;
    else if (objective_complete && best_value >= 1001 && best_value < 10000) {
        score_ratio = natural_log_score(100.0*score_ratio, completed_cost, 10000.0L-best_value, true)/100.0;
    } else score_ratio = natural_log_score(100.0*score_ratio, score, best_value, false)/100.0;
    quitp(score_ratio, "Value: %lld. Ratio: %.12f, RatioUnbounded: %.12f", score, score_ratio, score_ratio);
}
