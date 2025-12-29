#include <bits/stdc++.h>
using namespace std;

struct Timer {
    chrono::steady_clock::time_point start;
    double limit_ms;
    Timer(double limit_ms) : start(chrono::steady_clock::now()), limit_ms(limit_ms) {}
    inline double elapsed_ms() const {
        return chrono::duration<double, std::milli>(chrono::steady_clock::now() - start).count();
    }
    inline bool time_up() const { return elapsed_ms() >= limit_ms; }
};

static inline int argmin3(int a0, int a1, int a2) {
    if (a0 <= a1 && a0 <= a2) return 0;
    if (a1 <= a0 && a1 <= a2) return 1;
    return 2;
}

void compute_s_and_b(const vector<vector<int>>& adj, const vector<int>& col, vector<array<int,3>>& s, int &b) {
    int n = adj.size();
    for (int i = 0; i < n; ++i) s[i] = {0,0,0};
    for (int u = 0; u < n; ++u) {
        int cu = col[u];
        for (int v : adj[u]) {
            int cv = col[v];
            s[u][cv] += 1;
        }
    }
    long long sum = 0;
    for (int i = 0; i < n; ++i) sum += s[i][col[i]];
    b = (int)(sum / 2);
}

int local_descent(const vector<vector<int>>& adj, vector<int>& col, vector<array<int,3>>& s, int &b, Timer& timer) {
    int n = adj.size();
    deque<int> q;
    vector<char> inq(n, 0);
    for (int v = 0; v < n; ++v) {
        int c = col[v];
        int best = argmin3(s[v][0], s[v][1], s[v][2]);
        if (s[v][best] < s[v][c]) {
            q.push_back(v);
            inq[v] = 1;
        }
    }
    int moves = 0;
    while (!q.empty()) {
        if (timer.time_up()) break;
        int v = q.front(); q.pop_front();
        inq[v] = 0;
        int c = col[v];
        int best = argmin3(s[v][0], s[v][1], s[v][2]);
        if (best != c && s[v][best] < s[v][c]) {
            int old_same = s[v][c];
            int new_same = s[v][best];
            b += (new_same - old_same);
            col[v] = best;
            ++moves;
            for (int u : adj[v]) {
                s[u][c] -= 1;
                s[u][best] += 1;
                int cu = col[u];
                int bu = argmin3(s[u][0], s[u][1], s[u][2]);
                if (s[u][bu] < s[u][cu] && !inq[u]) {
                    q.push_back(u);
                    inq[u] = 1;
                }
            }
        }
    }
    return moves;
}

void greedy_by_degree_init(const vector<vector<int>>& adj, vector<int>& col, mt19937& rng) {
    int n = adj.size();
    vector<int> order(n);
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [&](int a, int b){
        return adj[a].size() > adj[b].size();
    });
    vector<int> tmp(n, -1);
    uniform_int_distribution<int> dist(0,2);
    for (int v : order) {
        int cnt[3] = {0,0,0};
        for (int u : adj[v]) {
            int cu = tmp[u];
            if (cu != -1) cnt[cu]++;
        }
        int best = 0;
        int bestVal = cnt[0];
        for (int c = 1; c < 3; ++c) {
            if (cnt[c] < bestVal) { bestVal = cnt[c]; best = c; }
        }
        // randomize ties slightly
        vector<int> cands;
        int mn = min(cnt[0], min(cnt[1], cnt[2]));
        for (int c = 0; c < 3; ++c) if (cnt[c] == mn) cands.push_back(c);
        best = cands[dist(rng) % cands.size()];
        tmp[v] = best;
    }
    col = tmp;
}

void balanced_random_init(int n, vector<int>& col, mt19937& rng) {
    vector<int> idx(n);
    iota(idx.begin(), idx.end(), 0);
    shuffle(idx.begin(), idx.end(), rng);
    col.assign(n, 0);
    for (int i = 0; i < n; ++i) col[idx[i]] = i % 3;
}

void random_init(int n, vector<int>& col, mt19937& rng) {
    uniform_int_distribution<int> dist(0,2);
    col.resize(n);
    for (int i = 0; i < n; ++i) col[i] = dist(rng);
}

void perturb(vector<vector<int>>& adj, vector<int>& col, vector<array<int,3>>& s, int &b, int flips, mt19937& rng) {
    int n = adj.size();
    // Prepare badness list
    vector<pair<int,int>> bad(n);
    for (int i = 0; i < n; ++i) bad[i] = { s[i][col[i]], i };
    sort(bad.begin(), bad.end(), greater<pair<int,int>>());
    int pool = min(n, max(flips * 5, flips));
    uniform_int_distribution<int> pick(0, max(0, pool-1));
    uniform_int_distribution<int> colorDist(0,2);
    for (int f = 0; f < flips && pool > 0; ++f) {
        int idx = pick(rng);
        int v = bad[idx].second;
        int oldc = col[v];
        int newc = colorDist(rng);
        if (newc == oldc) newc = (oldc + 1 + colorDist(rng)%2) % 3;
        // Update b
        b += s[v][newc] - s[v][oldc];
        col[v] = newc;
        // Update neighbors' s
        for (int u : adj[v]) {
            s[u][oldc] -= 1;
            s[u][newc] += 1;
        }
        // s[v] unchanged
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m;
    if (!(cin >> n >> m)) {
        return 0;
    }
    vector<vector<int>> adj(n);
    adj.reserve(n);
    for (int i = 0; i < m; ++i) {
        int u, v; cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    if (m == 0) {
        for (int i = 0; i < n; ++i) {
            if (i) cout << ' ';
            cout << 1;
        }
        cout << '\n';
        return 0;
    }

    const double TIME_LIMIT_MS = 1800.0;
    Timer timer(TIME_LIMIT_MS);
    mt19937 rng((uint64_t)chrono::steady_clock::now().time_since_epoch().count());

    vector<int> best_col(n, 0);
    int best_b = INT_MAX;

    vector<int> col(n, 0);
    vector<array<int,3>> s(n);
    int b = 0;

    // First try: greedy by degree
    greedy_by_degree_init(adj, col, rng);
    compute_s_and_b(adj, col, s, b);
    local_descent(adj, col, s, b, timer);
    if (b < best_b) {
        best_b = b;
        best_col = col;
    }

    // Second try: balanced random
    if (!timer.time_up()) {
        balanced_random_init(n, col, rng);
        compute_s_and_b(adj, col, s, b);
        local_descent(adj, col, s, b, timer);
        if (b < best_b) {
            best_b = b;
            best_col = col;
        }
    }

    // Iterative improvement with restarts/perturbations
    int iter = 0;
    while (!timer.time_up()) {
        if (iter % 2 == 0) {
            // Perturb best solution
            col = best_col;
            compute_s_and_b(adj, col, s, b);
            int flips = max(1, (int)sqrt((double)n));
            perturb(adj, col, s, b, flips, rng);
        } else {
            // Random restart
            if (iter % 4 == 1) balanced_random_init(n, col, rng);
            else random_init(n, col, rng);
            compute_s_and_b(adj, col, s, b);
        }
        local_descent(adj, col, s, b, timer);
        if (b < best_b) {
            best_b = b;
            best_col = col;
        }
        ++iter;
        if (timer.time_up()) break;
    }

    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << (best_col[i] + 1);
    }
    cout << '\n';
    return 0;
}