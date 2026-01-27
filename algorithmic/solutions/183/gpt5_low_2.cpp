#include <bits/stdc++.h>
using namespace std;

struct HeapNode {
    int deg;
    uint32_t key;
    int v;
    bool operator<(const HeapNode& other) const {
        if (deg != other.deg) return deg > other.deg; // min-heap by degree
        if (key != other.key) return key > other.key; // tie-break by random key
        return v > other.v;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N, M;
    if (!(cin >> N >> M)) return 0;
    vector<vector<int>> adj(N);
    adj.reserve(N);
    // Read edges
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    // Deduplicate adjacency lists
    for (int i = 0; i < N; ++i) {
        auto &a = adj[i];
        sort(a.begin(), a.end());
        a.erase(unique(a.begin(), a.end()), a.end());
    }

    vector<int> degree(N);
    for (int i = 0; i < N; ++i) degree[i] = (int)adj[i].size();

    vector<int> bestSel(N, 0);
    int bestK = -1;

    std::mt19937_64 rng(chrono::high_resolution_clock::now().time_since_epoch().count());

    auto start = chrono::high_resolution_clock::now();
    const double TIME_LIMIT = 1.8; // seconds

    int runs = 0;
    while (true) {
        auto now = chrono::high_resolution_clock::now();
        double elapsed = chrono::duration<double>(now - start).count();
        if (elapsed > TIME_LIMIT && bestK >= 0) break;
        runs++;

        vector<uint32_t> key(N);
        for (int i = 0; i < N; ++i) key[i] = (uint32_t)rng();

        vector<int> curDeg = degree;
        vector<char> remaining(N, 1);
        vector<int> sel(N, 0);

        priority_queue<HeapNode> pq;
        for (int i = 0; i < N; ++i) {
            pq.push({curDeg[i], key[i], i});
        }

        while (!pq.empty()) {
            auto hn = pq.top(); pq.pop();
            int v = hn.v;
            if (!remaining[v]) continue;
            if (hn.deg != curDeg[v]) continue;

            // Select v
            sel[v] = 1;
            remaining[v] = 0;

            // Remove neighbors of v and update degrees
            for (int u : adj[v]) {
                if (!remaining[u]) continue;
                remaining[u] = 0;
                // decrease degree of neighbors of u
                for (int w : adj[u]) {
                    if (remaining[w]) {
                        curDeg[w]--;
                        pq.push({curDeg[w], key[w], w});
                    }
                }
            }
        }

        int K = 0;
        for (int x : sel) K += x;
        if (K > bestK) {
            bestK = K;
            bestSel = move(sel);
        }

        // Safety break to avoid too many runs on trivial graphs
        if (runs > 200) break;
    }

    // Output solution
    for (int i = 0; i < N; ++i) {
        cout << (bestSel[i] ? 1 : 0) << "\n";
    }
    return 0;
}