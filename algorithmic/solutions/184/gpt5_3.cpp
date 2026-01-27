#include <bits/stdc++.h>
using namespace std;

struct Timer {
    chrono::steady_clock::time_point start;
    double limit_sec;
    Timer(double lim=1.95) { start = chrono::steady_clock::now(); limit_sec = lim; }
    inline bool time_up() const {
        auto now = chrono::steady_clock::now();
        double elapsed = chrono::duration<double>(now - start).count();
        return elapsed > limit_sec;
    }
    inline double elapsed() const {
        auto now = chrono::steady_clock::now();
        return chrono::duration<double>(now - start).count();
    }
};

static inline int popcountll(uint64_t x){ return __builtin_popcountll(x); }

vector<pair<int,int>> read_edges_and_dedup(int N, int M) {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    vector<pair<int,int>> E;
    E.reserve(M);
    for (int i = 0; i < M; ++i) {
        int u, v;
        if(!(cin >> u >> v)) break;
        --u; --v;
        if (u == v) continue;
        if (u > v) swap(u, v);
        E.emplace_back(u, v);
    }
    sort(E.begin(), E.end());
    E.erase(unique(E.begin(), E.end()), E.end());
    return E;
}

void build_adj(int N, const vector<pair<int,int>>& E,
               vector<vector<int>>& adj,
               vector<vector<uint64_t>>& adjmask) {
    adj.assign(N, {});
    adjmask.assign(N, {});
    int W = (N + 63) / 64;
    for (int i = 0; i < N; ++i) adjmask[i].assign(W, 0ull);
    for (auto &e : E) {
        int u = e.first, v = e.second;
        adj[u].push_back(v);
        adj[v].push_back(u);
        adjmask[u][v >> 6] |= (1ull << (v & 63));
        adjmask[v][u >> 6] |= (1ull << (u & 63));
    }
}

vector<char> greedy_MIS(int N, const vector<vector<int>>& adj, mt19937_64& rng) {
    vector<char> active(N, 1), selected(N, 0);
    vector<int> deg(N, 0);
    for (int i = 0; i < N; ++i) deg[i] = (int)adj[i].size();
    using PQNode = pair<pair<int,int>, int>; // ((deg, tie), v)
    priority_queue<PQNode, vector<PQNode>, greater<PQNode>> pq;
    uniform_int_distribution<int> tie_dist(INT_MIN, INT_MAX);
    for (int i = 0; i < N; ++i) pq.push({{deg[i], tie_dist(rng)}, i});
    int active_cnt = N;
    while (active_cnt > 0 && !pq.empty()) {
        auto cur = pq.top(); pq.pop();
        int u = cur.second;
        if (!active[u]) continue;
        if (cur.first.first != deg[u]) continue;
        selected[u] = 1;
        active[u] = 0;
        --active_cnt;
        for (int a : adj[u]) {
            if (!active[a]) continue;
            active[a] = 0;
            --active_cnt;
            for (int w : adj[a]) {
                if (!active[w]) continue;
                --deg[w];
                pq.push({{deg[w], tie_dist(rng)}, w});
            }
        }
    }
    return selected;
}

void compute_conflict_and_owner(int N, const vector<pair<int,int>>& E,
                                const vector<char>& selected,
                                vector<int>& conflict, vector<int>& owner) {
    conflict.assign(N, 0);
    owner.assign(N, -1);
    for (auto &e : E) {
        int u = e.first, v = e.second;
        if (selected[u] && !selected[v]) {
            int c = ++conflict[v];
            if (c == 1) owner[v] = u;
            else owner[v] = -2;
        }
        if (selected[v] && !selected[u]) {
            int c = ++conflict[u];
            if (c == 1) owner[u] = v;
            else owner[u] = -2;
        }
    }
}

void augment_to_maximal(int N, vector<char>& selected,
                        const vector<pair<int,int>>& E,
                        const vector<vector<int>>& adj) {
    vector<int> conflict(N, 0);
    for (auto &e : E) {
        int u = e.first, v = e.second;
        if (selected[u] && !selected[v]) conflict[v]++;
        if (selected[v] && !selected[u]) conflict[u]++;
    }
    deque<int> dq;
    vector<char> inq(N, 0);
    for (int i = 0; i < N; ++i) {
        if (!selected[i] && conflict[i] == 0) {
            dq.push_back(i);
            inq[i] = 1;
        }
    }
    while (!dq.empty()) {
        int v = dq.front(); dq.pop_front();
        inq[v] = 0;
        if (selected[v] || conflict[v] != 0) continue;
        selected[v] = 1;
        for (int u : adj[v]) {
            if (!selected[u]) {
                conflict[u]++;
            }
        }
    }
}

bool two_improve_and_augment(int N, vector<char>& selected,
                             const vector<pair<int,int>>& E,
                             const vector<vector<uint64_t>>& adjmask,
                             const vector<vector<int>>& adj) {
    vector<int> conflict, owner;
    compute_conflict_and_owner(N, E, selected, conflict, owner);
    vector<vector<int>> group(N);
    for (int i = 0; i < N; ++i) {
        if (!selected[i] && conflict[i] == 1 && owner[i] >= 0) {
            group[owner[i]].push_back(i);
        }
    }
    int W = (N + 63) / 64;
    for (int s = 0; s < N; ++s) {
        if (!selected[s]) continue;
        auto &L = group[s];
        if ((int)L.size() < 2) continue;
        vector<uint64_t> Lmask(W, 0ull);
        for (int x : L) Lmask[x >> 6] |= (1ull << (x & 63));
        for (int x : L) {
            int xb = x >> 6, xo = x & 63;
            int y = -1;
            for (int w = 0; w < W; ++w) {
                uint64_t tmp = Lmask[w] & ~(adjmask[x][w]);
                if (w == xb) tmp &= ~(1ull << xo);
                if (tmp) {
                    int bit = __builtin_ctzll(tmp);
                    int cand = w * 64 + bit;
                    if (cand < N) { y = cand; break; }
                }
            }
            if (y != -1) {
                selected[s] = 0;
                selected[x] = 1;
                selected[y] = 1;
                augment_to_maximal(N, selected, E, adj);
                return true;
            }
        }
    }
    return false;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N, M;
    if (!(cin >> N >> M)) {
        return 0;
    }
    Timer timer(1.95);
    auto E = read_edges_and_dedup(N, M);
    vector<vector<int>> adj;
    vector<vector<uint64_t>> adjmask;
    build_adj(N, E, adj, adjmask);

    random_device rd;
    uint64_t seed = chrono::high_resolution_clock::now().time_since_epoch().count() ^ (uint64_t)rd();
    mt19937_64 rng(seed);

    vector<char> best(N, 0);
    int bestSize = 0;

    // At least one run
    int runs = 0;
    while (true) {
        if (timer.time_up() && runs > 0) break;
        vector<char> selected = greedy_MIS(N, adj, rng);

        // 1-2 swap local improvements with augmentation
        while (!timer.time_up()) {
            bool improved = two_improve_and_augment(N, selected, E, adjmask, adj);
            if (!improved) break;
        }

        int sz = 0;
        for (int i = 0; i < N; ++i) if (selected[i]) ++sz;
        if (sz > bestSize) {
            bestSize = sz;
            best = selected;
        }
        runs++;
        if (timer.time_up()) break;
    }

    for (int i = 0; i < N; ++i) {
        cout << (best[i] ? 1 : 0) << '\n';
    }
    return 0;
}