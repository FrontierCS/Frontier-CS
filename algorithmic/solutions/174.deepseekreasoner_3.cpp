#include <iostream>
#include <vector>
#include <algorithm>
#include <numeric>
#include <random>
#include <chrono>
#include <tuple>

using namespace std;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(nullptr);
    cout.tie(nullptr);

    int n, m;
    cin >> n >> m;

    // Special case: no edges
    if (m == 0) {
        for (int i = 0; i < n; ++i) {
            cout << 1 << (i+1 == n ? "\n" : " ");
        }
        return 0;
    }

    vector<vector<int>> adj(n);
    vector<int> deg(n, 0);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        adj[u].push_back(v);
        adj[v].push_back(u);
        ++deg[u];
        ++deg[v];
    }

    // Random number generator
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

    // Best solution found
    vector<int> best_color(n);
    int best_conflicts = m + 1; // larger than possible

    // Try several initializations: 0 = greedy, 1..4 = random
    const int NUM_TRIALS = 5;
    for (int trial = 0; trial < NUM_TRIALS; ++trial) {
        vector<int> color(n);
        if (trial == 0) {
            // Greedy initialization by degree descending
            vector<int> order(n);
            iota(order.begin(), order.end(), 0);
            sort(order.begin(), order.end(), [&](int a, int b) { return deg[a] > deg[b]; });
            vector<int> tmp_color(n, -1);
            for (int v : order) {
                vector<int> count(3, 0);
                for (int u : adj[v]) {
                    if (tmp_color[u] != -1) {
                        ++count[tmp_color[u]];
                    }
                }
                int best = min_element(count.begin(), count.end()) - count.begin();
                tmp_color[v] = best;
            }
            color = tmp_color;
        } else {
            // Random initialization
            uniform_int_distribution<int> col_dist(0, 2);
            for (int i = 0; i < n; ++i) {
                color[i] = col_dist(rng);
            }
        }

        // cnt[i][c] = number of neighbors of i with color c
        vector<vector<int>> cnt(n, vector<int>(3, 0));
        for (int i = 0; i < n; ++i) {
            for (int j : adj[i]) {
                if (i < j) { // each edge once
                    cnt[i][color[j]]++;
                    cnt[j][color[i]]++;
                }
            }
        }

        // Compute total conflicting edges
        int total_conflicts = 0;
        for (int i = 0; i < n; ++i) {
            total_conflicts += cnt[i][color[i]];
        }
        total_conflicts /= 2;

        // Local search
        bool improved = true;
        int passes = 0;
        while (improved && passes < 200) {
            improved = false;
            vector<int> order(n);
            iota(order.begin(), order.end(), 0);
            shuffle(order.begin(), order.end(), rng);
            for (int i : order) {
                int old_c = color[i];
                int old_conf = cnt[i][old_c];
                int best_c = old_c;
                int best_conf = old_conf;
                for (int c = 0; c < 3; ++c) {
                    if (c == old_c) continue;
                    if (cnt[i][c] < best_conf) {
                        best_conf = cnt[i][c];
                        best_c = c;
                    }
                }
                if (best_c != old_c) {
                    // Update total conflicts
                    total_conflicts += (best_conf - old_conf);
                    // Update neighbor counts
                    for (int j : adj[i]) {
                        cnt[j][old_c]--;
                        cnt[j][best_c]++;
                    }
                    color[i] = best_c;
                    improved = true;
                }
            }
            ++passes;
            if (total_conflicts == 0) break; // perfect coloring found
        }

        if (total_conflicts < best_conflicts) {
            best_conflicts = total_conflicts;
            best_color = color;
        }
        if (best_conflicts == 0) break;
    }

    // Output colors (1-indexed)
    for (int i = 0; i < n; ++i) {
        cout << best_color[i] + 1 << (i+1 == n ? "\n" : " ");
    }

    return 0;
}