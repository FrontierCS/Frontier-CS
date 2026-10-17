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

struct DSU {
    int n;
    vector<int> p, sz;
    DSU(int n = 0) { init(n); }
    void init(int n_) {
        n = n_;
        p.resize(n);
        sz.assign(n, 1);
        iota(p.begin(), p.end(), 0);
    }
    int find(int a) {
        if (p[a] == a) return a;
        return p[a] = find(p[a]);
    }
    bool unite(int a, int b) {
        a = find(a); b = find(b);
        if (a == b) return false;
        if (sz[a] < sz[b]) swap(a, b);
        p[b] = a;
        sz[a] += sz[b];
        return true;
    }
    bool same(int a, int b) { return find(a) == find(b); }
};

struct InputData {
    int n, m, k;
    vector<pair<int,int>> stations;       // (x, y)
    vector<tuple<int,int,long long>> edges; // (u, v, w) 0-based
    vector<pair<int,int>> residents;      // (a, b)
};

struct OutputData {
    vector<int> powers;     // size n, 0..5000
    vector<int> edgeOn;     // size m, 0 or 1
};

static long long computeScore(const InputData& in, const OutputData& out) {
    // Connectivity from node 0 using edges ON
    DSU dsu(in.n);
    for (int j = 0; j < in.m; j++) {
        if (out.edgeOn[j]) {
            int u = std::get<0>(in.edges[j]);
            int v = std::get<1>(in.edges[j]);
            dsu.unite(u, v);
        }
    }
    vector<char> connected(in.n, 0);
    for (int i = 0; i < in.n; i++) connected[i] = dsu.same(0, i);

    // Broadcast coverage
    vector<char> covered(in.k, 0);
    for (int i = 0; i < in.n; i++) {
        if (!connected[i]) continue;
        long long p = out.powers[i];
        long long p2 = p * p;
        long long sx = in.stations[i].first;
        long long sy = in.stations[i].second;
        for (int k = 0; k < in.k; k++) {
            if (covered[k]) continue;
            long long rx = in.residents[k].first;
            long long ry = in.residents[k].second;
            long long dx = sx - rx;
            long long dy = sy - ry;
            long long d2 = dx * dx + dy * dy;
            if (d2 <= p2) covered[k] = 1;
        }
    }
    long long ncovered = 0;
    for (int k = 0; k < in.k; k++) if (covered[k]) ncovered++;

    if (ncovered < in.k) {
        double val = 1e6 * double(ncovered + 1) / double(in.k);
        return llround(val);
    } else {
        long long S = 0;
        for (int i = 0; i < in.n; i++) {
            long long p = out.powers[i];
            S += p * p;
        }
        for (int j = 0; j < in.m; j++) {
            if (out.edgeOn[j]) {
                S += std::get<2>(in.edges[j]);
            }
        }
        double val = 1e6 * (1.0 + 1e8 / (double(S) + 1e7));
        objective_complete = true;
        completed_cost = S;
        return llround(val);
    }
}

int main(int argc, char* argv[]) {
    registerTestlibCmd(argc, argv);

    // Read input
    InputData in;
    in.n = inf.readInt();
    in.m = inf.readInt();
    in.k = inf.readInt();
    in.stations.resize(in.n);
    for (int i = 0; i < in.n; i++) {
        int x = inf.readInt();
        int y = inf.readInt();
        in.stations[i] = {x, y};
    }
    in.edges.resize(in.m);
    for (int j = 0; j < in.m; j++) {
        int u = inf.readInt();
        int v = inf.readInt();
        long long w = inf.readLong();
        // Convert to 0-based
        --u; --v;
        in.edges[j] = make_tuple(u, v, w);
    }
    in.residents.resize(in.k);
    for (int i = 0; i < in.k; i++) {
        int a = inf.readInt();
        int b = inf.readInt();
        in.residents[i] = {a, b};
    }

    // Parse output: possibly multiple solutions, only last counts
    vector<OutputData> outs;
    while (!ouf.seekEof()) {
        OutputData out;
        out.powers.resize(in.n);
        for (int i = 0; i < in.n; i++) {
            out.powers[i] = ouf.readInt(0, 5000);
        }
        out.edgeOn.resize(in.m);
        for (int j = 0; j < in.m; j++) {
            out.edgeOn[j] = ouf.readInt(0, 1);
        }
        outs.push_back(std::move(out));
    }

    if (outs.empty()) {
        quitf(_wa, "empty output");
    }

    const OutputData& last = outs.back();
    long long score = computeScore(in, last);
    long long baseline_value = ans.readLong();
    long long best_value = ans.readLong();

    // External calibration anchors do not limit the feasible raw objective.
    double gap = (double)best_value - (double)baseline_value;
    // A dominated reference cannot define a decreasing quality scale.
    bool theoretical_anchor = gap <= 0.0;
    if (theoretical_anchor) gap = 11000000.0 - (double)baseline_value;
    ensuref(gap > 0.0, "Invalid calibration anchors");
    double calibration_ratio = max(0.0, ((double)score - (double)baseline_value) / gap);
    double score_ratio = calibration_ratio <= 1.0 ? 0.6 * calibration_ratio : 0.6 + 0.02 * log(calibration_ratio);
    if (theoretical_anchor) score_ratio = min(1.0, calibration_ratio);
    const long double value_anchor = theoretical_anchor ? (long double)baseline_value + 0.6L*gap : (long double)best_value;
    if (objective_complete && completed_cost == 0) score_ratio = 1.0;
    else if (objective_complete && value_anchor > 1e6L && value_anchor < 11e6L) {
        const long double cost_anchor = 1e8L/(value_anchor/1e6L-1.0L)-1e7L;
        score_ratio = natural_log_score(100.0*score_ratio, completed_cost, cost_anchor, true)/100.0;
    } else score_ratio = natural_log_score(100.0*score_ratio, score, value_anchor, false)/100.0;
    quitp(score_ratio, "Value: %lld. Ratio: %.12f, RatioUnbounded: %.12f", score, score_ratio, score_ratio);
}
