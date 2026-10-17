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

using int64 = long long;
using i128 = __int128_t;

static string toString128(i128 x) {
    if (x == 0) return "0";
    bool neg = false;
    if (x < 0) { neg = true; x = -x; }
    string s;
    while (x > 0) {
        int digit = (int)(x % 10);
        s.push_back(char('0' + digit));
        x /= 10;
    }
    if (neg) s.push_back('-');
    reverse(s.begin(), s.end());
    return s;
}

static bool hasEdgeSorted(const vector<vector<int>>& g, int u, int v) {
    const auto& adj = g[u];
    return binary_search(adj.begin(), adj.end(), v);
}

static i128 computeValue(int N, int K, const vector<int64>& r, const vector<int>& moves) {
    vector<int> first(N + 1, -1);
    int cur = 1;
    first[cur] = 0;

    i128 val = 0;
    for (int t = 1; t <= K; t++) {
        cur = moves[t - 1];
        if (first[cur] == -1) {
            first[cur] = t;
            val += (i128)r[cur] * (i128)t;
        }
    }
    // r[1]*0 is always 0, already implicit
    return val;
}

static vector<int> buildBaselineWalk(int N, int M, int K, const vector<vector<int>>& gSorted) {
    // 1) BFS tree rooted at 1, neighbors in increasing id order.
    vector<int> parent(N + 1, -1);
    parent[1] = 1;
    queue<int> q;
    q.push(1);

    while (!q.empty()) {
        int v = q.front(); q.pop();
        for (int to : gSorted[v]) {
            if (parent[to] == -1) {
                parent[to] = v;
                q.push(to);
            }
        }
    }

    // 2) children lists sorted increasing
    vector<vector<int>> children(N + 1);
    for (int v = 2; v <= N; v++) {
        // Graph is connected => all should be discovered
        if (parent[v] < 0) parent[v] = 1; // should not happen
        children[parent[v]].push_back(v);
    }
    for (int v = 1; v <= N; v++) sort(children[v].begin(), children[v].end());

    // 3) DFS Euler on the tree: go down and back up each tree edge once.
    vector<int> moves;
    moves.reserve(K);

    function<void(int)> dfs = [&](int v) {
        for (int ch : children[v]) {
            moves.push_back(ch); // move down
            dfs(ch);
            moves.push_back(v);  // move back up
        }
    };
    dfs(1);

    // 4) If shorter than K, append back-forth along smallest-id neighbor of 1.
    if ((int)moves.size() < K) {
        ensuref(!gSorted[1].empty(), "Vertex 1 has no incident edges (but graph is connected?)");
        int nb = gSorted[1][0];
        int cur = 1; // after Euler, we are at 1
        int need = K - (int)moves.size();
        for (int i = 0; i < need; i++) {
            if (i % 2 == 0) cur = nb;
            else cur = 1;
            moves.push_back(cur);
        }
    }

    if ((int)moves.size() > K) moves.resize(K);
    return moves;
}

int main(int argc, char* argv[]) {
    registerTestlibCmd(argc, argv);

    int N = inf.readInt();
    int M = inf.readInt();
    int K = inf.readInt();

    vector<int64> r(N + 1);
    for (int i = 1; i <= N; i++) r[i] = inf.readLong();

    vector<vector<int>> g(N + 1);
    g.reserve(N + 1);
    for (int i = 0; i < M; i++) {
        int u = inf.readInt();
        int v = inf.readInt();
        g[u].push_back(v);
        g[v].push_back(u);
    }
    for (int i = 1; i <= N; i++) sort(g[i].begin(), g[i].end());

    // Read participant output: exactly K integers.
    vector<int> moves;
    moves.reserve(K);

    for (int t = 1; t <= K; t++) {
        if (ouf.seekEof()) {
            quitp(0.0, "Output has fewer than K=%d integers", K);
        }
        int x = ouf.readInt(1, N, format("x[%d]", t));
        moves.push_back(x);
    }
    if (!ouf.seekEof()) {
        quitp(0.0, "Output has extra tokens after K=%d integers", K);
    }

    // Validate walk.
    vector<char> seen(N + 1, 0);
    int cur = 1;
    seen[cur] = 1;

    for (int t = 1; t <= K; t++) {
        int nx = moves[t - 1];
        if (!hasEdgeSorted(g, cur, nx)) {
            quitp(0.0, "Invalid move at t=%d: no edge %d-%d", t, cur, nx);
        }
        cur = nx;
        seen[cur] = 1;
    }

    for (int i = 1; i <= N; i++) {
        if (!seen[i]) quitp(0.0, "Vertex %d was never visited in times 0..K", i);
    }

    // Compute participant value V.
    i128 V = computeValue(N, K, r, moves);

    // Compute baseline B.
    vector<int> baseMoves = buildBaselineWalk(N, M, K, g);
    i128 B = computeValue(N, K, r, baseMoves);

    long double ratioLD = 0.0L;
    if (V != 0) {
        ratioLD = (long double)(V - B) / (long double)V;
        if (ratioLD < 0.0L) ratioLD = 0.0L;
        if (ratioLD > 1.0L) ratioLD = 1.0L;
    }

    double ratio = (double)ratioLD;
    ratio=bounded_base_ratio(ratio);
    ratio = natural_log_score(100.0L * (ratio), (long double)V, 2.5L*(long double)B, false) / 100.0;
    quitp(ratio,
          "Ratio: %.12f  V=%s  B=%s",
          ratio,
          toString128(V).c_str(),
          toString128(B).c_str());
}
