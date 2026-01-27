#include <bits/stdc++.h>
using namespace std;

struct FastRand {
    uint32_t x;
    FastRand(uint32_t seed = 123456789u) : x(seed) {}
    inline uint32_t next() {
        x ^= x << 13;
        x ^= x >> 17;
        x ^= x << 5;
        return x;
    }
    inline uint32_t nextInt(uint32_t n) {
        return next() % n;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    if (!(cin >> N >> M)) return 0;

    vector<vector<int>> adj(N);
    vector<int> deg(N, 0);

    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u < 0 || u >= N || v < 0 || v >= N || u == v) continue;
        adj[u].push_back(v);
        adj[v].push_back(u);
        deg[u]++; deg[v]++;
    }

    vector<int> baseOrder(N);
    iota(baseOrder.begin(), baseOrder.end(), 0);
    sort(baseOrder.begin(), baseOrder.end(), [&](int a, int b) {
        if (deg[a] != deg[b]) return deg[a] < deg[b];
        return a < b;
    });

    vector<int> revOrder = baseOrder;
    reverse(revOrder.begin(), revOrder.end());

    vector<unsigned char> bestSel(N, 0), curSel(N, 0), blocked(N, 0);
    int bestCnt = -1;

    auto greedy = [&](const vector<int> &ord) {
        fill(blocked.begin(), blocked.end(), 0);
        fill(curSel.begin(), curSel.end(), 0);
        int cnt = 0;
        for (int idx = 0; idx < N; ++idx) {
            int v = ord[idx];
            if (!blocked[v]) {
                curSel[v] = 1;
                cnt++;
                blocked[v] = 1;
                const auto &nb = adj[v];
                for (int u : nb) blocked[u] = 1;
            }
        }
        if (cnt > bestCnt) {
            bestCnt = cnt;
            bestSel = curSel;
        }
    };

    greedy(baseOrder);
    greedy(revOrder);

    FastRand rng(123456789u ^ (uint32_t)N ^ ((uint32_t)M << 16));
    int ITER = 60;
    vector<int> ord(N);

    for (int it = 0; it < ITER; ++it) {
        ord = baseOrder;
        for (int i = 0; i < N; ++i) {
            if ((rng.next() & 7u) == 0u) { // probability 1/8
                int j = rng.nextInt(N);
                swap(ord[i], ord[j]);
            }
        }
        greedy(ord);
    }

    for (int i = 0; i < N; ++i) {
        cout << (bestSel[i] ? 1 : 0) << '\n';
    }

    return 0;
}