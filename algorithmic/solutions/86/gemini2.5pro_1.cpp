#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <map>

// Using a global seems fine for competitive programming setup
int n;
std::vector<std::pair<int, int>> edges;

// Wrapper for the query to the interactor
int ask_query(int u, int v, int w) {
    std::cout << "0 " << u << " " << v << " " << w << std::endl;
    int median;
    std::cin >> median;
    if (median == -1) exit(0); // Should not happen on valid queries
    return median;
}

// Recursively solve for a subtree attached to a parent node
void solve(std::vector<int>& nodes, int parent) {
    if (nodes.empty()) {
        return;
    }
    if (nodes.size() == 1) {
        edges.push_back({parent, nodes[0]});
        return;
    }

    // Find a node in `nodes` that is farthest from `parent`. This node is an
    // endpoint of a diameter of the subtree rooted at `parent`.
    int u_far = nodes[0];
    for (size_t i = 1; i < nodes.size(); ++i) {
        int v = nodes[i];
        int median = ask_query(parent, u_far, v);
        if (median == u_far) {
            u_far = v;
        }
    }

    // Identify nodes on the path from `parent` to `u_far`.
    // Other nodes will be in subtrees attached to this path.
    std::vector<int> path_nodes;
    std::vector<int> other_nodes;
    std::map<int, int> medians; // Stores medians for other_nodes

    for (int node : nodes) {
        if (node != u_far) {
            int median = ask_query(parent, u_far, node);
            medians[node] = median;
            if (median == node) {
                path_nodes.push_back(node);
            } else {
                other_nodes.push_back(node);
            }
        }
    }
    path_nodes.push_back(u_far);
    
    // Sort nodes on the path by their distance from `parent` to find the path structure.
    std::sort(path_nodes.begin(), path_nodes.end(), [&](int u, int v) {
        int median = ask_query(parent, v, u);
        return median == u;
    });

    // Add edges forming the path from parent into the subtree.
    edges.push_back({parent, path_nodes[0]});
    for (size_t i = 0; i < path_nodes.size() - 1; ++i) {
        edges.push_back({path_nodes[i], path_nodes[i+1]});
    }

    // Group the remaining nodes by their attachment point on the newly found path.
    std::map<int, std::vector<int>> groups;
    for (int node : other_nodes) {
        groups[medians[node]].push_back(node);
    }
    
    // Recurse for each group.
    for (auto const& [p, group_nodes] : groups) {
        solve(const_cast<std::vector<int>&>(group_nodes), p);
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::cin >> n;

    // Find two endpoints of a diameter of the tree.
    // First, find a node `a` that is far from an arbitrary node (e.g., node 1).
    int a = 2;
    for (int i = 3; i <= n; ++i) {
        int median = ask_query(1, a, i);
        if (median == a) {
            a = i;
        }
    }
    
    // Then, find a node `b` that is farthest from `a`.
    std::vector<int> candidates;
    for (int i = 1; i <= n; i++) {
        if (i != a) candidates.push_back(i);
    }
    
    int farthest_dist_node = candidates[0];
    for (size_t i = 1; i < candidates.size(); ++i) {
        int median = ask_query(a, farthest_dist_node, candidates[i]);
        if (median == farthest_dist_node) {
            farthest_dist_node = candidates[i];
        }
    }
    int b = farthest_dist_node;

    // Identify nodes on the diameter path and group other nodes by their attachment point.
    std::vector<int> diameter_nodes;
    std::map<int, std::vector<int>> groups;
    std::map<int, int> medians;

    std::vector<int> other_nodes_cand;
    for (int i = 1; i <= n; ++i) {
        if (i != a && i != b) {
            other_nodes_cand.push_back(i);
        }
    }

    for (int node : other_nodes_cand) {
        int median = ask_query(a, b, node);
        medians[node] = median;
        if (median == node) {
            diameter_nodes.push_back(node);
        }
    }
    
    diameter_nodes.push_back(a);
    diameter_nodes.push_back(b);

    // Sort the diameter nodes to determine the path structure.
    std::sort(diameter_nodes.begin(), diameter_nodes.end(), [&](int u, int v){
        int median = ask_query(a, v, u);
        return median == u;
    });

    // Add edges of the diameter path.
    for (size_t i = 0; i < diameter_nodes.size() - 1; ++i) {
        edges.push_back({diameter_nodes[i], diameter_nodes[i+1]});
    }

    // Populate groups for recursive calls.
    for(int node : other_nodes_cand) {
        if (medians[node] != node) {
            groups[medians[node]].push_back(node);
        }
    }
    
    // Solve for subtrees attached to the diameter.
    for (auto const& [p, group_nodes] : groups) {
        solve(const_cast<std::vector<int>&>(group_nodes), p);
    }
    
    // Output the final tree structure.
    std::cout << "1";
    for (const auto& edge : edges) {
        std::cout << " " << edge.first << " " << edge.second;
    }
    std::cout << std::endl;

    return 0;
}