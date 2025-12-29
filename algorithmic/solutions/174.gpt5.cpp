#include <bits/stdc++.h>
using namespace std;

struct Timer {
    chrono::steady_clock::time_point start;
    Timer() { start = chrono::steady_clock::now(); }
    inline long long elapsed_ms() const {
        return chrono::duration_cast<chrono::milliseconds>(chrono::steady_clock::now() - start).count();
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m;
    if (!(cin >> n >> m)) {
        return 0;
    }
    vector<pair<int,int>> edges;
    edges.reserve(m);
    vector<int> deg(n, 0);
    for (int i = 0; i < m; ++i) {
        int u, v; cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        edges.emplace_back(u, v);
        deg[u]++; deg[v]++;
    }
    m = (int)edges.size();
    vector<vector<int>> g(n);
    for (int i = 0; i < n; ++i) g[i].reserve(deg[i]);
    for (auto &e : edges) {
        g[e.first].push_back(e.second);
        g[e.second].push_back(e.first);
    }
    // If no edges, any coloring
    if (m == 0) {
        for (int i = 0; i < n; ++i) {
            if (i) cout << ' ';
            cout << 1;
        }
        cout << '\n';
        return 0;
    }

    mt19937_64 rng(chrono::high_resolution_clock::now().time_since_epoch().count());

    // Initial greedy coloring by descending degree
    vector<int> order(n);
    iota(order.begin(), order.end(), 0);
    // Random tie-breaker in sorting
    stable_sort(order.begin(), order.end(), [&](int a, int b){
        if (deg[a] != deg[b]) return deg[a] > deg[b];
        return (rng() & 1);
    });

    vector<int> color(n, -1);
    array<int,3> colorSize = {0,0,0};
    for (int v : order) {
        array<int,3> used = {0,0,0};
        for (int u : g[v]) {
            if (color[u] != -1) used[color[u]]++;
        }
        int bestC = 0;
        int bestVal = used[0];
        // To encourage balance, include small bias towards smaller colorSize
        for (int c = 1; c < 3; ++c) {
            int val = used[c];
            if (val < bestVal) {
                bestVal = val;
                bestC = c;
            } else if (val == bestVal) {
                // tie-breaker: prefer smaller color class, then random
                if (colorSize[c] < colorSize[bestC]) {
                    bestC = c;
                } else if (colorSize[c] == colorSize[bestC]) {
                    if (rng() & 1) bestC = c;
                }
            }
        }
        color[v] = bestC;
        colorSize[bestC]++;
    }

    // Data structures for local search
    vector<array<int,3>> cnt(n); // neighbor counts per color
    for (int i = 0; i < n; ++i) cnt[i] = {0,0,0};
    for (int v = 0; v < n; ++v) {
        for (int u : g[v]) {
            int cu = color[u];
            cnt[v][cu]++;
        }
    }

    vector<int> conf(n, 0);
    long long b = 0;
    for (int v = 0; v < n; ++v) {
        conf[v] = cnt[v][color[v]];
        b += conf[v];
    }
    b /= 2;

    vector<int> conflict_list;
    conflict_list.reserve(n);
    vector<int> pos(n, -1);
    vector<char> in_conf(n, 0);

    auto add_conflict = [&](int v) {
        if (!in_conf[v] && conf[v] > 0) {
            pos[v] = (int)conflict_list.size();
            conflict_list.push_back(v);
            in_conf[v] = 1;
        }
    };
    auto remove_conflict = [&](int v) {
        if (in_conf[v] && conf[v] == 0) {
            int idx = pos[v];
            int last = conflict_list.back();
            conflict_list[idx] = last;
            pos[last] = idx;
            conflict_list.pop_back();
            pos[v] = -1;
            in_conf[v] = 0;
        }
    };

    for (int v = 0; v < n; ++v) {
        if (conf[v] > 0) add_conflict(v);
    }

    vector<int> best_color = color;
    long long best_b = b;

    // Local search with min-conflicts and occasional random moves
    Timer timer;
    const long long TIME_LIMIT_MS = 1500; // adjust to typical judge constraints
    long long last_improve_step = 0;
    long long steps = 0;

    auto recolor = [&](int v, int newc) {
        int oldc = color[v];
        if (oldc == newc) return;
        int old_conf_v = cnt[v][oldc];
        int new_conf_v = cnt[v][newc];
        b += (long long)new_conf_v - (long long)old_conf_v;

        // update neighbors
        for (int u : g[v]) {
            cnt[u][oldc]--;
            cnt[u][newc]++;
            if (color[u] == oldc) {
                conf[u]--;
                if (conf[u] == 0) remove_conflict(u);
            } else if (color[u] == newc) {
                int prev = conf[u];
                conf[u]++;
                if (prev == 0) add_conflict(u);
            }
        }
        color[v] = newc;
        conf[v] = new_conf_v;
        if (conf[v] == 0) remove_conflict(v);
        else add_conflict(v);
    };

    const int CHECK_INTERVAL = 4096;
    // Noise settings
    int noise_denom = 10; // probability ~1/noise_denom to allow uphill move when no better color
    while (!conflict_list.empty()) {
        steps++;
        if ((steps & (CHECK_INTERVAL - 1)) == 0) {
            if (timer.elapsed_ms() > TIME_LIMIT_MS) break;
            // Adjust noise if stagnating
            if (steps - last_improve_step > 20000) {
                noise_denom = max(3, noise_denom - 1); // increase noise
                last_improve_step = steps; // prevent continuous shrink
            }
        }
        // pick a random conflicting vertex
        int idx = (int)(rng() % conflict_list.size());
        int v = conflict_list[idx];
        int oldc = color[v];
        int cur = cnt[v][oldc];

        // choose best color among all, but prefer one != oldc that strictly improves
        int best_other_c = -1;
        int best_other_val = INT_MAX;
        for (int c = 0; c < 3; ++c) if (c != oldc) {
            int val = cnt[v][c];
            if (val < best_other_val || (val == best_other_val && (rng() & 1))) {
                best_other_val = val;
                best_other_c = c;
            }
        }
        if (best_other_c == -1) continue;

        if (best_other_val < cur) {
            long long prev_b = b;
            recolor(v, best_other_c);
            if (b < prev_b) {
                last_improve_step = steps;
                if (b < best_b) {
                    best_b = b;
                    best_color = color;
                    if (best_b == 0) break;
                }
            }
        } else {
            // optional noise move to escape local minima
            if ((int)(rng() % noise_denom) == 0) {
                long long prev_b = b;
                recolor(v, best_other_c);
                if (b < prev_b) {
                    last_improve_step = steps;
                    if (b < best_b) {
                        best_b = b;
                        best_color = color;
                        if (best_b == 0) break;
                    }
                }
            }
        }
    }

    // Output best found
    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << (best_color[i] + 1);
    }
    cout << '\n';
    return 0;
}