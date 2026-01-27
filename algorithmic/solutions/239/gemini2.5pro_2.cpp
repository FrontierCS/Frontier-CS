#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <tuple>

// A vector to store the added edges in the format {u, c, v}
// representing adding an edge u -> v via intermediate node c.
std::vector<std::tuple<int, int, int>> added_edges;

// A boolean matrix to keep track of added edges to avoid duplicates.
// n <= 2^12 = 4096. A static array is feasible.
bool has_edge[4100][4100] = {false};

// Function to add an edge if it doesn't already exist.
void add_edge_if_new(int u, int c, int v) {
    if (u >= v) return;
    if (!has_edge[u][v]) {
        added_edges.emplace_back(u, c, v);
        has_edge[u][v] = true;
    }
}

// Recursive function to generate the necessary edges.
void solve(int l, int r) {
    // Base case: If the range is too small, initial edges suffice.
    if (r - l <= 1) {
        return;
    }

    // Divide the range into two halves.
    int m = l + (r - l) / 2;

    // Recursively solve for the two halves.
    solve(l, m);
    solve(m, r);

    // Combine step: Add edges to connect vertices from the left half to the right half.
    // We establish paths through the midpoint `m`.

    // For each vertex `i` in the left partition [l, m-1], we add an edge `i -> m`.
    // The intermediate vertex `c` for the path `i -> c -> m` is the midpoint
    // of the sub-range `[l, m]`, which is `l + (m - l) / 2`.
    // The recursive calls ensure that edges `i -> c` and `c -> m` exist or can be formed.
    int c1 = l + (m - l) / 2;
    for (int i = l; i < m; ++i) {
        add_edge_if_new(i, c1, m);
    }

    // Similarly, for each vertex `j` in the right partition [m+1, r], we add an edge `m -> j`.
    // The intermediate vertex `c` for the path `m -> c -> j` is the midpoint
    // of the sub-range `[m, r]`, which is `m + (r - m) / 2`.
    int c2 = m + (r - m) / 2;
    for (int j = m + 1; j <= r; ++j) {
        add_edge_if_new(m, c2, j);
    }
}

int main() {
    // Fast I/O
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;

    if (n > 0) {
        // Initialize `has_edge` for the initial graph edges v -> v+1.
        for (int i = 0; i < n; ++i) {
            has_edge[i][i + 1] = true;
        }
        
        solve(0, n);
    }

    // Output the results
    std::cout << added_edges.size() << "\n";
    for (const auto& edge : added_edges) {
        std::cout << std::get<0>(edge) << " " << std::get<1>(edge) << " " << std::get<2>(edge) << "\n";
    }

    return 0;
}