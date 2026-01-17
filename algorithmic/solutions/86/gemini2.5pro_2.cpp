#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <map>

// Function to perform a query
int query(int u, int v, int w) {
    std::cout << "0 " << u << " " << v << " " << w << std::endl;
    int median;
    std::cin >> median;
    if (median == -1) exit(0); // Exit on error signal from interactor
    return median;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;
    
    // Base case for n=3, which can be solved with one query.
    if (n == 3) {
        int m = query(1, 2, 3);
        std::vector<int> others;
        for (int i = 1; i <= 3; ++i) {
            if (i != m) {
                others.push_back(i);
            }
        }
        std::cout << "1 " << m << " " << others[0] << " " << m << " " << others[1] << std::endl;
        return 0;
    }

    // Step 1: Find all nodes on the path between two arbitrary nodes (1 and 2).
    // A node 'i' is on the path between 'u' and 'v' if the median of (u, v, i) is 'i'.
    int u1 = 1, u2 = 2;
    std::vector<int> path_nodes;
    path_nodes.push_back(u1);
    path_nodes.push_back(u2);
    for (int i = 3; i <= n; ++i) {
        if (query(u1, u2, i) == i) {
            path_nodes.push_back(i);
        }
    }

    // Step 2: Sort the path nodes to reconstruct the path.
    // We can sort them by their distance from u1. For two nodes u, v on the path,
    // if median(u1, v, u) is u, then u is closer to u1.
    std::sort(path_nodes.begin(), path_nodes.end(), [&](int u, int v) {
        if (u == v) return false;
        return query(u1, v, u) == u;
    });

    std::vector<std::pair<int, int>> edges;
    for (size_t i = 0; i < path_nodes.size() - 1; ++i) {
        edges.push_back({path_nodes[i], path_nodes[i + 1]});
    }

    // Step 3: Group the remaining nodes by their attachment point to the path.
    // The attachment point of a node 'i' to path P(u,v) is the median of (u, v, i).
    std::map<int, std::vector<int>> groups;
    int path_start = path_nodes.front();
    int path_end = path_nodes.back();
    for (int i = 1; i <= n; ++i) {
        bool on_path = false;
        for (int p_node : path_nodes) {
            if (i == p_node) {
                on_path = true;
                break;
            }
        }
        if (!on_path) {
            int m = query(path_start, path_end, i);
            groups[m].push_back(i);
        }
    }

    // Step 4: Solve for each group, which forms a subtree attached to the path.
    // For a subtree rooted at `r` (with parent `p` on the path), we can find the
    // LCA of any two nodes `u,v` in the subtree by querying `median(p, u, v)`.
    // We build the subtree by adding nodes one by one and finding their parent.
    for (auto const& [r, U_nodes] : groups) {
        if (U_nodes.empty()) continue;
        
        // Find a reference node `p` on the path adjacent to `r`.
        int p = -1;
        for(size_t i = 0; i < path_nodes.size(); ++i) {
            if(path_nodes[i] == r) {
                p = (i > 0) ? path_nodes[i - 1] : path_nodes[i + 1];
                break;
            }
        }
        
        if (U_nodes.size() == 1) {
            edges.push_back({r, U_nodes[0]});
            continue;
        }

        std::vector<int> processed_nodes;
        
        for (int u : U_nodes) {
            int best_parent = r;
            for (int v : processed_nodes) {
                int lca = query(p, u, v);
                // Check if `lca` is an ancestor of `best_parent`. If so, it's not a better parent.
                // If `best_parent` is an ancestor of `lca`, `lca` is a better (deeper) parent.
                if (query(p, lca, best_parent) == best_parent) {
                    best_parent = lca;
                }
            }
            edges.push_back({best_parent, u});
            processed_nodes.push_back(u);
        }
    }

    // Step 5: Output the discovered edges.
    std::cout << "1";
    for (const auto& edge : edges) {
        std::cout << " " << edge.first << " " << edge.second;
    }
    std::cout << std::endl;

    return 0;
}