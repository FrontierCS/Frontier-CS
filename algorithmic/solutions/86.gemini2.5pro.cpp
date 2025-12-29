#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <map>

// Function to ask a query
int ask_query(int u, int v, int w) {
    std::cout << "0 " << u << " " << v << " " << w << std::endl;
    int median;
    std::cin >> median;
    return median;
}

// Global storage for edges
std::vector<std::pair<int, int>> found_edges;

// Recursive function to solve for a subtree
void solve(int p, std::vector<int>& U) {
    if (U.empty()) {
        return;
    }

    // 1. Pick a pivot
    int u0 = U.back();
    U.pop_back();

    // 2. Partition rest of U into descendants of u0 and the rest
    std::vector<int> D, R;
    if (!U.empty()){
        for (int v : U) {
            int m = ask_query(p, u0, v);
            if (m == u0) {
                D.push_back(v);
            } else {
                R.push_back(v);
            }
        }
    }
    
    // 3. Find parent of u0 among candidates R union {p}
    std::vector<int> C = R;
    C.push_back(p);
    
    std::vector<int> ancestors;
    for (int v : C) {
        if (v == p) {
            ancestors.push_back(p);
            continue;
        }
        // with p as root, median(p, u0, v) is lca_p(u0, v)
        // v is an ancestor of u0 iff lca_p(u0, v) == v
        int m = ask_query(p, u0, v);
        if (m == v) {
            ancestors.push_back(v);
        }
    }
    
    // Find the deepest ancestor, which is the parent
    int parent_of_u0 = ancestors[0];
    for (size_t i = 1; i < ancestors.size(); ++i) {
        int v = ancestors[i];
        // To find which of parent_of_u0 and v is deeper,
        // we find their lca w.r.t p. The one that is not lca is deeper.
        int m = ask_query(p, parent_of_u0, v);
        if (m == parent_of_u0) {
            parent_of_u0 = v;
        }
    }
    
    found_edges.push_back({parent_of_u0, u0});

    // 4. Recurse
    solve(u0, D);
    solve(p, R);
}

// Function to report the answer
void report_answer() {
    std::cout << "1";
    for (const auto& edge : found_edges) {
        std::cout << " " << edge.first << " " << edge.second;
    }
    std::cout << std::endl;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;

    if (n == 3) {
        int m = ask_query(1, 2, 3);
        if (m == 1) found_edges = {{1, 2}, {1, 3}};
        else if (m == 2) found_edges = {{2, 1}, {2, 3}};
        else found_edges = {{3, 1}, {3, 2}};
        report_answer();
        return 0;
    }

    // 1. Find an initial path between two arbitrary nodes, e.g., 1 and 2
    std::vector<int> path_nodes;
    path_nodes.push_back(1);
    path_nodes.push_back(2);
    
    std::vector<int> other_nodes;
    for (int i = 3; i <= n; ++i) {
        int m = ask_query(1, 2, i);
        if (m == i) {
            path_nodes.push_back(i);
        } else {
            other_nodes.push_back(i);
        }
    }

    // 2. Find endpoints of the path
    int u_end = path_nodes[0], v_end = path_nodes[1];
    for (size_t i = 2; i < path_nodes.size(); ++i) {
        int w = path_nodes[i];
        int m = ask_query(u_end, v_end, w);
        if (m == u_end) { // v--u--w, new endpoints are v and w
            v_end = w;
        } else if (m == v_end) { // u--v--w, new endpoints are u and w
            u_end = w;
        }
    }
    int e1 = u_end, e2 = v_end;
    
    // 3. Sort path nodes based on distance from e1
    std::sort(path_nodes.begin(), path_nodes.end(), [&](int u, int v) {
        if (u == e1) return true;
        if (v == e1) return false;
        // For any other pairs, u comes before v if u is on path e1-v
        return ask_query(e1, u, v) == u;
    });

    // 4. Add path edges
    for (size_t i = 0; i < path_nodes.size() - 1; ++i) {
        found_edges.push_back({path_nodes[i], path_nodes[i+1]});
    }

    // 5. Group other nodes based on their attachment point to the path
    std::map<int, std::vector<int>> groups;
    for (int node : other_nodes) {
        int m = ask_query(e1, e2, node);
        groups[m].push_back(node);
    }

    // 6. Solve for each group
    for (auto const& [p, U_val] : groups) {
        std::vector<int> U_copy = U_val;
        solve(p, U_copy);
    }
    
    report_answer();

    return 0;
}