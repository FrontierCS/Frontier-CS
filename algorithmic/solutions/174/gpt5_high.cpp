#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) return 0;
    vector<vector<int>> adj(n);
    adj.reserve(n);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    vector<int> deg(n);
    for (int i = 0; i < n; ++i) deg[i] = (int)adj[i].size();

    mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());
    auto rand01 = [&]() -> double {
        return std::uniform_real_distribution<double>(0.0, 1.0)(rng);
    };
    auto randint = [&](int l, int r) -> int {
        return std::uniform_int_distribution<int>(l, r)(rng);
    };

    // Greedy initialization by descending degree with random tie-breaking
    vector<int> col(n, -1);
    {
        vector<int> order(n);
        iota(order.begin(), order.end(), 0);
        sort(order.begin(), order.end(), [&](int a, int b){ return deg[a] > deg[b]; });
        array<int, 3> cntC;
        for (int u : order) {
            cntC = {0,0,0};
            for (int v : adj[u]) {
                if (col[v] != -1) cntC[col[v]]++;
            }
            int minVal = min(cntC[0], min(cntC[1], cntC[2]));
            int choices[3], cc = 0;
            for (int c = 0; c < 3; ++c) if (cntC[c] == minVal) choices[cc++] = c;
            col[u] = choices[randint(0, cc-1)];
        }
    }

    // Prepare counts of neighbor colors
    vector<array<int,3>> cnt(n);
    for (int i = 0; i < n; ++i) cnt[i] = {0,0,0};
    for (int u = 0; u < n; ++u) {
        for (int v : adj[u]) {
            cnt[u][col[v]]++;
        }
    }

    long long b = 0;
    for (int i = 0; i < n; ++i) b += cnt[i][col[i]];
    b /= 2;

    // Conflict list maintenance
    vector<int> confList;
    confList.reserve(n);
    vector<int> pos(n, -1);
    auto in_conflict = [&](int v) -> bool {
        return cnt[v][col[v]] > 0;
    };
    auto add_conf = [&](int v) {
        if (pos[v] != -1) return;
        pos[v] = (int)confList.size();
        confList.push_back(v);
    };
    auto remove_conf = [&](int v) {
        if (pos[v] == -1) return;
        int idx = pos[v];
        int last = confList.back();
        confList[idx] = last;
        pos[last] = idx;
        confList.pop_back();
        pos[v] = -1;
    };
    auto update_conf_status = [&](int v) {
        if (in_conflict(v)) add_conf(v);
        else remove_conf(v);
    };

    for (int i = 0; i < n; ++i) if (in_conflict(i)) add_conf(i);

    auto best_color_and_delta = [&](int i) -> pair<int,int> {
        int cur = col[i];
        int c1 = (cur + 1) % 3;
        int c2 = (cur + 2) % 3;
        int d1 = cnt[i][c1] - cnt[i][cur];
        int d2 = cnt[i][c2] - cnt[i][cur];
        if (d1 < d2) return {c1, d1};
        if (d2 < d1) return {c2, d2};
        // tie-break randomly
        if (rand01() < 0.5) return {c1, d1};
        else return {c2, d2};
    };

    auto apply_move = [&](int i, int newc, int delta) {
        int oldc = col[i];
        if (oldc == newc) return;
        // update neighbors
        for (int j : adj[i]) {
            cnt[j][oldc]--;
            cnt[j][newc]++;
            if (col[j] == oldc || col[j] == newc) {
                update_conf_status(j);
            }
        }
        b += delta;
        col[i] = newc;
        update_conf_status(i);
    };

    auto start = chrono::steady_clock::now();
    auto elapsed_sec = [&]() -> double {
        return chrono::duration<double>(chrono::steady_clock::now() - start).count();
    };
    double TIME_LIMIT = 0.95; // seconds, conservative

    // Initial hill climbing passes over conflicting vertices
    {
        bool improved = true;
        int passes = 0;
        while (improved && elapsed_sec() < TIME_LIMIT * 0.4) { // allocate ~40% time
            improved = false;
            vector<int> nodes = confList; // snapshot
            shuffle(nodes.begin(), nodes.end(), rng);
            for (int i : nodes) {
                if (pos[i] == -1) continue; // resolved already
                auto [nc, d] = best_color_and_delta(i);
                if (d < 0) {
                    apply_move(i, nc, d);
                    improved = true;
                    if (b == 0) break;
                }
            }
            passes++;
            if (b == 0) break;
        }
    }

    // Simulated annealing on conflicts
    if (b > 0) {
        double avg_deg = n ? (2.0 * (double)m / (double)n) : 0.0;
        double T0 = max(0.5, avg_deg * 0.5);
        double Tend = 0.01;
        // allocate remaining time
        double t0 = elapsed_sec();
        double remaining = max(0.0, TIME_LIMIT - t0);
        if (remaining > 0.0) {
            long long iter = 0;
            while (elapsed_sec() < TIME_LIMIT) {
                int i;
                if (!confList.empty()) {
                    i = confList[randint(0, (int)confList.size()-1)];
                } else {
                    // already perfect
                    break;
                }
                auto [nc, d] = best_color_and_delta(i);
                if (d <= 0) {
                    apply_move(i, nc, d);
                } else {
                    double frac = (elapsed_sec() - t0) / max(remaining, 1e-9);
                    if (frac < 0.0) frac = 0.0;
                    if (frac > 1.0) frac = 1.0;
                    double T = T0 * pow(Tend / T0, frac); // exponential cooling
                    double prob = exp(-(double)d / max(T, 1e-9));
                    if (rand01() < prob) {
                        apply_move(i, nc, d);
                    }
                }
                // occasional random perturbation
                if ((iter & 1023) == 0) {
                    if (elapsed_sec() >= TIME_LIMIT) break;
                    if (rand01() < 0.05 && n > 0) {
                        int v = randint(0, n - 1);
                        int cur = col[v];
                        int newc = randint(0, 1);
                        if (newc >= cur) newc++;
                        int delta = cnt[v][newc] - cnt[v][cur];
                        apply_move(v, newc, delta);
                    }
                }
                ++iter;
                if (b == 0) break;
            }
        }
    }

    // Final single pass hill-climb if time permits
    if (b > 0 && elapsed_sec() < TIME_LIMIT * 0.98) {
        vector<int> nodes = confList;
        shuffle(nodes.begin(), nodes.end(), rng);
        for (int i : nodes) {
            if (pos[i] == -1) continue;
            auto [nc, d] = best_color_and_delta(i);
            if (d < 0) {
                apply_move(i, nc, d);
                if (b == 0) break;
            }
            if (elapsed_sec() >= TIME_LIMIT) break;
        }
    }

    // Output colors in 1..3
    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << (col[i] + 1);
    }
    cout << '\n';

    return 0;
}