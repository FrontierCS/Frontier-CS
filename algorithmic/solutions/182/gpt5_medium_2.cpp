#include <bits/stdc++.h>
using namespace std;

struct FastRNG {
    uint64_t x;
    FastRNG() {
        uint64_t t = chrono::high_resolution_clock::now().time_since_epoch().count();
        x = t ^ (t << 13) ^ (t >> 7) ^ (t << 17);
        if (x == 0) x = 88172645463393265ull;
    }
    uint64_t next() {
        x ^= x << 7;
        x ^= x >> 9;
        return x;
    }
    size_t operator()(size_t n) { return (size_t)(next() % n); }
};

static inline int other(int v, int a, int b) {
    return a == v ? b : a;
}

vector<char> greedy_degree_cover(int N, int M, const vector<int>& U, const vector<int>& V, const vector<vector<int>>& adj) {
    vector<char> inCover(N, 0);
    vector<char> covered(M, 0);
    vector<int> deg(N, 0);
    for (int i = 0; i < N; ++i) deg[i] = (int)adj[i].size();

    long long uncoveredEdges = M;
    priority_queue<pair<int,int>> pq;
    for (int i = 0; i < N; ++i) pq.emplace(deg[i], i);

    while (uncoveredEdges > 0) {
        while (!pq.empty()) {
            auto [d, v] = pq.top();
            if (d != deg[v] || inCover[v]) { pq.pop(); continue; }
            if (d == 0) { pq.pop(); continue; }
            // choose v
            inCover[v] = 1;
            for (int eid : adj[v]) {
                if (!covered[eid]) {
                    covered[eid] = 1;
                    --uncoveredEdges;
                    int u = (U[eid] == v ? V[eid] : U[eid]);
                    if (!inCover[u]) {
                        --deg[u];
                        pq.emplace(deg[u], u);
                    }
                }
            }
            break;
        }
        if (pq.empty()) break; // safety
    }
    return inCover;
}

vector<char> maximal_matching_cover(int N, int M, const vector<int>& U, const vector<int>& V) {
    vector<char> inCover(N, 0), used(N, 0);
    for (int i = 0; i < M; ++i) {
        int a = U[i], b = V[i];
        if (!used[a] && !used[b]) {
            used[a] = used[b] = 1;
            inCover[a] = inCover[b] = 1;
        }
    }
    return inCover;
}

void trim_cover(vector<char>& cover, int N, const vector<int>& U, const vector<int>& V, const vector<vector<int>>& adj) {
    vector<int> order;
    order.reserve(N);
    for (int i = 0; i < N; ++i) if (cover[i]) order.push_back(i);
    FastRNG rng;
    shuffle(order.begin(), order.end(), std::mt19937((unsigned)rng.next()));
    for (int v : order) {
        if (!cover[v]) continue;
        bool removable = true;
        for (int eid : adj[v]) {
            int u = (U[eid] == v ? V[eid] : U[eid]);
            if (!cover[u]) { removable = false; break; }
        }
        if (removable) cover[v] = 0;
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N, M;
    if (!(cin >> N >> M)) return 0;
    vector<int> U(M), V(M);
    vector<vector<int>> adj(N);
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        U[i] = u; V[i] = v;
        adj[u].push_back(i);
        adj[v].push_back(i);
    }

    // Strategy 1: Greedy by degree
    auto cover1 = greedy_degree_cover(N, M, U, V, adj);
    trim_cover(cover1, N, U, V, adj);

    // Strategy 2: Maximal matching
    auto cover2 = maximal_matching_cover(N, M, U, V);
    trim_cover(cover2, N, U, V, adj);

    // Choose better
    int k1 = 0, k2 = 0;
    for (int i = 0; i < N; ++i) { if (cover1[i]) ++k1; if (cover2[i]) ++k2; }
    const vector<char>& best = (k1 <= k2 ? cover1 : cover2);

    for (int i = 0; i < N; ++i) {
        cout << (best[i] ? 1 : 0) << '\n';
    }
    return 0;
}