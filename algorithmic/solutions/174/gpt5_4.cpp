#include <bits/stdc++.h>
using namespace std;

struct Solver {
    int n, m;
    vector<vector<int>> adj;
    vector<pair<int,int>> edges;
    vector<int> deg;
    mt19937 rng;
    chrono::steady_clock::time_point start_time;
    double time_limit_sec;

    Solver(int n_, int m_) : n(n_), m(m_), adj(n_), deg(n_,0) {
        rng.seed(uint64_t(chrono::high_resolution_clock::now().time_since_epoch().count()));
        time_limit_sec = 0.9; // time budget in seconds
    }

    inline bool time_up() {
        auto now = chrono::steady_clock::now();
        double elapsed = chrono::duration<double>(now - start_time).count();
        return elapsed > time_limit_sec;
    }

    void add_edge(int u, int v) {
        adj[u].push_back(v);
        adj[v].push_back(u);
        edges.emplace_back(u, v);
        deg[u]++; deg[v]++;
    }

    bool bipartite_coloring(vector<int>& col) {
        col.assign(n, -1);
        queue<int> q;
        for (int s = 0; s < n; ++s) {
            if (col[s] != -1) continue;
            col[s] = 0;
            q.push(s);
            while (!q.empty()) {
                int u = q.front(); q.pop();
                for (int v : adj[u]) {
                    if (col[v] == -1) {
                        col[v] = col[u] ^ 1;
                        q.push(v);
                    } else if (col[v] == col[u]) {
                        return false;
                    }
                }
            }
        }
        return true;
    }

    void greedy_initial(vector<int>& color) {
        color.assign(n, -1);
        vector<int> order(n);
        iota(order.begin(), order.end(), 0);
        vector<uint32_t> key(n);
        for (int i = 0; i < n; ++i) key[i] = rng();
        sort(order.begin(), order.end(), [&](int a, int b){
            if (deg[a] != deg[b]) return deg[a] > deg[b];
            return key[a] < key[b];
        });
        uniform_int_distribution<int> dist01(0, 1);
        for (int v : order) {
            int cnt[3] = {0,0,0};
            for (int u : adj[v]) {
                if (color[u] != -1) cnt[color[u]]++;
            }
            int bestC = 0;
            int bestVal = cnt[0];
            for (int c = 1; c < 3; ++c) {
                if (cnt[c] < bestVal) {
                    bestVal = cnt[c];
                    bestC = c;
                } else if (cnt[c] == bestVal) {
                    if (dist01(rng)) bestC = c;
                }
            }
            color[v] = bestC;
        }
    }

    void random_initial(vector<int>& color) {
        color.resize(n);
        for (int i = 0; i < n; ++i) color[i] = rng() % 3;
    }

    int compute_b(const vector<int>& color) {
        int b = 0;
        for (auto &e : edges) {
            if (color[e.first] == color[e.second]) b++;
        }
        return b;
    }

    int local_improve(vector<int>& color, vector<array<int,3>>& cnt, int b) {
        deque<int> dq;
        vector<char> inq(n, 0);
        for (int i = 0; i < n; ++i) { dq.push_back(i); inq[i] = 1; }
        uniform_int_distribution<int> rnd(0, INT_MAX);
        while (!dq.empty()) {
            if (time_up()) break;
            int v = dq.front(); dq.pop_front(); inq[v] = 0;
            int cur = color[v];
            int curCnt = cnt[v][cur];
            int minVal = cnt[v][0];
            int minC = 0;
            for (int c = 1; c < 3; ++c) {
                if (cnt[v][c] < minVal) {
                    minVal = cnt[v][c];
                    minC = c;
                } else if (cnt[v][c] == minVal) {
                    if ((rnd(rng) & 1)) minC = c; // random tie-break among minima
                }
            }
            if (minVal < curCnt) {
                int old = cur, neu = minC;
                int delta = curCnt - minVal; // reduction in conflicts
                color[v] = neu;
                b -= delta;
                // update neighbors
                for (int u : adj[v]) {
                    cnt[u][old]--;
                    cnt[u][neu]++;
                    if (!inq[u]) { dq.push_back(u); inq[u] = 1; }
                }
                // v's cnt remains the same (counts neighbor colors)
                // Consider re-checking v later after neighbors move
                // but neighbors will enqueue v when they move
            }
        }
        return b;
    }

    void run() {
        start_time = chrono::steady_clock::now();

        vector<int> best_color(n, 0);
        int best_b = INT_MAX;

        // Attempt perfect bipartite 2-coloring
        vector<int> bi;
        if (bipartite_coloring(bi)) {
            for (int i = 0; i < n; ++i) {
                cout << (bi[i] + 1) << (i + 1 == n ? '\n' : ' ');
            }
            return;
        }

        // Pre-alloc arrays used in runs
        vector<int> color(n, 0);
        vector<array<int,3>> cnt(n);

        int attempt = 0;
        while (true) {
            if (time_up()) break;
            // Choose initial method
            if (attempt % 2 == 0) {
                greedy_initial(color);
            } else {
                random_initial(color);
            }
            attempt++;

            // Build cnt and initial conflicts
            for (int i = 0; i < n; ++i) cnt[i] = {0,0,0};
            int b = 0;
            for (auto &e : edges) {
                int u = e.first, v = e.second;
                cnt[u][color[v]]++;
                cnt[v][color[u]]++;
                if (color[u] == color[v]) b++;
            }

            // Local improvement
            b = local_improve(color, cnt, b);

            if (b < best_b) {
                best_b = b;
                best_color = color;
                if (best_b == 0) break; // perfect 3-coloring found
            }

            if (time_up()) break;
        }

        for (int i = 0; i < n; ++i) {
            cout << (best_color[i] + 1) << (i + 1 == n ? '\n' : ' ');
        }
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m;
    if (!(cin >> n >> m)) {
        return 0;
    }
    Solver solver(n, m);
    for (int i = 0; i < m; ++i) {
        int u, v; cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        solver.add_edge(u, v);
    }
    solver.run();
    return 0;
}