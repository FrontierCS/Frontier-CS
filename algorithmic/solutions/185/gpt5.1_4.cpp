#include <bits/stdc++.h>
using namespace std;

const int MAXN = 1000;
static bitset<MAXN> adj[MAXN];

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    if (!(cin >> N >> M)) return 0;

    vector<int> deg(N, 0);

    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        if (!adj[u][v]) {
            adj[u].set(v);
            adj[v].set(u);
            ++deg[u];
            ++deg[v];
        }
    }

    vector<int> order(N);
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [&](int a, int b) {
        return deg[a] > deg[b];
    });

    vector<int> seeds;
    int K1 = min(N, 100);
    for (int i = 0; i < K1; ++i) seeds.push_back(order[i]);

    if (N > K1) {
        vector<int> others(order.begin() + K1, order.end());
        mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());
        shuffle(others.begin(), others.end(), rng);
        int limit = min(N, 200);
        for (int i = 0; i < (int)others.size() && (int)seeds.size() < limit; ++i) {
            seeds.push_back(others[i]);
        }
    }

    using clock_type = chrono::steady_clock;
    auto startTime = clock_type::now();
    const int TIME_LIMIT_MS = 1900;

    int bestsize = 0;
    vector<int> bestclique;

    for (int idx = 0; idx < (int)seeds.size(); ++idx) {
        if (idx % 8 == 0) {
            auto now = clock_type::now();
            if (chrono::duration_cast<chrono::milliseconds>(now - startTime).count() > TIME_LIMIT_MS)
                break;
        }

        int s = seeds[idx];
        if (deg[s] + 1 <= bestsize) continue;

        vector<int> clique;
        clique.reserve(N);
        clique.push_back(s);
        bitset<MAXN> P = adj[s];

        while (P.any()) {
            int possibleMax = (int)clique.size() + (int)P.count();
            if (possibleMax <= bestsize) break;

            int bestv = -1;
            int bestvdeg = -1;
            for (int v = 0; v < N; ++v) {
                if (P[v] && deg[v] > bestvdeg) {
                    bestvdeg = deg[v];
                    bestv = v;
                }
            }
            if (bestv == -1) break;
            clique.push_back(bestv);
            P &= adj[bestv];
        }

        if ((int)clique.size() > bestsize) {
            bestsize = (int)clique.size();
            bestclique = clique;
        }
    }

    if (bestsize == 0) {
        bool found = false;
        for (int u = 0; u < N && !found; ++u) {
            for (int v = 0; v < N && !found; ++v) {
                if (adj[u][v]) {
                    bestsize = 2;
                    bestclique = {u, v};
                    found = true;
                }
            }
        }
        if (!found) {
            bestsize = 1;
            bestclique = {0};
        }
    }

    vector<int> inClique(N, 0);
    for (int v : bestclique) inClique[v] = 1;

    for (int i = 0; i < N; ++i) {
        cout << inClique[i] << '\n';
    }

    return 0;
}