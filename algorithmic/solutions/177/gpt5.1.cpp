#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    vector<vector<int>> adj(n);
    vector<pair<int,int>> edges;
    edges.reserve(m);

    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        adj[u].push_back(v);
        adj[v].push_back(u);
        edges.emplace_back(u, v);
    }

    // RNG
    mt19937_64 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());

    // Initial greedy coloring
    vector<int> color(n, -1);
    vector<int> order(n);
    for (int i = 0; i < n; ++i) order[i] = i;
    shuffle(order.begin(), order.end(), rng);

    for (int idx = 0; idx < n; ++idx) {
        int v = order[idx];
        int cntc[3] = {0, 0, 0};
        for (int u : adj[v]) {
            int cu = color[u];
            if (cu != -1) cntc[cu]++;
        }
        int best_color = 0;
        int best_cnt = cntc[0];
        for (int c = 1; c < 3; ++c) {
            if (cntc[c] < best_cnt) {
                best_cnt = cntc[c];
                best_color = c;
            }
        }
        color[v] = best_color;
    }

    // Prepare structures for local search
    vector<array<int,3>> cnt(n);
    for (int i = 0; i < n; ++i) cnt[i] = {0,0,0};
    vector<int> w(n, 0);               // number of conflicting edges incident to each vertex
    long long b = 0;                   // total number of conflicting edges

    for (const auto &e : edges) {
        int u = e.first;
        int v = e.second;
        int cu = color[u];
        int cv = color[v];
        cnt[u][cv]++;
        cnt[v][cu]++;
        if (cu == cv) {
            w[u]++;
            w[v]++;
            b++;
        }
    }

    vector<int> conflict_list;
    conflict_list.reserve(n);
    vector<int> pos(n, -1);

    auto add_conflict = [&](int v) {
        if (pos[v] == -1) {
            pos[v] = (int)conflict_list.size();
            conflict_list.push_back(v);
        }
    };

    auto remove_conflict = [&](int v) {
        int idx = pos[v];
        if (idx == -1) return;
        int last = conflict_list.back();
        conflict_list[idx] = last;
        pos[last] = idx;
        conflict_list.pop_back();
        pos[v] = -1;
    };

    for (int v = 0; v < n; ++v) {
        if (w[v] > 0) add_conflict(v);
    }

    const long long ITER_LIMIT = 4000000LL;
    const long long OPS_LIMIT  = 80000000LL; // limit on neighbor-operations

    long long iter = 0;
    long long ops  = 0;

    while (!conflict_list.empty() && iter < ITER_LIMIT && ops < OPS_LIMIT) {
        ++iter;

        int idx = (int)(rng() % conflict_list.size());
        int v = conflict_list[idx];
        int c_old = color[v];
        int cur_conf = w[v]; // >0

        auto &cnt_v = cnt[v];
        int best_color = c_old;
        int best_conf = cur_conf;

        for (int c = 0; c < 3; ++c) {
            if (c == c_old) continue;
            int val = cnt_v[c];
            if (val < best_conf) {
                best_conf = val;
                best_color = c;
            }
        }

        if (best_conf < cur_conf) {
            int c_new = best_color;
            int delta_b = cnt_v[c_new] - cnt_v[c_old]; // negative

            const auto &neighbors = adj[v];
            ops += neighbors.size();

            color[v] = c_new;

            for (int u : neighbors) {
                cnt[u][c_old]--;
                cnt[u][c_new]++;

                int cu = color[u];
                if (cu == c_old) {
                    // edge (u,v) was conflicting, now non-conflicting
                    w[u]--;
                    if (w[u] == 0) remove_conflict(u);
                } else if (cu == c_new) {
                    // edge (u,v) becomes conflicting
                    w[u]++;
                    if (w[u] == 1) add_conflict(u);
                }
            }

            w[v] = best_conf;
            if (w[v] == 0) remove_conflict(v);
            // else v stays in conflict_list

            b += delta_b;
        }

        if (ops >= OPS_LIMIT) break;
    }

    // Output colors (1-based)
    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << (color[i] + 1);
    }
    cout << '\n';

    return 0;
}