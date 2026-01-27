#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static constexpr size_t BUFSIZE = 1 << 20;
    char buf[BUFSIZE];
    size_t idx = 0, size = 0;

    inline char readChar() {
        if (idx >= size) {
            size = fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }

    template <class T>
    bool readInt(T &out) {
        char c;
        do {
            c = readChar();
            if (!c) return false;
        } while (c <= ' ');

        T sign = 1;
        if constexpr (is_signed_v<T>) {
            if (c == '-') {
                sign = -1;
                c = readChar();
            }
        }

        T val = 0;
        while (c > ' ') {
            val = val * 10 + (c - '0');
            c = readChar();
        }
        out = val * sign;
        return true;
    }
};

static inline int countSet(const vector<uint8_t> &inIS) {
    int s = 0;
    for (uint8_t x : inIS) s += (x != 0);
    return s;
}

static inline bool validateIS(const vector<vector<int>> &adj, const vector<uint8_t> &inIS) {
    int n = (int)adj.size();
    for (int u = 0; u < n; ++u) {
        if (!inIS[u]) continue;
        for (int v : adj[u]) {
            if (v > u && inIS[v]) return false;
        }
    }
    return true;
}

static vector<uint8_t> greedyStatic(const vector<vector<int>> &adj, const vector<int> &deg, mt19937_64 &rng) {
    int n = (int)adj.size();
    vector<uint64_t> key(n);
    for (int i = 0; i < n; ++i) key[i] = (uint64_t(deg[i]) << 32) ^ (uint64_t)rng();

    vector<int> order(n);
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [&](int a, int b) { return key[a] < key[b]; });

    vector<uint8_t> forbidden(n, 0), inIS(n, 0);
    for (int v : order) {
        if (forbidden[v]) continue;
        inIS[v] = 1;
        forbidden[v] = 1;
        for (int u : adj[v]) forbidden[u] = 1;
    }
    return inIS;
}

static vector<uint8_t> greedyDynamicMinDegree(const vector<vector<int>> &adj, const vector<int> &deg, mt19937_64 &rng) {
    int n = (int)adj.size();
    vector<uint8_t> rem(n, 1), inIS(n, 0);
    vector<int> curDeg = deg;

    struct Node {
        int d;
        uint64_t r;
        int v;
    };
    struct Comp {
        bool operator()(const Node &a, const Node &b) const {
            if (a.d != b.d) return a.d > b.d;
            return a.r > b.r;
        }
    };
    priority_queue<Node, vector<Node>, Comp> pq;
    pq = decltype(pq)();

    for (int i = 0; i < n; ++i) pq.push(Node{curDeg[i], (uint64_t)rng(), i});

    auto removeFromRemaining = [&](int x) {
        rem[x] = 0;
        for (int nb : adj[x]) {
            if (rem[nb]) {
                --curDeg[nb];
                pq.push(Node{curDeg[nb], (uint64_t)rng(), nb});
            }
        }
    };

    while (!pq.empty()) {
        Node nd = pq.top();
        pq.pop();
        int v = nd.v;
        if (!rem[v]) continue;
        if (nd.d != curDeg[v]) continue;

        inIS[v] = 1;
        removeFromRemaining(v);
        for (int nb : adj[v]) {
            if (rem[nb]) removeFromRemaining(nb);
        }
    }
    return inIS;
}

