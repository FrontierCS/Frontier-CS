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

// Historical bounded base ratio; only its <=60-point branch is retained.
static double bounded_base_ratio(double s) {
    return std::max(0.0, std::min(1.0, s));
}

#include "testlib.h"
#include <bits/stdc++.h>
using namespace std;

static inline int bit(char c) { return c == 'B'; }

static long long simulateCost(
    const vector<vector<int>>& g,
    const vector<int>& initCol,
    const vector<int>& order0 // 0-based permutation
) {
    int n = (int)g.size();
    vector<int> col = initCol;
    vector<char> removed(n, 0);

    long long black = 0;
    for (int i = 0; i < n; i++) black += col[i];

    long long cost = 0;
    for (int t = 0; t < n; t++) {
        int u = order0[t];
        // Order validity (duplicates/out of range) is checked elsewhere, but keep safe:
        if (u < 0 || u >= n || removed[u]) return (1LL << 62);

        cost += black;

        if (col[u]) black--;
        removed[u] = 1;

        for (int v : g[u]) if (!removed[v]) {
            if (col[v]) { col[v] = 0; black--; }
            else        { col[v] = 1; black++; }
        }
    }
    return cost;
}

static vector<int> baselineBfsOrder(const vector<vector<int>>& g) {
    int n = (int)g.size();
    vector<int> order;
    order.reserve(n);
    vector<char> vis(n, 0);
    queue<int> q;
    vis[0] = 1;
    q.push(0);
    while (!q.empty()) {
        int u = q.front(); q.pop();
        order.push_back(u);
        for (int v : g[u]) if (!vis[v]) {
            vis[v] = 1;
            q.push(v);
        }
    }
    // Tree is connected, so order size must be n
    return order;
}

int main(int argc, char** argv) {
    registerTestlibCmd(argc, argv);

    int N = inf.readInt(1, 200000, "N");
    vector<vector<int>> g(N);
    for (int i = 0; i < N - 1; i++) {
        int a = inf.readInt(1, N, "A_i") - 1;
        int b = inf.readInt(1, N, "B_i") - 1;
        g[a].push_back(b);
        g[b].push_back(a);
    }
    for (int i = 0; i < N; i++) {
        sort(g[i].begin(), g[i].end()); // ensures deterministic BFS tie-breaking
    }

    string S = inf.readToken();
    if ((int)S.size() != N) {
        // Invalid input shouldn't happen in official tests.
        quitf(_fail, "Invalid input: |S|=%d, expected N=%d", (int)S.size(), N);
    }
    vector<int> initCol(N);
    for (int i = 0; i < N; i++) {
        if (S[i] != 'W' && S[i] != 'B') quitf(_fail, "Invalid input char in S");
        initCol[i] = bit(S[i]);
    }

    // Read participant output safely: invalid output => score 0 (not WA/PE).
    vector<int> outOrder;
    outOrder.reserve(N);
    vector<char> seen(N, 0);

    auto invalid0 = [&](const char* msg) {
        quitp(0.0, "Invalid output: %s", msg);
    };

    // Read tokens manually so that non-integer, out-of-range, or missing
    // values all route through quitp(0.0) instead of testlib's built-in
    // _pe/_wa exit path from ouf.readInt(lo, hi, ...).
    for (int i = 0; i < N; i++) {
        if (ouf.seekEof()) invalid0("missing vertex P_t");
        string tok = ouf.readToken();
        if (tok.empty()) invalid0("empty token for P_t");
        if (tok.size() > 10) invalid0("vertex index out of range");
        for (size_t j = 0; j < tok.size(); j++) {
            if (tok[j] < '0' || tok[j] > '9') invalid0("non-integer token for P_t");
        }
        long long v = 0;
        for (size_t j = 0; j < tok.size(); j++) v = v * 10 + (tok[j] - '0');
        if (v < 1 || v > N) invalid0("vertex index out of range");
        int x = (int)v;
        if (seen[x - 1]) invalid0("duplicate vertex");
        seen[x - 1] = 1;
        outOrder.push_back(x - 1);
    }
    if (!ouf.seekEof()) invalid0("extra tokens after N integers");

    vector<int> baseOrder = baselineBfsOrder(g);
    long long C_base = simulateCost(g, initCol, baseOrder);
    long long C_out  = simulateCost(g, initCol, outOrder);

    double ratio = 0.0;
    if (C_base != 0) {
        long double x = (long double)(C_base - C_out) / (long double)C_base;
        if (x < 0) x = 0;
        if (x > 1) x = 1;
        ratio = (double)x;
    }

    ratio=bounded_base_ratio(ratio);
    ratio = natural_log_score(100.0L * (ratio), C_out, 0.4L*C_base, true) / 100.0;
    quitp(ratio,
          "Ratio: %.12f C_out=%lld C_base=%lld",
          ratio, C_out, C_base);
}
