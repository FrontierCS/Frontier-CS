#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static constexpr size_t BUFSIZE = 1 << 20;
    int idx = 0, size = 0;
    char buf[BUFSIZE];

    inline char read() {
        if (idx >= size) {
            size = (int)fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }

    template <class T>
    bool readInt(T &out) {
        char c;
        do {
            c = read();
            if (!c) return false;
        } while (c <= ' ');

        T sign = 1;
        if (c == '-') {
            sign = -1;
            c = read();
        }

        T val = 0;
        while (c > ' ') {
            val = val * 10 + (c - '0');
            c = read();
        }
        out = val * sign;
        return true;
    }
};

static inline long long nowMs() {
    using namespace std::chrono;
    return duration_cast<milliseconds>(steady_clock::now().time_since_epoch()).count();
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    FastScanner fs;
    int N, M;
    if (!fs.readInt(N)) return 0;
    fs.readInt(M);

    const int MAXB = 16; // ceil(1000/64)=16
    int B = (N + 63) >> 6;

    vector<array<uint64_t, MAXB>> mask(N);
    for (int i = 0; i < N; i++) mask[i].fill(0);

    for (int i = 0; i < M; i++) {
        int u, v;
        fs.readInt(u); fs.readInt(v);
        --u; --v;
        if (u == v) continue;
        mask[u][v >> 6] |= (1ULL << (v & 63));
        mask[v][u >> 6] |= (1ULL << (u & 63));
    }

    vector<vector<int>> adj(N);
    vector<int> deg(N, 0);
    for (int i = 0; i < N; i++) {
        adj[i].clear();
        for (int w = 0; w < B; w++) {
            uint64_t x = mask[i][w];
            while (x) {
                int b = __builtin_ctzll(x);
                int v = (w << 6) + b;
                if (v < N && v != i) {
                    adj[i].push_back(v);
                    deg[i]++;
                }
                x &= x - 1;
            }
        }
    }

    vector<int> baseOrder(N);
    iota(baseOrder.begin(), baseOrder.end(), 0);
    stable_sort(baseOrder.begin(), baseOrder.end(), [&](int a, int b) {
        if (deg[a] != deg[b]) return deg[a] < deg[b];
        return a < b;
    });

    mt19937 rng((uint32_t)chrono::high_resolution_clock::now().time_since_epoch().count());

    vector<char> bestSet(N, 0);
    int bestK = -1;

    vector<char> inSet(N, 0);
    vector<int> conf(N, 0);

    auto addVertex = [&](int v) {
        inSet[v] = 1;
        for (int u : adj[v]) conf[u]++;
    };
    auto removeVertex = [&](int v) {
        inSet[v] = 0;
        for (int u : adj[v]) conf[u]--;
    };
    auto countK = [&]() -> int {
        int k = 0;
        for (int i = 0; i < N; i++) k += (int)inSet[i];
        return k;
    };
    auto augmentAll = [&]() {
        for (int v : baseOrder) {
            if (!inSet[v] && conf[v] == 0) addVertex(v);
        }
    };

    auto improveOnce = [&](long long deadlineMs) -> bool {
        vector<int> setOrder;
        setOrder.reserve(N);
        for (int i = 0; i < N; i++) if (inSet[i]) setOrder.push_back(i);
        shuffle(setOrder.begin(), setOrder.end(), rng);

        array<uint64_t, MAXB> lm;

        for (int u : setOrder) {
            if (nowMs() >= deadlineMs) return false;

            vector<int> L;
            L.reserve(adj[u].size());
            for (int v : adj[u]) {
                if (!inSet[v] && conf[v] == 1) L.push_back(v);
            }
            if ((int)L.size() < 2) continue;

            lm.fill(0);
            for (int v : L) lm[v >> 6] |= (1ULL << (v & 63));

            int a = -1, b = -1;
            for (int x : L) {
                int wx = x >> 6, bx = x & 63;
                for (int w = 0; w < B; w++) {
                    uint64_t tmp = lm[w] & ~mask[x][w];
                    if (w == wx) tmp &= ~(1ULL << bx);
                    if (tmp) {
                        int t = __builtin_ctzll(tmp);
                        int y = (w << 6) + t;
                        if (y >= 0 && y < N) {
                            a = x; b = y;
                            break;
                        }
                    }
                }
                if (a != -1) break;
            }
            if (a == -1) continue;

            // Apply 1->2 (or more) exchange: remove u, add a,b, then try add more from L and augment globally
            removeVertex(u);

            if (!inSet[a] && conf[a] == 0) addVertex(a);
            if (!inSet[b] && conf[b] == 0) addVertex(b);

            // Try to add more vertices from L (many become free after removing u)
            // Use a light heuristic order: lower degree first with random tie
            vector<int> L2 = L;
            if (L2.size() > 2) {
                // Partial shuffle for diversity without too much cost
                shuffle(L2.begin(), L2.end(), rng);
                stable_sort(L2.begin(), L2.end(), [&](int p, int q) {
                    if (deg[p] != deg[q]) return deg[p] < deg[q];
                    return p < q;
                });
            }
            for (int v : L2) {
                if (!inSet[v] && conf[v] == 0) addVertex(v);
            }

            augmentAll();
            return true;
        }
        return false;
    };

    const long long startMs = nowMs();
    const long long deadlineMs = startMs + 1850; // keep margin

    int iter = 0;
    vector<int> order(N);

    while (nowMs() < deadlineMs) {
        iter++;

        fill(inSet.begin(), inSet.end(), 0);
        fill(conf.begin(), conf.end(), 0);

        // Build initial solution
        iota(order.begin(), order.end(), 0);

        int strat = iter % 5;
        if (strat == 0) {
            shuffle(order.begin(), order.end(), rng);
        } else if (strat == 1 || strat == 2 || strat == 3) {
            vector<uint32_t> key(N);
            for (int i = 0; i < N; i++) key[i] = rng();
            sort(order.begin(), order.end(), [&](int a, int b) {
                if (deg[a] != deg[b]) return deg[a] < deg[b];
                return key[a] < key[b];
            });
        } else { // strat == 4 diversify: sometimes prefer higher degree first (can help in dense graphs)
            vector<uint32_t> key(N);
            for (int i = 0; i < N; i++) key[i] = rng();
            sort(order.begin(), order.end(), [&](int a, int b) {
                if (deg[a] != deg[b]) return deg[a] > deg[b];
                return key[a] < key[b];
            });
        }

        for (int v : order) {
            if (!inSet[v] && conf[v] == 0) addVertex(v);
        }

        // Local improvement
        augmentAll();
        while (nowMs() < deadlineMs) {
            if (!improveOnce(deadlineMs)) break;
        }

        int k = countK();
        if (k > bestK) {
            bestK = k;
            for (int i = 0; i < N; i++) bestSet[i] = inSet[i];
        }
    }

    // Final safety repair to ensure independence (should be unnecessary, but safe)
    vector<char> ans = bestSet;
    vector<int> c(N, 0);
    for (int i = 0; i < N; i++) if (ans[i]) {
        int cnt = 0;
        for (int j : adj[i]) if (ans[j]) cnt++;
        c[i] = cnt;
    }
    bool changed = true;
    while (changed) {
        changed = false;
        int worst = -1, worstVal = 0;
        for (int i = 0; i < N; i++) {
            if (ans[i] && c[i] > worstVal) {
                worstVal = c[i];
                worst = i;
            }
        }
        if (worst != -1) {
            ans[worst] = 0;
            for (int j : adj[worst]) if (ans[j]) c[j]--;
            c[worst] = 0;
            changed = true;
        }
    }

    for (int i = 0; i < N; i++) {
        cout << (ans[i] ? 1 : 0) << "\n";
    }
    return 0;
}