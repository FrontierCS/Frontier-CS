#include "testlib.h"
#include <bits/stdc++.h>
using namespace std;

int main(int argc, char* argv[]) {
    registerTestlibCmd(argc, argv);

    // ---- read input ----
    int L = inf.readInt();
    int N = inf.readInt();
    int M = inf.readInt();
    string S = inf.readToken(); // length L; S[k-1] is owner of route k (between islands k-1 and k)

    vector<int> X(N), H(N), D(N);
    vector<char> C(N);
    for (int i = 0; i < N; i++) {
        X[i] = inf.readInt();
        string ci = inf.readToken();
        C[i] = ci[0];
        H[i] = inf.readInt();
        D[i] = inf.readInt();
    }

    vector<int> A(M), B(M);
    vector<long long> W(M);
    for (int j = 0; j < M; j++) {
        A[j] = inf.readInt();
        B[j] = inf.readInt();
        W[j] = inf.readLong();
    }

    // prefix sums for bad-route counting
    // prefBadA[k] = number of routes in [1..k] not owned by A (i.e., owned by J)
    // prefBadJ[k] = number of routes in [1..k] not owned by J (i.e., owned by A)
    vector<int> prefBadA(L + 1, 0), prefBadJ(L + 1, 0);
    for (int k = 1; k <= L; k++) {
        prefBadA[k] = prefBadA[k-1] + (S[k-1] != 'A' ? 1 : 0);
        prefBadJ[k] = prefBadJ[k-1] + (S[k-1] != 'J' ? 1 : 0);
    }

    // bad(c, u, v) = number of routes on path u..v whose owner != c
    auto badRoutes = [&](char c, int u, int v) -> int {
        if (u > v) swap(u, v);
        if (c == 'A') return prefBadA[v] - prefBadA[u];
        else          return prefBadJ[v] - prefBadJ[u];
    };

    // ---- read participant output ----
    vector<int> Li(N, -1), Ri(N, -1);
    vector<bool> hired(N, false);

    for (int i = 0; i < N; i++) {
        string tok = ouf.readToken();
        if (tok == "-1") {
            hired[i] = false;
        } else {
            // tok is l_i
            int li, ri;
            try {
                li = stoi(tok);
            } catch (...) {
                quitf(_wa, "Resident %d: invalid token '%s'", i+1, tok.c_str());
            }
            ri = ouf.readInt();

            // feasibility checks
            if (li < 0 || li > L)
                quitf(_wa, "Resident %d: l=%d out of range [0,%d]", i+1, li, L);
            if (ri < 0 || ri > L)
                quitf(_wa, "Resident %d: r=%d out of range [0,%d]", i+1, ri, L);
            if (li >= ri)
                quitf(_wa, "Resident %d: l=%d >= r=%d, need l < r", i+1, li, ri);
            if (ri - li > D[i])
                quitf(_wa, "Resident %d: r-l=%d exceeds D=%d", i+1, ri-li, D[i]);

            hired[i] = true;
            Li[i] = li;
            Ri[i] = ri;
        }
    }

    // Check no extra tokens remain in participant output
    if (!ouf.seekEof()) {
        quitf(_wa, "Extra output after %d lines", N);
    }

    // ---- compute setup cost ----
    long long setup_total = 0;
    for (int i = 0; i < N; i++) {
        if (!hired[i]) continue;
        int li = Li[i], ri = Ri[i];
        long long hi = (long long)H[i];
        int cost_to_l = badRoutes(C[i], X[i], li);
        int cost_to_r = badRoutes(C[i], X[i], ri);
        long long setup = hi + (long long)min(cost_to_l, cost_to_r);
        setup_total += setup;
    }

    // ---- build graph and run Dijkstra per demand ----
    // Edge: {to, cost}
    struct Edge { int to, cost; };
    vector<vector<Edge>> adj(L + 1);

    // always-available adjacent-island routes, cost 1
    for (int k = 1; k <= L; k++) {
        adj[k-1].push_back({k, 1});
        adj[k].push_back({k-1, 1});
    }

    // hired shuttle edges
    for (int i = 0; i < N; i++) {
        if (!hired[i]) continue;
        int li = Li[i], ri = Ri[i];
        int ec = badRoutes(C[i], li, ri);
        adj[li].push_back({ri, ec});
        adj[ri].push_back({li, ec});
    }

    // Dijkstra from a source
    auto dijkstra = [&](int src) -> vector<int> {
        vector<int> dist(L + 1, INT_MAX);
        priority_queue<pair<int,int>, vector<pair<int,int>>, greater<pair<int,int>>> pq;
        dist[src] = 0;
        pq.push({0, src});
        while (!pq.empty()) {
            auto top = pq.top(); pq.pop();
            int d = top.first, u = top.second;
            if (d > dist[u]) continue;
            for (int e = 0; e < (int)adj[u].size(); e++) {
                int nd = d + adj[u][e].cost;
                int v = adj[u][e].to;
                if (nd < dist[v]) {
                    dist[v] = nd;
                    pq.push({nd, v});
                }
            }
        }
        return dist;
    };

    // cache Dijkstra results by source to avoid recomputation
    unordered_map<int, vector<int>> dist_cache;

    long long demand_total = 0;
    for (int j = 0; j < M; j++) {
        int src = A[j], dst = B[j];
        if (dist_cache.find(src) == dist_cache.end()) {
            dist_cache[src] = dijkstra(src);
        }
        long long sp = dist_cache[src][dst];
        if (sp == INT_MAX) {
            // Graph is always connected via adjacent edges, should never happen
            quitf(_wa, "Demand %d: no path from %d to %d", j+1, src, dst);
        }
        demand_total += W[j] * sp;
    }

    long long U = setup_total + demand_total;

    // ---- compute baseline B = sum W_j * |A_j - B_j| (hire nobody) ----
    long long baseline = 0;
    for (int j = 0; j < M; j++) {
        baseline += W[j] * (long long)abs(A[j] - B[j]);
    }

    // ---- compute score ratio ----
    // Statement: Score = floor(10^9 * min(5, B/U))
    // Baseline (U=B): score = 10^9 = 1.0 * 10^9
    // Maximum (B/U=5): score = 5*10^9
    // Map to [0,1] for quitp: ratio = min(5, B/U) / 5
    // So baseline -> ratio=0.2, maximum -> ratio=1.0
    // This is consistent: quitp scores are relative; baseline is not "perfect" (ratio=1)
    // but rather a known reference point. The problem rewards improvement beyond baseline.

    double ratio;
    if (U <= 0) {
        ratio = 1.0;
    } else {
        double bu = (double)baseline / (double)U;
        double score_mult = (bu < 5.0) ? bu : 5.0; // min(5, B/U)
        ratio = score_mult / 5.0;                   // normalize to [0,1]
    }

    if (ratio < 0.0) ratio = 0.0;
    if (ratio > 1.0) ratio = 1.0;

    // The Ratio tag is parsed by the judge
    quitp(ratio,
          "Ratio: %.10f | B=%lld U=%lld (setup=%lld demand=%lld) score=%.0f",
          ratio, baseline, U, setup_total, demand_total,
          floor(1e9 * ((ratio * 5.0) < 5.0 ? ratio * 5.0 : 5.0)));

    return 0;
}