#include <bits/stdc++.h>
using namespace std;

struct FastRand {
    uint64_t x;
    FastRand(uint64_t seed = 88172645463393265ull) : x(seed) {}
    inline uint32_t next() {
        x ^= x << 7;
        x ^= x >> 9;
        return (uint32_t)x;
    }
    inline uint64_t next64() {
        uint64_t a = next();
        uint64_t b = next();
        return (a << 32) ^ b;
    }
    template<typename Iter>
    void shuffle(Iter first, Iter last) {
        if (first == last) return;
        auto n = last - first;
        for (decltype(n) i = n - 1; i > 0; --i) {
            uint64_t j = next64() % (uint64_t)(i + 1);
            swap(first[i], first[j]);
        }
    }
};

static inline vector<char> greedySequential(const vector<vector<int>>& g, const vector<int>& order) {
    int n = (int)g.size();
    vector<char> blocked(n, 0), sel(n, 0);
    for (int u : order) {
        if (!blocked[u]) {
            sel[u] = 1;
            blocked[u] = 1;
            for (int v : g[u]) blocked[v] = 1;
        }
    }
    return sel;
}

struct Node {
    int deg;
    uint32_t rnd;
    int id;
};
struct Cmp {
    bool operator()(const Node& a, const Node& b) const {
        if (a.deg != b.deg) return a.deg > b.deg; // min-heap
        return a.rnd > b.rnd;
    }
};

static inline vector<char> greedyMinDegreeHeap(const vector<vector<int>>& g, FastRand& frng) {
    int n = (int)g.size();
    vector<int> deg(n);
    for (int i = 0; i < n; ++i) deg[i] = (int)g[i].size();
    vector<char> removed(n, 0), sel(n, 0);
    priority_queue<Node, vector<Node>, Cmp> pq;
    pq = {};
    for (int i = 0; i < n; ++i) pq.push({deg[i], frng.next(), i});
    while (!pq.empty()) {
        Node cur = pq.top(); pq.pop();
        int u = cur.id;
        if (removed[u]) continue;
        if (cur.deg != deg[u]) continue;
        removed[u] = 2;
        sel[u] = 1;
        for (int v : g[u]) {
            if (!removed[v]) {
                removed[v] = 1;
                for (int w : g[v]) {
                    if (!removed[w]) {
                        deg[w]--;
                        pq.push({deg[w], frng.next(), w});
                    }
                }
            }
        }
    }
    return sel;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N, M;
    if (!(cin >> N >> M)) return 0;

    vector<pair<int,int>> edges;
    edges.reserve(M);
    vector<int> degCnt(N, 0);
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u < 0 || v < 0 || u >= N || v >= N || u == v) continue;
        edges.emplace_back(u, v);
        degCnt[u]++;
        degCnt[v]++;
    }

    vector<vector<int>> g(N);
    for (int i = 0; i < N; ++i) g[i].reserve(degCnt[i]);
    for (auto &e : edges) {
        int u = e.first, v = e.second;
        g[u].push_back(v);
        g[v].push_back(u);
    }

    auto start = chrono::steady_clock::now();
    const double TIME_LIMIT = 1.9;

    uint64_t seed = (uint64_t)chrono::steady_clock::now().time_since_epoch().count();
    seed ^= (uint64_t)N * 0x9e3779b97f4a7c15ull;
    seed ^= (uint64_t)edges.size() * 0x85ebca6b;
    FastRand frng(seed);

    vector<int> baseOrder(N);
    iota(baseOrder.begin(), baseOrder.end(), 0);
    vector<int> staticDeg(N);
    for (int i = 0; i < N; ++i) staticDeg[i] = (int)g[i].size();

    // Initial runs
    vector<uint32_t> tieRand(N);
    for (int i = 0; i < N; ++i) tieRand[i] = frng.next();
    vector<int> order = baseOrder;
    sort(order.begin(), order.end(), [&](int a, int b) {
        if (staticDeg[a] != staticDeg[b]) return staticDeg[a] < staticDeg[b];
        return tieRand[a] < tieRand[b];
    });
    vector<char> bestSel = greedySequential(g, order);
    int bestK = 0;
    for (int i = 0; i < N; ++i) bestK += bestSel[i];

    // Random order run
    order = baseOrder;
    frng.shuffle(order.begin(), order.end());
    vector<char> selRand = greedySequential(g, order);
    int kRand = 0; for (int i = 0; i < N; ++i) kRand += selRand[i];
    if (kRand > bestK) { bestK = kRand; bestSel.swap(selRand); }

    // Min-degree heap run
    vector<char> selMinDeg = greedyMinDegreeHeap(g, frng);
    int kMinDeg = 0; for (int i = 0; i < N; ++i) kMinDeg += selMinDeg[i];
    if (kMinDeg > bestK) { bestK = kMinDeg; bestSel.swap(selMinDeg); }

    // Additional randomized runs within time
    int iter = 0;
    while (true) {
        auto now = chrono::steady_clock::now();
        double elapsed = chrono::duration<double>(now - start).count();
        if (elapsed > TIME_LIMIT) break;

        if (iter % 3 == 0) {
            order = baseOrder;
            frng.shuffle(order.begin(), order.end());
        } else if (iter % 3 == 1) {
            // Randomized degree bias: sort by random key divided by (deg+1)
            vector<pair<uint64_t,int>> keys;
            keys.reserve(N);
            for (int i = 0; i < N; ++i) {
                uint64_t r = frng.next64();
                // Create key that prefers small degrees: r / (deg+1)
                uint64_t key = r / (uint64_t)(staticDeg[i] + 1);
                keys.emplace_back(key, i);
            }
            sort(keys.begin(), keys.end(), [&](const auto& A, const auto& B){
                if (A.first != B.first) return A.first < B.first;
                return A.second < B.second;
            });
            order.resize(N);
            for (int i = 0; i < N; ++i) order[i] = keys[i].second;
        } else {
            // Degree ascending with fresh tie-breaks
            for (int i = 0; i < N; ++i) tieRand[i] = frng.next();
            order = baseOrder;
            sort(order.begin(), order.end(), [&](int a, int b) {
                if (staticDeg[a] != staticDeg[b]) return staticDeg[a] < staticDeg[b];
                return tieRand[a] < tieRand[b];
            });
        }

        vector<char> sel = greedySequential(g, order);
        int k = 0; for (int i = 0; i < N; ++i) k += sel[i];
        if (k > bestK) { bestK = k; bestSel.swap(sel); }
        iter++;
    }

    for (int i = 0; i < N; ++i) {
        cout << (bestSel[i] ? 1 : 0) << '\n';
    }
    return 0;
}