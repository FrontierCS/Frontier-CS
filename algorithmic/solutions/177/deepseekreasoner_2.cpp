#include <iostream>
#include <vector>
#include <algorithm>
#include <random>
#include <numeric>
#include <array>

using namespace std;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    cin >> n >> m;

    vector<vector<int>> adj(n);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    if (m == 0) {
        for (int i = 0; i < n; ++i) {
            cout << 1 << " \n"[i == n-1];
        }
        return 0;
    }

    const int NUM_TRIALS = 5;
    const int MAX_PASSES = 50;

    vector<int> best_colors(n);
    int best_conflicts = m + 1;

    mt19937 rng(random_device{}());

    for (int trial = 0; trial < NUM_TRIALS; ++trial) {
        vector<int> color(n);

        // First trial: greedy coloring by degree
        if (trial == 0) {
            vector<array<int,3>> cnt_nei(n, {0,0,0});
            vector<int> order(n);
            iota(order.begin(), order.end(), 0);
            sort(order.begin(), order.end(),
                 [&](int a, int b) { return adj[a].size() > adj[b].size(); });

            for (int v : order) {
                int best_c = 1;
                int min_conf = cnt_nei[v][0];
                for (int c = 2; c <= 3; ++c) {
                    if (cnt_nei[v][c-1] < min_conf) {
                        min_conf = cnt_nei[v][c-1];
                        best_c = c;
                    }
                }
                color[v] = best_c;
                for (int u : adj[v]) {
                    if (color[u] == 0) {
                        cnt_nei[u][best_c-1]++;
                    }
                }
            }
        } else {
            // Random coloring
            for (int i = 0; i < n; ++i) {
                color[i] = rng() % 3 + 1;
            }
        }

        // cnt[v][c] = number of neighbors of v with color c+1
        vector<array<int,3>> cnt(n, {0,0,0});
        for (int v = 0; v < n; ++v) {
            for (int u : adj[v]) {
                cnt[v][color[u]-1]++;
            }
        }

        vector<int> conflict_count(n);
        int sum_conf = 0;
        for (int v = 0; v < n; ++v) {
            conflict_count[v] = cnt[v][color[v]-1];
            sum_conf += conflict_count[v];
        }
        int total_conflicts = sum_conf / 2;

        int passes = 0;
        bool improved = true;
        while (improved && passes < MAX_PASSES) {
            improved = false;
            ++passes;

            vector<int> order(n);
            iota(order.begin(), order.end(), 0);
            shuffle(order.begin(), order.end(), rng);

            for (int v : order) {
                int c_old = color[v];
                int cur_conf = conflict_count[v];
                int best_c = c_old;
                int best_gain = 0;
                for (int c = 1; c <= 3; ++c) {
                    if (c == c_old) continue;
                    int new_conf = cnt[v][c-1];
                    int gain = cur_conf - new_conf;
                    if (gain > best_gain) {
                        best_gain = gain;
                        best_c = c;
                    }
                }
                if (best_gain > 0) {
                    color[v] = best_c;
                    conflict_count[v] = cnt[v][best_c-1];
                    total_conflicts -= best_gain;

                    for (int u : adj[v]) {
                        cnt[u][c_old-1]--;
                        cnt[u][best_c-1]++;
                        if (color[u] == c_old) {
                            conflict_count[u]--;
                        } else if (color[u] == best_c) {
                            conflict_count[u]++;
                        }
                    }
                    improved = true;
                }
            }
        }

        if (total_conflicts < best_conflicts) {
            best_conflicts = total_conflicts;
            best_colors = color;
            if (best_conflicts == 0) break;
        }
    }

    for (int i = 0; i < n; ++i) {
        cout << best_colors[i] << " \n"[i == n-1];
    }

    return 0;
}