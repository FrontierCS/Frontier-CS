#include <bits/stdc++.h>
using namespace std;

static const int MAXN = 1000;
static const int WORDS = (MAXN + 63) / 64;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    if (!(cin >> N >> M)) return 0;

    vector<array<unsigned long long, WORDS>> adj(N);
    for (int i = 0; i < N; ++i) {
        adj[i].fill(0);
    }

    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u < 0 || v < 0 || u >= N || v >= N || u == v) continue;
        adj[u][v >> 6] |= 1ULL << (v & 63);
        adj[v][u >> 6] |= 1ULL << (u & 63);
    }

    vector<int> deg(N);
    int maxDeg = 0;
    for (int v = 0; v < N; ++v) {
        int cnt = 0;
        for (int w = 0; w < WORDS; ++w) {
            cnt += __builtin_popcountll(adj[v][w]);
        }
        deg[v] = cnt;
        if (cnt > maxDeg) maxDeg = cnt;
    }

    vector<vector<int>> buckets(maxDeg + 1);
    for (int v = 0; v < N; ++v) {
        buckets[deg[v]].push_back(v);
    }

    mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());

    array<unsigned long long, WORDS> selected;
    array<unsigned long long, WORDS> bestSelected;
    bestSelected.fill(0);
    int bestSize = 0;

    vector<int> order;
    order.reserve(N);

    auto start = chrono::steady_clock::now();
    const double TIME_LIMIT = 1.8;
    bool doneFirst = false;

    while (true) {
        if (doneFirst) {
            auto now = chrono::steady_clock::now();
            double elapsed = chrono::duration<double>(now - start).count();
            if (elapsed > TIME_LIMIT) break;
        }
        doneFirst = true;

        order.clear();
        for (int d = 0; d <= maxDeg; ++d) {
            auto &B = buckets[d];
            if (B.empty()) continue;
            shuffle(B.begin(), B.end(), rng);
            for (int v : B) order.push_back(v);
        }

        for (int w = 0; w < WORDS; ++w) selected[w] = 0ULL;
        int curSize = 0;

        for (int v : order) {
            bool conflict = false;
            for (int w = 0; w < WORDS; ++w) {
                if (adj[v][w] & selected[w]) {
                    conflict = true;
                    break;
                }
            }
            if (!conflict) {
                selected[v >> 6] |= 1ULL << (v & 63);
                ++curSize;
            }
        }

        if (curSize > bestSize) {
            bestSize = curSize;
            bestSelected = selected;
        }
    }

    for (int i = 0; i < N; ++i) {
        int word = i >> 6;
        int bit = i & 63;
        int val = (bestSelected[word] & (1ULL << bit)) ? 1 : 0;
        cout << val << '\n';
    }

    return 0;
}