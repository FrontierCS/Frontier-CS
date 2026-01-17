#include <iostream>
#include <vector>
#include <algorithm>
#include <random>
#include <array>

using namespace std;

const int RUNS = 5;
const int MAX_PASSES = 20;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    cin >> n >> m;

    vector<vector<int>> adj(n + 1);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    // Random number generator
    random_device rd;
    mt19937 gen(rd());
    uniform_int_distribution<int> col_dist(1, 3);

    vector<int> best_coloring(n + 1);
    int best_conflicts = m + 1; // initialize with a value larger than possible

    for (int run = 0; run < RUNS; ++run) {
        // Random initial coloring
        vector<int> color(n + 1);
        for (int v = 1; v <= n; ++v) {
            color[v] = col_dist(gen);
        }

        // cnt[v][c] = number of neighbors of v with color c (c in 0..2)
        vector<array<int, 3>> cnt(n + 1);
        for (int v = 1; v <= n; ++v) {
            cnt[v].fill(0);
        }
        for (int v = 1; v <= n; ++v) {
            for (int u : adj[v]) {
                cnt[v][color[u] - 1]++;
            }
        }

        // Iterative improvement
        bool improved = true;
        int passes = 0;
        while (improved && passes < MAX_PASSES) {
            improved = false;
            vector<int> order(n);
            iota(order.begin(), order.end(), 1);
            shuffle(order.begin(), order.end(), gen);

            for (int v : order) {
                int cur_c = color[v];
                int cur_conf = cnt[v][cur_c - 1];
                int best_c = cur_c;
                int best_conf = cur_conf;

                // Check the other two colors
                for (int c = 1; c <= 3; ++c) {
                    if (c == cur_c) continue;
                    int conf = cnt[v][c - 1];
                    if (conf < best_conf) {
                        best_conf = conf;
                        best_c = c;
                    }
                }

                if (best_c != cur_c) {
                    // Update neighbor counts
                    for (int u : adj[v]) {
                        cnt[u][cur_c - 1]--;
                        cnt[u][best_c - 1]++;
                    }
                    color[v] = best_c;
                    improved = true;
                }
            }
            ++passes;
        }

        // Compute number of conflicting edges for this run
        int conflicts = 0;
        for (int v = 1; v <= n; ++v) {
            for (int u : adj[v]) {
                if (u > v && color[u] == color[v]) {
                    ++conflicts;
                }
            }
        }

        if (conflicts < best_conflicts) {
            best_conflicts = conflicts;
            best_coloring = color;
        }

        // Early exit if perfect coloring found
        if (best_conflicts == 0) break;
    }

    // Output the best coloring found
    for (int v = 1; v <= n; ++v) {
        cout << best_coloring[v] << (v == n ? '\n' : ' ');
    }

    return 0;
}