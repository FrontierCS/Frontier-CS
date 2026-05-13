#include "testlib.h"
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

    // ---- Compute score ----
    // score = 100000 * min(2, B/A)
    // ratio for quitp = min(1, B/(2*A))  (since max score = 200000 corresponds to ratio=1)
    double ratio;
    if (A == 0) {
        // This shouldn't happen if m >= 1, but guard
        ratio = 1.0;
    } else {
        double bOverA = (double)B / (double)A;
        ratio = min(1.0, bOverA / 2.0);
    }

    // Clamp to [0,1]
    if (ratio < 0.0) ratio = 0.0;
    if (ratio > 1.0) ratio = 1.0;

    quitp(ratio, "Feasible. A=%lld B=%lld ratio=%.6f Ratio: %.6f", A, B, ratio, ratio);

    return 0;
}