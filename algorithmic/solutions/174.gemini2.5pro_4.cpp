#include <iostream>
#include <vector>
#include <algorithm>
#include <numeric>

const int MAXN = 1001;
std::vector<int> adj[MAXN];
int color[MAXN];

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n, m;
    std::cin >> n >> m;
    for (int i = 0; i < m; ++i) {
        int u, v;
        std::cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    // --- Greedy coloring based on degree ---
    // Color vertices with higher degree first.
    std::vector<std::pair<int, int>> degrees;
    for (int i = 1; i <= n; ++i) {
        degrees.push_back({-(int)adj[i].size(), i});
    }
    std::sort(degrees.begin(), degrees.end());

    // Initially, all colors are 0 (uncolored).
    for (const auto& p : degrees) {
        int u = p.second;
        int counts[4] = {0}; // counts for colors 1, 2, 3
        for (int v : adj[u]) {
            if (color[v] != 0) { // if neighbor is already colored
                counts[color[v]]++;
            }
        }

        // Assign the color that causes the minimum number of new conflicts.
        // Tie-break by choosing the smallest color index.
        int best_c = 1;
        for (int c = 2; c <= 3; ++c) {
            if (counts[c] < counts[best_c]) {
                best_c = c;
            }
        }
        color[u] = best_c;
    }

    // --- Local Search refinement ---
    // Iteratively try to improve the coloring by making local changes.
    int max_iterations = 100;
    for (int iter = 0; iter < max_iterations; ++iter) {
        bool changed = false;
        for (int u = 1; u <= n; ++u) {
            int counts[4] = {0};
            for (int v : adj[u]) {
                counts[color[v]]++;
            }

            int current_c = color[u];
            int best_c = current_c;
            
            // Find a color for u that results in fewer conflicts with its neighbors.
            // Tie-break by choosing the smallest color index.
            for (int c = 1; c <= 3; ++c) {
                if (counts[c] < counts[best_c]) {
                    best_c = c;
                }
            }

            if (best_c != current_c) {
                color[u] = best_c;
                changed = true;
            }
        }
        // If a full pass over all vertices results in no changes,
        // we have reached a local minimum and can stop.
        if (!changed) {
            break;
        }
    }

    // --- Output ---
    for (int i = 1; i <= n; ++i) {
        std::cout << color[i] << (i == n ? "" : " ");
    }
    std::cout << std::endl;

    return 0;
}