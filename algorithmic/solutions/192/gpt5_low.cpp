#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) return 0;
    vector<vector<int>> adj(n);
    adj.reserve(n);
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
    m = (int)edges.size();
    if (m == 0) {
        for (int i = 0; i < n; ++i) {
            if (i) cout << ' ';
            cout << 0;
        }
        cout << '\n';
        return 0;
    }

    auto now = [](){ return chrono::high_resolution_clock::now(); };
    auto start_time = now();
    const double time_limit_sec = 1.8;

    mt19937 rng((uint32_t)chrono::steady_clock::now().time_since_epoch().count());

    vector<int> best_s(n, 0);
    long long best_cut = -1;

    auto compute_cut = [&](const vector<int>& s)->long long{
        long long c = 0;
        for (auto &e : edges) {
            if (s[e.first] != s[e.second]) ++c;
        }
        return c;
    };

    auto run_one = [&](vector<int>& s)->long long {
        int N = n;
        vector<int> gain(N, 0);
        // initial gains and cut
        long long cut = 0;
        for (auto &e : edges) {
            if (s[e.first] != s[e.second]) ++cut;
        }
        for (int v = 0; v < N; ++v) {
            int deg = (int)adj[v].size();
            int diff = 0;
            for (int u : adj[v]) {
                if (s[u] != s[v]) ++diff;
            }
            gain[v] = deg - 2*diff; // deg_same - deg_diff
        }

        deque<int> q;
        for (int i = 0; i < N; ++i) if (gain[i] > 0) q.push_back(i);

        while (!q.empty()) {
            if (chrono::duration<double>(now() - start_time).count() > time_limit_sec) break;
            int v = q.front(); q.pop_front();
            if (gain[v] <= 0) continue;
            int old_sv = s[v];
            int delta = gain[v];
            // flip v
            s[v] ^= 1;
            cut += delta;
            // update gains
            for (int u : adj[v]) {
                if (s[u] == old_sv) {
                    // was same, now different -> gain[u] -= 2
                    gain[u] -= 2;
                } else {
                    // was different, now same -> gain[u] += 2
                    gain[u] += 2;
                }
                if (gain[u] > 0) q.push_back(u);
            }
            gain[v] = -gain[v];
            if (gain[v] > 0) q.push_back(v);
        }
        return cut;
    };

    // Try multiple restarts until time limit
    int iter = 0;
    while (chrono::duration<double>(now() - start_time).count() < time_limit_sec) {
        vector<int> s(n);
        if (iter == 0) {
            // deterministic start: alternate
            for (int i = 0; i < n; ++i) s[i] = i & 1;
        } else {
            for (int i = 0; i < n; ++i) s[i] = rng() & 1;
        }
        long long cut = run_one(s);
        if (cut > best_cut) {
            best_cut = cut;
            best_s = s;
        }
        ++iter;
    }

    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << best_s[i];
    }
    cout << '\n';
    return 0;
}