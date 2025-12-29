#include <bits/stdc++.h>
using namespace std;

struct SplitMix64 {
    uint64_t x;
    explicit SplitMix64(uint64_t seed = 0) : x(seed) {}
    uint64_t next_u64() {
        uint64_t z = (x += 0x9e3779b97f4a7c15ULL);
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
        return z ^ (z >> 31);
    }
    uint32_t next_u32() { return (uint32_t)next_u64(); }
    int next_int(int lo, int hi) { // inclusive
        return lo + (int)(next_u64() % (uint64_t)(hi - lo + 1));
    }
};

static inline long long llabsll(long long x) { return x < 0 ? -x : x; }

struct SCC {
    int n;
    vector<vector<int>> g, rg;
    vector<int> comp, order, vis;
    int comps = 0;

    SCC(int n=0): n(n), g(n), rg(n), comp(n, -1), vis(n, 0) {}

    void add_edge(int u, int v) {
        g[u].push_back(v);
        rg[v].push_back(u);
    }

    void build() {
        order.clear();
        fill(vis.begin(), vis.end(), 0);
        for (int i = 0; i < n; i++) if (!vis[i]) {
            // iterative DFS for order
            vector<pair<int,int>> st;
            st.push_back({i, 0});
            vis[i] = 1;
            while (!st.empty()) {
                auto &[v, it] = st.back();
                if (it < (int)g[v].size()) {
                    int to = g[v][it++];
                    if (!vis[to]) {
                        vis[to] = 1;
                        st.push_back({to, 0});
                    }
                } else {
                    order.push_back(v);
                    st.pop_back();
                }
            }
        }

        fill(comp.begin(), comp.end(), -1);
        comps = 0;
        for (int idx = (int)order.size() - 1; idx >= 0; idx--) {
            int s = order[idx];
            if (comp[s] != -1) continue;
            // iterative DFS on reverse graph
            vector<int> st;
            st.push_back(s);
            comp[s] = comps;
            while (!st.empty()) {
                int v = st.back(); st.pop_back();
                for (int to : rg[v]) if (comp[to] == -1) {
                    comp[to] = comps;
                    st.push_back(to);
                }
            }
            comps++;
        }
    }
};

static long long simulate_error(const vector<int>& a, const vector<int>& b, const vector<int>& T, int L) {
    int N = (int)T.size();
    vector<int> cnt(N, 0);
    int cur = 0;
    for (int step = 0; step < L; step++) {
        int c = ++cnt[cur];
        cur = (c & 1) ? a[cur] : b[cur];
    }
    long long err = 0;
    for (int i = 0; i < N; i++) err += llabsll((long long)cnt[i] - (long long)T[i]);
    return err;
}

