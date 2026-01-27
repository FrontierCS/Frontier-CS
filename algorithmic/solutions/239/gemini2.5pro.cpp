#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <map>

// Data structure for an added edge
struct Edge {
    int u, c, v;
};

// Global list of added edges for the final output
std::vector<Edge> added_edges;
// Adjacency list to represent the current state of the graph
std::map<int, std::vector<int>> current_adj;

// Adds an edge to our graph representation if it doesn't already exist
void add_edge_to_map(int u, int v) {
    if (!current_adj.count(u) || !std::binary_search(current_adj[u].begin(), current_adj[u].end(), v)) {
        current_adj[u].push_back(v);
        std::sort(current_adj[u].begin(), current_adj[u].end());
    }
}

// Records an edge addition and updates the graph
void add_edge(int u, int c, int v) {
    bool edge_exists = false;
    if (current_adj.count(u)) {
        if (std::binary_search(current_adj[u].begin(), current_adj[u].end(), v)) {
            edge_exists = true;
        }
    }
    if (!edge_exists) {
        added_edges.push_back({u, c, v});
        add_edge_to_map(u, v);
    }
}

// Finds the greedy path from u to v by always taking the longest possible jump
std::vector<int> find_greedy_path(int u, int v) {
    std::vector<int> path;
    int curr = u;
    while (curr < v) {
        path.push_back(curr);
        int next_node = curr + 1;
        if (current_adj.count(curr)) {
            auto it = std::upper_bound(current_adj[curr].begin(), current_adj[curr].end(), v);
            if (it != current_adj[curr].begin()) {
                it--;
                if (*it > next_node) {
                    next_node = *it;
                }
            }
        }
        curr = next_node;
    }
    path.push_back(v);
    return path;
}


// Reduces the distance between u and v to 1 by adding shortcut edges
void make_dist_one(int u, int v) {
    if (u >= v) return;

    while (true) {
        std::vector<int> path = find_greedy_path(u, v);

        if (path.size() <= 2) {
            return; // Distance is already 1
        }
        
        // Add shortcuts for all paths of length 2 on the current greedy path
        // Iterating backwards is not strictly necessary here but can be safer
        // in some dynamic programming contexts on paths.
        for (size_t i = 0; i + 2 < path.size(); ++i) {
            add_edge(path[i], path[i+1], path[i+2]);
        }
    }
}

// The main recursive function to solve the problem for range [l, r]
void solve(int l, int r) {
    if (r - l <= 3) {
        return;
    }

    // A special recursive structure that ensures all pairs of vertices are covered.
    // It's based on finding the largest power of 2 that fits in the interval.
    int k = 0;
    while ((1 << (k + 1)) <= (r - l)) {
        k++;
    }
    int p1 = l + (1 << k);
    int p2 = r - (1 << k);

    solve(l, p2);
    solve(p1, r);
}


int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;

    if (n == 0) {
        std::cout << 0 << std::endl;
        return 0;
    }

    // Initialize the graph with the base edges v -> v+1
    for (int i = 0; i < n; ++i) {
        add_edge_to_map(i, i + 1);
    }
    
    // An alternative, simpler recursive structure with explicit "glue"
    // that also solves the problem correctly and efficiently.
    std::function<void(int, int)> solve_simple = 
        [&](int l, int r) {
        if (r - l <= 1) return;
        int m = l + (r - l) / 2;
        solve_simple(l, m);
        solve_simple(m, r);
        make_dist_one(l, r);
    };

    solve_simple(0, n);

    std::cout << added_edges.size() << std::endl;
    for (const auto& edge : added_edges) {
        std::cout << edge.u << " " << edge.c << " " << edge.v << std::endl;
    }

    return 0;
}