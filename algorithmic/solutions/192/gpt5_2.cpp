#include <bits/stdc++.h>
using namespace std;

static inline uint64_t now_seed() {
    return chrono::steady_clock::now().time_since_epoch().count();
}

struct MaxCutSolver {
    int n, m;
    vector<vector<int>> adj;
    vector<pair<int,int>> edges;
    vector<int> deg;

    mt19937_64 rng;
    chrono::steady_clock::time_point start_time;
    double time_limit;

    MaxCutSolver(int n, int m, vector<pair<int,int>>& edges, vector<vector<int>>& adj, vector<int>& deg, double tl)
        : n(n), m(m), edges(edges), adj(adj), deg(deg), rng(now_seed()), time_limit(tl) {
        start_time = chrono::steady_clock::now();
    }

    double elapsed() {
        auto t = chrono::steady_clock::now();
        return chrono::duration<double>(t - start_time).count();
    }

    void random_init(vector<int>& s) {
        uniform_int_distribution<int> bit(0, 1);
        for (int i = 0; i < n; ++i) s[i] = bit(rng);
    }

    void greedy_init(vector<int>& s) {
        vector<int> assigned(n, 0);
        vector<int> count0(n, 0), count1(n, 0);
        vector<int> order(n);
        iota(order.begin(), order.end(), 0);
        shuffle(order.begin(), order.end(), rng);
        for (int v : order) {
            int c0 = 0, c1 = 0;
            for (int u : adj[v]) if (assigned[u]) {
                if (s[u] == 0) c1++;
                else c0++;
            }
            if (c0 > c1) s[v] = 0;
            else if (c1 > c0) s[v] = 1;
            else s[v] = (rng() & 1);
            assigned[v] = 1;
        }
    }

    long long compute_ext_and_cut(const vector<int>& s, vector<int>& ext) {
        ext.assign(n, 0);
        long long cut = 0;
        for (auto &e : edges) {
            int u = e.first, v = e.second;
            if (s[u] != s[v]) {
                cut++;
                ext[u]++;
                ext[v]++;
            }
        }
        return cut;
    }

    void hill_climb(vector<int>& s, vector<int>& ext, long long& cut) {
        vector<int> gain(n);
        priority_queue<pair<int,int>> pq;
        for (int v = 0; v < n; ++v) {
            gain[v] = deg[v] - 2*ext[v];
            pq.emplace(gain[v], v);
        }
        while (!pq.empty()) {
            auto [g, v] = pq.top();
            if (g != gain[v]) { pq.pop(); continue; }
            if (g <= 0) break;
            pq.pop();
            int old_sv = s[v];
            s[v] ^= 1;
            cut += g;
            ext[v] = deg[v] - ext[v];
            for (int u : adj[v]) {
                if (s[u] == old_sv) ext[u]++; else ext[u]--;
                int gu = deg[u] - 2*ext[u];
                gain[u] = gu;
                pq.emplace(gu, u);
            }
            gain[v] = deg[v] - 2*ext[v];
            pq.emplace(gain[v], v);
            if (elapsed() > time_limit) break;
        }
    }

    long long KL_pass(vector<int>& s, vector<int>& ext, long long& cut) {
        vector<int> gain(n);
        for (int v = 0; v < n; ++v) gain[v] = deg[v] - 2*ext[v];
        vector<char> locked(n, 0);
        priority_queue<pair<int,int>> pq;
        for (int v = 0; v < n; ++v) pq.emplace(gain[v], v);

        vector<int> order;
        vector<int> step_gain;
        order.reserve(n);
        step_gain.reserve(n);

        int steps = 0;
        while (steps < n && !pq.empty()) {
            int v = -1, gv = INT_MIN;
            while (!pq.empty()) {
                auto [g, x] = pq.top();
                if (g != gain[x] || locked[x]) { pq.pop(); continue; }
                v = x; gv = g; break;
            }
            if (v == -1) break;

            order.push_back(v);
            step_gain.push_back(gv);
            locked[v] = 1;

            int old_sv = s[v];
            s[v] ^= 1;
            cut += gv;
            ext[v] = deg[v] - ext[v];
            for (int u : adj[v]) {
                if (s[u] == old_sv) ext[u]++; else ext[u]--;
                if (!locked[u]) {
                    gain[u] = deg[u] - 2*ext[u];
                    pq.emplace(gain[u], u);
                }
            }
            steps++;

            if (elapsed() > time_limit) break;
        }

        long long bestSum = LLONG_MIN;
        int bestK = 0;
        long long sum = 0;
        for (int i = 0; i < (int)step_gain.size(); ++i) {
            sum += step_gain[i];
            if (sum > bestSum) { bestSum = sum; bestK = i + 1; }
        }

        if (bestSum <= 0) {
            for (int i = (int)order.size() - 1; i >= 0; --i) {
                int v = order[i];
                int old_sv = s[v];
                s[v] ^= 1;
                int g = deg[v] - 2*ext[v];
                cut += g;
                ext[v] = deg[v] - ext[v];
                for (int u : adj[v]) {
                    if (s[u] == old_sv) ext[u]++; else ext[u]--;
                }
            }
            return 0;
        } else {
            for (int i = (int)order.size() - 1; i >= bestK; --i) {
                int v = order[i];
                int old_sv = s[v];
                s[v] ^= 1;
                int g = deg[v] - 2*ext[v];
                cut += g;
                ext[v] = deg[v] - ext[v];
                for (int u : adj[v]) {
                    if (s[u] == old_sv) ext[u]++; else ext[u]--;
                }
            }
            return bestSum;
        }
    }

    void solve(vector<int>& best_s) {
        if (m == 0) {
            best_s.assign(n, 0);
            return;
        }

        long long best_cut = -1;
        vector<int> s(n), ext(n);
        vector<int> s_best(n);

        int restart = 0;
        const int MAX_RESTARTS = 50;

        while (elapsed() < time_limit && restart < MAX_RESTARTS) {
            if ((restart & 1) == 0) random_init(s);
            else greedy_init(s);

            long long cut = compute_ext_and_cut(s, ext);

            hill_climb(s, ext, cut);

            // KL passes with hill climbing in between
            for (int pass = 0; pass < 10; ++pass) {
                if (elapsed() > time_limit) break;
                long long imp = KL_pass(s, ext, cut);
                if (imp <= 0) break;
                hill_climb(s, ext, cut);
            }

            if (cut > best_cut) {
                best_cut = cut;
                s_best = s;
            }

            restart++;
        }

        best_s = s_best;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) {
        return 0;
    }

    vector<vector<int>> adj(n);
    vector<pair<int,int>> edges;
    edges.reserve(m);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        adj[u].push_back(v);
        adj[v].push_back(u);
        edges.emplace_back(u, v);
    }

    vector<int> deg(n);
    for (int i = 0; i < n; ++i) deg[i] = (int)adj[i].size();

    double TIME_LIMIT = 1.8; // seconds
    MaxCutSolver solver(n, (int)edges.size(), edges, adj, deg, TIME_LIMIT);
    vector<int> best_s;
    solver.solve(best_s);

    if (best_s.empty()) best_s.assign(n, 0);
    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << (best_s[i] & 1);
    }
    cout << '\n';
    return 0;
}