static void improveSwap1(const vector<vector<int>> &adj, vector<uint8_t> &inIS, mt19937_64 &rng) {
    int n = (int)adj.size();
    vector<int> conflict(n, 0), witness(n, -1);

    int curSize = 0;
    for (int u = 0; u < n; ++u) {
        if (!inIS[u]) continue;
        ++curSize;
        for (int v : adj[u]) {
            ++conflict[v];
            witness[v] = u; // any IS neighbor
        }
    }

    auto findOne = [&](int v) -> int {
        for (int nb : adj[v]) if (inIS[nb]) return nb;
        return -1;
    };

    auto addV = [&](int x) {
        inIS[x] = 1;
        ++curSize;
        for (int nb : adj[x]) {
            ++conflict[nb];
            witness[nb] = x;
        }
    };

    auto removeV = [&](int x) {
        inIS[x] = 0;
        --curSize;
        for (int nb : adj[x]) {
            int c = --conflict[nb];
            if (c <= 0) {
                conflict[nb] = 0;
                witness[nb] = -1;
            } else if (c == 1) {
                int w = witness[nb];
                if (w >= 0 && inIS[w]) {
                    // ok
                } else {
                    witness[nb] = findOne(nb);
                }
            }
        }
    };

    constexpr int MAX_PASSES = 6;
    for (int pass = 0; pass < MAX_PASSES; ++pass) {
        vector<int> cand;
        cand.reserve(n);
        for (int v = 0; v < n; ++v) {
            if (!inIS[v] && conflict[v] == 1) cand.push_back(v);
        }
        if (cand.empty()) break;
        shuffle(cand.begin(), cand.end(), rng);

        int beforeSize = curSize;

        for (int v : cand) {
            if (inIS[v] || conflict[v] != 1) continue;

            int u = witness[v];
            if (u < 0 || !inIS[u]) u = findOne(v);
            if (u < 0 || !inIS[u]) continue;

            removeV(u);

            if (conflict[v] != 0) {
                addV(u);
                continue;
            }

            addV(v);

            vector<int> freeList;
            freeList.reserve(adj[u].size());
            for (int w : adj[u]) {
                if (!inIS[w] && conflict[w] == 0) freeList.push_back(w);
            }
            shuffle(freeList.begin(), freeList.end(), rng);
            for (int w : freeList) {
                if (!inIS[w] && conflict[w] == 0) addV(w);
            }
        }

        if (curSize == beforeSize) {
            // might still have performed plateau swaps, but limit passes anyway
            // break early to save time
            break;
        }
    }

    // Safety: ensure maximality by greedy-add any conflict==0 vertices (shouldn't exist)
    // (This keeps validity and can only increase size)
    vector<int> addables;
    addables.reserve(n);
    for (int v = 0; v < n; ++v) if (!inIS[v] && conflict[v] == 0) addables.push_back(v);
    shuffle(addables.begin(), addables.end(), rng);
    for (int v : addables) if (!inIS[v] && conflict[v] == 0) addV(v);
}

int main() {
    FastScanner fs;
    int N, M;
    if (!fs.readInt(N)) return 0;
    fs.readInt(M);

    vector<int> du(N, 0);
    vector<int> eu, ev;
    eu.reserve(M);
    ev.reserve(M);

    for (int i = 0; i < M; ++i) {
        int u, v;
        fs.readInt(u);
        fs.readInt(v);
        --u; --v;
        if (u == v) continue;
        eu.push_back(u);
        ev.push_back(v);
        ++du[u];
        ++du[v];
    }

    vector<vector<int>> adj(N);
    for (int i = 0; i < N; ++i) adj[i].reserve(du[i]);

    for (size_t i = 0; i < eu.size(); ++i) {
        int u = eu[i], v = ev[i];
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    for (int i = 0; i < N; ++i) {
        auto &a = adj[i];
        sort(a.begin(), a.end());
        a.erase(unique(a.begin(), a.end()), a.end());
    }

    vector<int> deg(N);
    for (int i = 0; i < N; ++i) deg[i] = (int)adj[i].size();

    uint64_t seed = chrono::high_resolution_clock::now().time_since_epoch().count();
    mt19937_64 rng(seed);

    vector<uint8_t> best(N, 0);
    int bestSize = -1;

    int T = 8;
    int Tdyn = 5;

    for (int iter = 0; iter < T; ++iter) {
        vector<uint8_t> cur;
        if (iter < Tdyn) cur = greedyDynamicMinDegree(adj, deg, rng);
        else cur = greedyStatic(adj, deg, rng);

        improveSwap1(adj, cur, rng);

        if (!validateIS(adj, cur)) {
            // Fallback if something went wrong (shouldn't)
            cur = greedyStatic(adj, deg, rng);
        }

        int sz = countSet(cur);
        if (sz > bestSize) {
            bestSize = sz;
            best.swap(cur);
        }
    }

    if (!validateIS(adj, best)) {
        best = greedyStatic(adj, deg, rng);
        if (!validateIS(adj, best)) {
            fill(best.begin(), best.end(), 0);
        }
    }

    string out;
    out.reserve((size_t)N * 2);
    for (int i = 0; i < N; ++i) {
        out.push_back(best[i] ? '1' : '0');
        out.push_back('\n');
    }
    cout << out;
    return 0;
}