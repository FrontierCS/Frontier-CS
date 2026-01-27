#include <bits/stdc++.h>
using namespace std;

static const int MAXN = 1024;

using BS = bitset<MAXN>;

struct RNG {
    uint64_t s;
    RNG() {
        uint64_t x = chrono::high_resolution_clock::now().time_since_epoch().count();
        s = splitmix64(x);
    }
    static uint64_t splitmix64(uint64_t x) {
        x += 0x9e3779b97f4a7c15ULL;
        x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
        x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
        return x ^ (x >> 31);
    }
    inline uint64_t next_u64() {
        s = splitmix64(s);
        return s;
    }
    inline int next_int(int l, int r) { // inclusive
        uint64_t x = next_u64();
        return l + int(x % (uint64_t)(r - l + 1));
    }
    inline double next_double() {
        return (next_u64() >> 11) * (1.0 / 9007199254740992.0);
    }
};

int N;
long long M;
vector<BS> adj;
vector<int> degs;
RNG rng;

struct Clique {
    BS set;
    vector<int> nodes;
    inline int size() const { return (int)nodes.size(); }
    inline bool contains(int v) const { return set[v]; }
    inline void add(int v) { if (!set[v]) { set.set(v); nodes.push_back(v); } }
    inline void clear() { set.reset(); nodes.clear(); }
};

inline int pick_random_from_bitset(const BS& S) {
    int cnt = (int)S.count();
    if (cnt == 0) return -1;
    int k = rng.next_int(0, cnt - 1);
    for (int i = 0; i < N; ++i) {
        if (S[i]) {
            if (k == 0) return i;
            --k;
        }
    }
    return -1;
}

static int scratchScore[MAXN];

int pick_best_with_ties(const BS& R, const vector<BS>& adj) {
    int sMax = -1;
    for (int v = 0; v < N; ++v) {
        if (R[v]) {
            // number of neighbors of v within R
            int s = (int)( (adj[v] & R).count() );
            scratchScore[v] = s;
            if (s > sMax) sMax = s;
        } else {
            scratchScore[v] = -1;
        }
    }
    // collect all v with s == sMax
    int cnt = 0;
    for (int v = 0; v < N; ++v) if (R[v] && scratchScore[v] == sMax) cnt++;
    if (cnt == 0) return -1;
    int kth = rng.next_int(0, cnt - 1);
    for (int v = 0; v < N; ++v) {
        if (R[v] && scratchScore[v] == sMax) {
            if (kth == 0) return v;
            --kth;
        }
    }
    return -1;
}

void greedy_extend(BS& curSet, BS R, vector<int>& added, const vector<BS>& adj) {
    while (R.any()) {
        int v;
        if (R.count() == 1) {
            // pick the only vertex
            for (int i = 0; i < N; ++i) if (R[i]) { v = i; break; }
        } else {
            v = pick_best_with_ties(R, adj);
            if (v < 0) break;
        }
        curSet.set(v);
        added.push_back(v);
        R &= adj[v];
    }
}

Clique greedy_build_all(const vector<BS>& adj, int mode) {
    // mode:
    // 0: start from empty
    // 1: start from a random vertex
    // 2: start from a random edge (random vertex and a random neighbor)
    Clique cl;
    BS R;
    R.reset();
    if (mode == 0) {
        // all vertices are candidates
        for (int i = 0; i < N; ++i) R.set(i);
    } else if (mode == 1) {
        int v = rng.next_int(0, N - 1);
        cl.add(v);
        R = adj[v];
    } else { // mode == 2
        int v = rng.next_int(0, N - 1);
        if (adj[v].any()) {
            int u = pick_random_from_bitset(adj[v]);
            if (u == -1) {
                for (int i = 0; i < N; ++i) R.set(i);
            } else {
                cl.add(v);
                cl.add(u);
                R = adj[v] & adj[u];
            }
        } else {
            for (int i = 0; i < N; ++i) R.set(i);
        }
    }
    vector<int> added;
    greedy_extend(cl.set, R, added, adj);
    // Build nodes from set: order = [existing nodes] + added
    // Our cl.nodes has any initial seeds already.
    for (int v : added) cl.nodes.push_back(v);
    return cl;
}