static bool strongly_connected(const vector<int>& a, const vector<int>& b) {
    int N = (int)a.size();
    SCC scc(N);
    for (int i = 0; i < N; i++) {
        scc.add_edge(i, a[i]);
        scc.add_edge(i, b[i]);
    }
    scc.build();
    return scc.comps == 1;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, L;
    cin >> N >> L;
    vector<int> T(N);
    for (int i = 0; i < N; i++) cin >> T[i];

    uint64_t seed = chrono::high_resolution_clock::now().time_since_epoch().count();
    SplitMix64 rng(seed);

    vector<long long> demand(N);
    for (int i = 0; i < N; i++) demand[i] = 2LL * (long long)T[i];

    const int M = 2 * N;
    vector<int> src(M), w(M), dest(M, 0);
    for (int i = 0; i < N; i++) {
        src[2 * i] = i;
        src[2 * i + 1] = i;
        w[2 * i] = T[i];
        w[2 * i + 1] = T[i];
    }

    vector<long long> r(N, 0);

    // Greedy assignment
    vector<int> order(M);
    iota(order.begin(), order.end(), 0);
    stable_sort(order.begin(), order.end(), [&](int i, int j) {
        if (w[i] != w[j]) return w[i] > w[j];
        return i < j;
    });

    auto choose_best_dest = [&](int wi) -> int {
        long long bestDelta = (1LL << 62);
        int best = -1;
        for (int j = 0; j < N; j++) {
            if (wi > 0 && demand[j] == 0) continue;
            long long oldv = llabsll(r[j] - demand[j]);
            long long newv = llabsll((r[j] + wi) - demand[j]);
            long long delta = newv - oldv;
            if (delta < bestDelta) {
                bestDelta = delta;
                best = j;
            } else if (delta == bestDelta && (rng.next_u32() & 3u) == 0u) {
                best = j;
            }
        }
        if (best == -1) best = rng.next_int(0, N - 1);
        return best;
    };

    for (int k : order) {
        if (w[k] == 0) {
            dest[k] = rng.next_int(0, N - 1);
            continue;
        }
        int d = choose_best_dest(w[k]);
        dest[k] = d;
        r[d] += w[k];
    }

    auto objective = [&]() -> long long {
        long long obj = 0;
        for (int j = 0; j < N; j++) obj += llabsll(r[j] - demand[j]);
        return obj;
    };

    long long obj = objective();

    // Local improvement (hill climbing)
    vector<int> defOrder;
    defOrder.reserve(N);
    const int ITERS = 300000;
    const int TOPK = 12;

    auto rebuild_def_order = [&]() {
        vector<pair<long long,int>> vec;
        vec.reserve(N);
        for (int j = 0; j < N; j++) {
            if (demand[j] == 0) continue;
            vec.push_back({demand[j] - r[j], j}); // positive = deficit
        }
        sort(vec.begin(), vec.end(), [&](auto &a, auto &b) {
            if (a.first != b.first) return a.first > b.first;
            return a.second < b.second;
        });
        defOrder.clear();
        for (auto &p : vec) defOrder.push_back(p.second);
        if (defOrder.empty()) {
            defOrder.resize(N);
            iota(defOrder.begin(), defOrder.end(), 0);
        }
    };

    rebuild_def_order();

    for (int iter = 0; iter < ITERS; iter++) {
        if ((iter % 2500) == 0) rebuild_def_order();

        int k = rng.next_int(0, M - 1);
        int wi = w[k];
        if (wi == 0) continue;

        int u = dest[k];
        int v;
        if ((iter & 1) == 0) {
            int K = min(TOPK, (int)defOrder.size());
            v = defOrder[rng.next_int(0, K - 1)];
        } else {
            v = rng.next_int(0, N - 1);
            if (demand[v] == 0) continue;
        }
        if (v == u) continue;

        long long oldU = llabsll(r[u] - demand[u]);
        long long newU = llabsll((r[u] - wi) - demand[u]);
        long long oldV = llabsll(r[v] - demand[v]);
        long long newV = llabsll((r[v] + wi) - demand[v]);
        long long delta = (newU + newV) - (oldU + oldV);
        if (delta < 0) {
            r[u] -= wi;
            r[v] += wi;
            dest[k] = v;
            obj += delta;
        }
    }

    // Build edges from assignments
    vector<int> a(N), b(N);
    for (int i = 0; i < N; i++) {
        int d0 = dest[2 * i];
        int d1 = dest[2 * i + 1];
        long long def0 = (d0 >= 0 ? demand[d0] - r[d0] : 0);
        long long def1 = (d1 >= 0 ? demand[d1] - r[d1] : 0);
        if (def0 > def1) { a[i] = d0; b[i] = d1; }
        else { a[i] = d1; b[i] = d0; }
    }

    // Enforce strong connectivity by linking SCCs in a cycle (try a few rounds)
    vector<long long> R(N, 0);
    auto rebuild_R = [&]() {
        fill(R.begin(), R.end(), 0);
        for (int i = 0; i < N; i++) {
            R[a[i]] += T[i];
            R[b[i]] += T[i];
        }
    };

    rebuild_R();

    for (int round = 0; round < 10; round++) {
        SCC scc(N);
        for (int i = 0; i < N; i++) {
            scc.add_edge(i, a[i]);
            scc.add_edge(i, b[i]);
        }
        scc.build();
        if (scc.comps == 1) break;

        int m = scc.comps;
        vector<int> rep(m, -1);
        for (int i = 0; i < N; i++) {
            int c = scc.comp[i];
            if (rep[c] == -1 || T[i] < T[rep[c]]) rep[c] = i;
        }

        for (int c = 0; c < m; c++) {
            int u = rep[c];
            int v = rep[(c + 1) % m];
            if (a[u] == v || b[u] == v) continue;
            int wu = T[u];

            auto edge_delta = [&](int oldDest) -> long long {
                long long beforeOld = llabsll(R[oldDest] - demand[oldDest]);
                long long afterOld = llabsll((R[oldDest] - wu) - demand[oldDest]);
                long long beforeNew = llabsll(R[v] - demand[v]);
                long long afterNew = llabsll((R[v] + wu) - demand[v]);
                return (afterOld - beforeOld) + (afterNew - beforeNew);
            };

            int bestWhich = -1;
            long long bestDelta = (1LL << 62);
            bool bestPrefer = false;

            for (int which = 0; which < 2; which++) {
                int oldDest = (which == 0 ? a[u] : b[u]);
                bool prefer = (scc.comp[oldDest] != scc.comp[u]); // if already leaving SCC, prefer to redirect that
                long long delta = edge_delta(oldDest);
                if (bestWhich == -1 ||
                    (prefer && !bestPrefer) ||
                    (prefer == bestPrefer && delta < bestDelta)) {
                    bestWhich = which;
                    bestDelta = delta;
                    bestPrefer = prefer;
                }
            }

            int oldDest = (bestWhich == 0 ? a[u] : b[u]);
            R[oldDest] -= wu;
            R[v] += wu;
            if (bestWhich == 0) a[u] = v;
            else b[u] = v;
        }

        rebuild_R();
    }

    // Small simulation-based hill climb
    long long bestErr = simulate_error(a, b, T, L);
    for (int it = 0; it < 25; it++) {
        int u = rng.next_int(0, N - 1);
        int which = rng.next_int(0, 1);
        int old = (which == 0 ? a[u] : b[u]);
        int nd = rng.next_int(0, N - 1);
        if (nd == old) continue;

        if (which == 0) a[u] = nd;
        else b[u] = nd;

        if (!strongly_connected(a, b)) {
            if (which == 0) a[u] = old;
            else b[u] = old;
            continue;
        }

        long long err = simulate_error(a, b, T, L);
        if (err < bestErr) {
            bestErr = err;
        } else {
            if (which == 0) a[u] = old;
            else b[u] = old;
        }
    }

    for (int i = 0; i < N; i++) {
        cout << a[i] << ' ' << b[i] << "\n";
    }
    return 0;
}