#include <bits/stdc++.h>
using namespace std;

struct Node {
    int g;
    uint32_t r;
    int v;
};
struct Cmp {
    bool operator()(const Node& a, const Node& b) const {
        if (a.g != b.g) return a.g < b.g;       // max gain first
        return a.r < b.r;                       // random tie-break
    }
};

static inline uint64_t splitmix64(uint64_t x) {
    x += 0x9e3779b97f4a7c15ULL;
    x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
    x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
    return x ^ (x >> 31);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    cin >> n >> m;

    vector<vector<int>> adj(n);
    vector<pair<int,int>> edges;
    edges.reserve(m);

    for (int i = 0; i < m; i++) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        adj[u].push_back(v);
        adj[v].push_back(u);
        edges.push_back({u, v});
    }

    if (m == 0) {
        for (int i = 0; i < n; i++) {
            if (i) cout << ' ';
            cout << 0;
        }
        cout << "\n";
        return 0;
    }

    auto start = chrono::steady_clock::now();
    auto deadline = start + chrono::milliseconds(1900);

    uint64_t seed = chrono::high_resolution_clock::now().time_since_epoch().count();
    seed ^= (uint64_t)(uintptr_t)&seed;
    seed = splitmix64(seed);

    mt19937 rng((uint32_t)seed);

    auto now_ok = [&]() -> bool {
        return chrono::steady_clock::now() < deadline;
    };

    auto initRandom = [&]() -> vector<int> {
        vector<int> s(n);
        for (int i = 0; i < n; i++) s[i] = (rng() & 1u);
        return s;
    };

    auto initGreedy = [&]() -> vector<int> {
        vector<int> s(n, 0);
        vector<char> assigned(n, 0);
        vector<int> order(n);
        iota(order.begin(), order.end(), 0);
        shuffle(order.begin(), order.end(), rng);

        int first = order[0];
        s[first] = (rng() & 1u);
        assigned[first] = 1;

        for (int idx = 1; idx < n; idx++) {
            int v = order[idx];
            int to0 = 0, to1 = 0;
            for (int u : adj[v]) if (assigned[u]) (s[u] ? to1 : to0)++;
            // If v in 0 => cut edges to assigned in 1 = to1
            // If v in 1 => cut edges to assigned in 0 = to0
            if (to0 > to1) s[v] = 1;
            else if (to1 > to0) s[v] = 0;
            else s[v] = (rng() & 1u);
            assigned[v] = 1;
        }
        return s;
    };

    auto localSearch = [&](vector<int>& s) -> long long {
        vector<int> gain(n, 0);
        long long cut = 0;

        for (auto [u, v] : edges) if (s[u] != s[v]) cut++;

        for (int i = 0; i < n; i++) {
            int diff = 0;
            int si = s[i];
            for (int u : adj[i]) diff += (si != s[u]);
            gain[i] = (int)adj[i].size() - 2 * diff;
        }

        priority_queue<Node, vector<Node>, Cmp> pq;
        for (int i = 0; i < n; i++) pq.push(Node{gain[i], (uint32_t)rng(), i});

        while (!pq.empty() && now_ok()) {
            Node cur = pq.top(); pq.pop();
            int v = cur.v;
            if (cur.g != gain[v]) continue;
            if (cur.g <= 0) break;

            int g = cur.g;
            int old = s[v];
            s[v] ^= 1;
            cut += g;

            gain[v] = -g;
            pq.push(Node{gain[v], (uint32_t)rng(), v});

            for (int u : adj[v]) {
                if (s[u] == old) gain[u] -= 2;
                else gain[u] += 2;
                pq.push(Node{gain[u], (uint32_t)rng(), u});
            }
        }
        return cut;
    };

    vector<int> bestS(n, 0);
    long long bestCut = -1;

    int iter = 0;
    while (now_ok()) {
        vector<int> s = (iter % 2 == 0) ? initGreedy() : initRandom();
        long long cut = localSearch(s);
        if (cut > bestCut) {
            bestCut = cut;
            bestS = s;
        }

        // Small perturbations from current solution
        for (int p = 0; p < 2 && now_ok(); p++) {
            vector<int> s2 = s;
            int k = max(1, n / 25); // ~4%
            for (int i = 0; i < k; i++) {
                int v = (int)(rng() % (uint32_t)n);
                s2[v] ^= 1;
            }
            long long cut2 = localSearch(s2);
            if (cut2 > bestCut) {
                bestCut = cut2;
                bestS = s2;
            }
            if (cut2 > cut) {
                cut = cut2;
                s.swap(s2);
            }
        }

        iter++;
    }

    for (int i = 0; i < n; i++) {
        if (i) cout << ' ';
        cout << bestS[i];
    }
    cout << "\n";
    return 0;
}