bool improve_oneswap(Clique& cl, const vector<BS>& adj) {
    if (cl.size() <= 1) return false;
    // randomize order of trying which vertex to remove
    vector<int> order = cl.nodes;
    // shuffle order a bit
    if (order.size() > 1) {
        for (int i = (int)order.size() - 1; i > 0; --i) {
            int j = rng.next_int(0, i);
            swap(order[i], order[j]);
        }
    }
    BS clSet = cl.set;
    for (int w : order) {
        BS T;
        T.set(); // all bits
        for (int x : cl.nodes) {
            if (x == w) continue;
            T &= adj[x];
        }
        // exclude current clique vertices
        T &= ~clSet;
        // need at least two vertices in T to have potential to grow
        if (T.count() < 2) continue;
        // Try to build a clique in T and see if we can increase size
        BS base = clSet;
        base.reset(w);
        vector<int> added;
        greedy_extend(base, T, added, adj);
        int newSize = (int)base.count();
        if (newSize > cl.size()) {
            // update clique
            cl.set = base;
            cl.nodes.clear();
            cl.nodes.reserve(newSize);
            for (int i = 0; i < N; ++i) if (cl.set[i]) cl.nodes.push_back(i);
            return true;
        }
    }
    return false;
}

Clique degree_order_greedy(const vector<BS>& adj, const vector<int>& degs) {
    vector<int> ord(N);
    iota(ord.begin(), ord.end(), 0);
    sort(ord.begin(), ord.end(), [&](int a, int b){
        if (degs[a] != degs[b]) return degs[a] > degs[b];
        return a < b;
    });
    Clique cl;
    for (int v : ord) {
        // check if v is adjacent to all nodes in current clique
        // i.e., no node in clique is a non-neighbor of v
        // equivalently (cl.set & ~adj[v]) is empty
        if (((cl.set & (~adj[v])).any()) == false) {
            cl.add(v);
        }
    }
    return cl;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> N >> M)) {
        return 0;
    }
    adj.assign(N, BS());
    for (long long i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        if (u >= 0 && u < N && v >= 0 && v < N) {
            adj[u].set(v);
            adj[v].set(u);
        }
    }
    degs.assign(N, 0);
    for (int i = 0; i < N; ++i) degs[i] = (int)adj[i].count();

    auto start = chrono::steady_clock::now();
    const int TIME_LIMIT_MS = 1900;

    Clique best;
    // Initial attempt: degree order greedy
    {
        Clique init = degree_order_greedy(adj, degs);
        best = init;
    }
    // Try to improve initial best via 1-swap few times
    {
        for (int iter = 0; iter < 2; ++iter) {
            bool imp = improve_oneswap(best, adj);
            if (!imp) break;
        }
    }

    // Multi-start greedy with local improvement
    int modes[3] = {0,1,2};
    int mode_count = 3;

    while (true) {
        auto now = chrono::steady_clock::now();
        int elapsed = (int)chrono::duration_cast<chrono::milliseconds>(now - start).count();
        if (elapsed > TIME_LIMIT_MS) break;

        int mode = modes[rng.next_int(0, mode_count - 1)];
        Clique cur = greedy_build_all(adj, mode);

        // Local improvement: try a few 1-swap steps
        for (int rep = 0; rep < 3; ++rep) {
            if (!improve_oneswap(cur, adj)) break;
            auto now2 = chrono::steady_clock::now();
            if ((int)chrono::duration_cast<chrono::milliseconds>(now2 - start).count() > TIME_LIMIT_MS) break;
        }

        if (cur.size() > best.size()) {
            best = cur;
        }
    }

    // Output solution: exactly N lines of 0/1
    for (int i = 0; i < N; ++i) {
        cout << (best.set[i] ? 1 : 0) << '\n';
    }
    return 0;
}