#include "testlib.h"
#include <bits/stdc++.h>
using namespace std;

typedef long long ll;
typedef pair<ll,int> pli;

const ll INF = (ll)4e18;
const int MAXV = 8001;

vector<pair<int,ll>> adj[MAXV];

vector<ll> dijkstra(int src, int V) {
    vector<ll> d(V + 1, INF);
    priority_queue<pli, vector<pli>, greater<pli>> pq;
    d[src] = 0;
    pq.push({0, src});
    while (!pq.empty()) {
        auto [dd, u] = pq.top(); pq.pop();
        if (dd > d[u]) continue;
        for (auto& [v, w] : adj[u]) {
            if (d[u] + w < d[v]) {
                d[v] = d[u] + w;
                pq.push({d[v], v});
            }
        }
    }
    return d;
}

int main(int argc, char* argv[]) {
    registerTestlibCmd(argc, argv);

    // ---------- read input ----------
    int V  = inf.readInt();
    int E  = inf.readInt();
    int M  = inf.readInt();
    int N  = inf.readInt();
    ll  C  = inf.readLong();

    for (int i = 0; i < E; i++) {
        int u = inf.readInt();
        int v = inf.readInt();
        ll  w = inf.readLong();
        adj[u].push_back({v, w});
        adj[v].push_back({u, w});
    }

    vector<int> pad_node(M + 1);
    vector<ll>  pad_cost(M + 1);
    for (int j = 1; j <= M; j++) {
        pad_node[j] = inf.readInt();
        pad_cost[j] = inf.readLong();
    }

    vector<int> src_ship(N), tgt_ship(N);
    for (int i = 0; i < N; i++) {
        src_ship[i] = inf.readInt();
        tgt_ship[i] = inf.readInt();
    }

    // ---------- read participant output ----------
    int K = ouf.readInt(0, M, "K must be between 0 and M");

    vector<int> chosen(K);
    vector<bool> used(M + 1, false);
    ll total_cost = 0;

    for (int i = 0; i < K; i++) {
        chosen[i] = ouf.readInt(1, M, "site index out of range [1,M]");
        if (used[chosen[i]])
            quitf(_wa, "duplicate site index %d", chosen[i]);
        used[chosen[i]] = true;
        total_cost += pad_cost[chosen[i]];
    }

    if (!ouf.seekEof())
        quitf(_wa, "extra data after the K chosen site indices");

    if (total_cost > C)
        quitf(_wa, "total construction cost %lld exceeds budget %lld", total_cost, C);

    // ---------- gather unique Dijkstra sources ----------
    set<int> sources_set;
    for (int i = 0; i < N; i++) {
        sources_set.insert(src_ship[i]);
        sources_set.insert(tgt_ship[i]);
    }

    // Run Dijkstra from each unique source
    map<int, vector<ll>> dist_from;
    for (int s : sources_set) {
        dist_from[s] = dijkstra(s, V);
    }

    // Collect chosen pad node intersections
    vector<int> pad_nodes_chosen;
    pad_nodes_chosen.reserve(K);
    for (int i = 0; i < K; i++) {
        pad_nodes_chosen.push_back(pad_node[chosen[i]]);
    }

    // ---------- compute B and O ----------
    ll B = 0, O = 0;
    for (int i = 0; i < N; i++) {
        int s = src_ship[i];
        int t = tgt_ship[i];

        const vector<ll>& ds = dist_from[s];
        const vector<ll>& dt = dist_from[t];

        ll direct = ds[t];
        B += direct;

        ll best = direct;
        if (!pad_nodes_chosen.empty()) {
            ll min_s = INF, min_t = INF;
            for (int p : pad_nodes_chosen) {
                if (ds[p] < min_s) min_s = ds[p];
                if (dt[p] < min_t) min_t = dt[p];
            }
            if (min_s < INF && min_t < INF) {
                ll tele = min_s + min_t;
                if (tele < best) best = tele;
            }
        }
        O += best;
    }

    // ---------- score ----------
    // statement: score = round(1,000,000 * max(0, min(1, (B - O) / B)))
    // B > 0 guaranteed since all weights > 0 and s_i != t_i with connected graph
    if (B <= 0) {
        // Degenerate: shouldn't happen per constraints; give full score
        quitp(1.0, "B=0 (degenerate), Ratio: 1.000000000");
    }

    double raw_ratio = (double)(B - O) / (double)B;
    if (raw_ratio < 0.0) raw_ratio = 0.0;
    if (raw_ratio > 1.0) raw_ratio = 1.0;

    // round to nearest 1/1,000,000 as stated in problem
    double rounded_ratio = round(raw_ratio * 1000000.0) / 1000000.0;

    quitp(rounded_ratio,
          "B=%lld O=%lld improvement=%lld Ratio: %.9f",
          B, O, (B - O), rounded_ratio);

    return 0;
}