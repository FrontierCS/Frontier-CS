#include <bits/stdc++.h>
using namespace std;

static uint64_t rng_state;

inline uint32_t fast_rand() {
    uint64_t x = rng_state;
    x ^= x << 7;
    x ^= x >> 9;
    rng_state = x;
    return (uint32_t)x;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    int M;
    if (!(cin >> N >> M)) return 0;

    vector<vector<int>> adj(N);
    adj.reserve(N);
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u < 0 || u >= N || v < 0 || v >= N || u == v) continue;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    vector<int> deg(N);
    for (int i = 0; i < N; ++i) {
        deg[i] = (int)adj[i].size();
    }

    // Base order: vertices sorted by non-decreasing degree
    vector<int> base(N);
    iota(base.begin(), base.end(), 0);
    sort(base.begin(), base.end(), [&](int a, int b) {
        if (deg[a] != deg[b]) return deg[a] < deg[b];
        return a < b;
    });

    auto greedy = [&](const vector<int>& order, vector<char>& inSet) -> int {
        fill(inSet.begin(), inSet.end(), 0);
        int K = 0;
        for (int v : order) {
            bool ok = true;
            const auto &nbrs = adj[v];
            for (int u : nbrs) {
                if (inSet[u]) { ok = false; break; }
            }
            if (ok) {
                inSet[v] = 1;
                ++K;
            }
        }
        return K;
    };

    vector<char> current(N, 0), best(N, 0);

    // Seed RNG
    rng_state = chrono::steady_clock::now().time_since_epoch().count();
    if (rng_state == 0) rng_state = 88172645463325252ull;

    // Initial solution with pure degree-based order
    int bestK = greedy(base, current);
    best = current;

    const int MAX_ITERS = 200;
    vector<int> order(N);

    for (int iter = 1; iter <= MAX_ITERS; ++iter) {
        // Start from base order or its reverse
        if (iter & 1) {
            order = base;
        } else {
            order.assign(base.rbegin(), base.rend());
        }

        // Apply localized randomization while roughly preserving degree order
        const int W = 30;
        for (int i = 0; i < N; ++i) {
            int rem = N - i;
            int maxw = rem < W ? rem : W;
            if (maxw > 1) {
                int j = i + (fast_rand() % maxw);
                int tmp = order[i];
                order[i] = order[j];
                order[j] = tmp;
            }
        }

        int K = greedy(order, current);
        if (K > bestK) {
            bestK = K;
            best = current;
        }
    }

    for (int i = 0; i < N; ++i) {
        cout << (best[i] ? 1 : 0) << '\n';
    }

    return 0;
}