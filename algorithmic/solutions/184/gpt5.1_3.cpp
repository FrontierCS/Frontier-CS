#include <iostream>
#include <vector>
#include <algorithm>
#include <random>
#include <chrono>

using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    long long M;
    if (!(cin >> N >> M)) return 0;

    vector<vector<int>> g(N + 1);
    g.reserve(N + 1);

    for (long long i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        if (u == v) continue; // ignore self-loops if any (though problem states u != v)
        g[u].push_back(v);
        g[v].push_back(u);
    }

    // Deduplicate adjacency lists
    vector<int> deg(N + 1);
    for (int v = 1; v <= N; ++v) {
        auto &adj = g[v];
        sort(adj.begin(), adj.end());
        adj.erase(unique(adj.begin(), adj.end()), adj.end());
        deg[v] = (int)adj.size();
    }

    // Random generator
    uint64_t seed = chrono::steady_clock::now().time_since_epoch().count();
    mt19937_64 rng(seed);

    // Determine number of random iterations based on M
    long long approxEdgeOps = 2LL * M; // approx adjacency checks per run
    int T = 200;
    if (approxEdgeOps > 0) {
        long long maxRunsByEdges = 100000000LL / approxEdgeOps; // aim for <=1e8 edge checks
        if (maxRunsByEdges < 10) maxRunsByEdges = 10;           // at least some attempts
        if (maxRunsByEdges < T) T = (int)maxRunsByEdges;
    }

    vector<int> base(N);
    for (int i = 0; i < N; ++i) base[i] = i + 1;

    vector<unsigned char> bestChosen(N + 1, 0);
    vector<unsigned char> tmpChosen(N + 1, 0);
    int bestSize = 0;

    auto runGreedy = [&](const vector<int> &order) {
        fill(tmpChosen.begin(), tmpChosen.end(), 0);
        int cnt = 0;
        for (int v : order) {
            if (g[v].empty()) { // isolated vertex, always safe to include
                if (!tmpChosen[v]) {
                    tmpChosen[v] = 1;
                    ++cnt;
                }
                continue;
            }
            if (cnt == 0) { // first vertex, can always be added
                tmpChosen[v] = 1;
                ++cnt;
                continue;
            }
            bool ok = true;
            const auto &adj = g[v];
            for (int u : adj) {
                if (tmpChosen[u]) {
                    ok = false;
                    break;
                }
            }
            if (ok) {
                tmpChosen[v] = 1;
                ++cnt;
            }
        }
        if (cnt > bestSize) {
            bestSize = cnt;
            bestChosen = tmpChosen;
        }
    };

    // Initial greedy: degree ascending
    {
        vector<int> order = base;
        sort(order.begin(), order.end(), [&](int a, int b) {
            if (deg[a] != deg[b]) return deg[a] < deg[b];
            return a < b;
        });
        runGreedy(order);
    }

    // Degree descending
    {
        vector<int> order = base;
        sort(order.begin(), order.end(), [&](int a, int b) {
            if (deg[a] != deg[b]) return deg[a] > deg[b];
            return a < b;
        });
        runGreedy(order);
    }

    // Random permutations
    vector<int> order = base;
    for (int it = 0; it < T; ++it) {
        shuffle(order.begin(), order.end(), rng);
        runGreedy(order);
    }

    for (int i = 1; i <= N; ++i) {
        cout << (bestChosen[i] ? 1 : 0) << '\n';
    }

    return 0;
}