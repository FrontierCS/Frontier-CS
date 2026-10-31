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

typedef long long ll;
typedef pair<ll,int> pli;

static const ll INF = 1e18;

int main(int argc, char* argv[]) {
    registerTestlibCmd(argc, argv);

    // ---- Read input ----
    int n = inf.readInt();
    int m = inf.readInt();
    int k = inf.readInt();

    vector<int> X(m+1), Y(m+1);
    vector<ll> C(m+1);
    // adjacency list for Dijkstra: (neighbor, edge_weight)
    vector<vector<pair<int,ll>>> adj(n+1);

    for (int i = 1; i <= m; i++) {
        X[i] = inf.readInt();
        Y[i] = inf.readInt();
        C[i] = inf.readLong();
        adj[X[i]].push_back({Y[i], C[i]});
        if (X[i] != Y[i])
            adj[Y[i]].push_back({X[i], C[i]});
    }

    // ---- Dijkstra from node 1 ----
    vector<ll> dist(n+1, INF);
    dist[1] = 0;
    priority_queue<pli, vector<pli>, greater<pli>> pq;
    pq.push({0, 1});
    while (!pq.empty()) {
        auto [d, u] = pq.top(); pq.pop();
        if (d > dist[u]) continue;
        for (auto [v, w] : adj[u]) {
            if (dist[u] + w < dist[v]) {
                dist[v] = dist[u] + w;
                pq.push({dist[v], v});
            }
        }
    }

    // ---- Compute baseline B ----
    // tau_i = dist[x_i] + c_i + dist[y_i]
    // sort by decreasing tau, tie-break by smaller trail id
    vector<int> order(m);
    iota(order.begin(), order.end(), 1);
    vector<ll> tau(m+1);
    for (int i = 1; i <= m; i++) {
        ll dx = (dist[X[i]] == INF ? INF : dist[X[i]]);
        ll dy = (dist[Y[i]] == INF ? INF : dist[Y[i]]);
        tau[i] = (dx == INF || dy == INF) ? INF : dx + C[i] + dy;
    }
    sort(order.begin(), order.end(), [&](int a, int b){
        if (tau[a] != tau[b]) return tau[a] > tau[b];
        return a < b;
    });

    vector<ll> load(k, 0LL);
    for (int idx : order) {
        // find team with min load, tie-break smaller index
        int best = 0;
        for (int j = 1; j < k; j++)
            if (load[j] < load[best]) best = j;
        load[best] += tau[idx];
    }
    ll B = *max_element(load.begin(), load.end());

    // ---- Read participant output ----
    vector<vector<int>> walks(k);
    for (int j = 0; j < k; j++) {
        int t = ouf.readInt();
        if (t < 0)
            quitf(_wa, "Team %d has negative number of traversals: %d", j+1, t);
        walks[j].resize(t);
        for (int p = 0; p < t; p++) {
            int a = ouf.readInt();
            if (a == 0)
                quitf(_wa, "Team %d step %d: trail id is 0 (must be nonzero signed int)", j+1, p+1);
            int absa = abs(a);
            if (absa < 1 || absa > m)
                quitf(_wa, "Team %d step %d: |trail id| = %d out of range [1,%d]", j+1, p+1, absa, m);
            walks[j][p] = a;
        }
    }

    // Assert end of stream
    if (!ouf.seekEof())
        quitf(_wa, "Extra data in output after all team descriptions");

    // ---- Check feasibility ----
    // Track which trails are covered
    vector<bool> covered(m+1, false);

    ll A = 0; // max team length

    for (int j = 0; j < k; j++) {
        int cur = 1; // start at glade 1
        ll teamLen = 0;

        for (int p = 0; p < (int)walks[j].size(); p++) {
            int a = walks[j][p];
            int absa = abs(a);
            int from_node = (a > 0) ? X[absa] : Y[absa];
            int to_node   = (a > 0) ? Y[absa] : X[absa];

            if (from_node != cur)
                quitf(_wa, "Team %d step %d: trail starts at glade %d but team is at glade %d",
                      j+1, p+1, from_node, cur);

            cur = to_node;
            teamLen += C[absa];
            covered[absa] = true;
        }

        if (cur != 1)
            quitf(_wa, "Team %d does not return to glade 1 (ends at glade %d)", j+1, cur);

        if (teamLen > A) A = teamLen;
    }

    // Check all trails covered
    for (int i = 1; i <= m; i++) {
        if (!covered[i])
            quitf(_wa, "Trail %d is never traversed by any team", i);
    }

    // Positive trail lengths and full coverage imply A>0.
    ensuref(A > 0 && B > 0, "Positive route and baseline costs required");
    double r = (double)B / (2.0 * (double)A);
    double ratio = referenceScore(r);
    ratio = natural_log_score(100.0L * (ratio), A, (long double)B/2.0L, true) / 100.0;
    quitp(ratio, "Feasible. A=%lld B=%lld Ratio: %.12f, RatioUnbounded: %.12f", A, B, ratio, ratio);

    return 0;
}
