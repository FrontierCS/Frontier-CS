#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <map>

int ask_query(int u, int v, int w) {
    std::cout << "0 " << u << " " << v << " " << w << std::endl;
    int median;
    std::cin >> median;
    return median;
}

std::vector<std::pair<int, int>> edges;

void solve(std::vector<int> nodes, int parent) {
    if (nodes.empty()) {
        return;
    }
    if (nodes.size() == 1) {
        edges.push_back({nodes[0], parent});
        return;
    }
    
    int u1 = parent;
    int u2 = nodes[0];

    // Find node in `nodes` farthest from `u1` (parent)
    int farthest = u2;
    for (size_t i = 1; i < nodes.size(); ++i) {
        int m = ask_query(u1, farthest, nodes[i]);
        if (m == farthest) {
            farthest = nodes[i];
        }
    }
    u2 = farthest;
    
    std::vector<int> path;
    std::map<int, std::vector<int>> buckets;

    for (int node : nodes) {
        if (node == u2) continue;
        int m = ask_query(u1, u2, node);
        if (m != node) {
            buckets[m].push_back(node);
        } else {
            path.push_back(node);
        }
    }
    
    path.push_back(u2);
    
    std::sort(path.begin(), path.end(), [&](int p1, int p2) {
        if (p1 == u1) return true;
        if (p2 == u1) return false;
        return ask_query(u1, p1, p2) == p1;
    });

    int last_on_path = u1;
    for (int node_on_path : path) {
        edges.push_back({last_on_path, node_on_path});
        if (buckets.count(node_on_path)) {
            solve(buckets[node_on_path], node_on_path);
        }
        last_on_path = node_on_path;
    }
}


int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    
    int n;
    std::cin >> n;
    
    // Find one endpoint of a diameter by finding the node farthest from node 1.
    int leaf1 = 2;
    for (int i = 3; i <= n; ++i) {
        int m = ask_query(1, leaf1, i);
        if (m == leaf1) {
            leaf1 = i;
        }
    }

    // Find the other endpoint by finding the node farthest from leaf1.
    int leaf2 = 1;
    if (leaf1 == 1) leaf2 = 2;
    for (int i = 1; i <= n; ++i) {
        if (i == leaf1 || i == leaf2) continue;
        int m = ask_query(leaf1, leaf2, i);
        if (m == leaf2) {
            leaf2 = i;
        }
    }
    
    std::vector<int> path;
    std::map<int, std::vector<int>> subtrees;
    
    // Identify nodes on the diameter and partition the rest into subtrees.
    for (int i = 1; i <= n; ++i) {
        if (i == leaf1 || i == leaf2) continue;
        int m = ask_query(leaf1, leaf2, i);
        if (m == i) {
            path.push_back(i);
        } else {
            subtrees[m].push_back(i);
        }
    }
    
    path.push_back(leaf1);
    path.push_back(leaf2);
    
    // Sort the path nodes by their distance from leaf1.
    std::sort(path.begin(), path.end(), [&](int a, int b){
        if (a == leaf1) return true;
        if (b == leaf1) return false;
        return ask_query(leaf1, a, b) == a;
    });

    // Add edges for the main path.
    for (size_t i = 0; i < path.size() - 1; ++i) {
        edges.push_back({path[i], path[i+1]});
    }
    
    // Recursively solve for each subtree.
    for (auto const& [root, nodes] : subtrees) {
        solve(nodes, root);
    }

    std::cout << "1";
    for (const auto& edge : edges) {
        std::cout << " " << edge.first << " " << edge.second;
    }
    std::cout << std::endl;

    return 0;
}