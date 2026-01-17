#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <map>

using namespace std;

// This function sends a query to the judge.
bool ask(int v, const vector<int>& s) {
    if (s.empty()) {
        return false;
    }
    cout << "? " << s.size() << " " << v;
    for (int node : s) {
        cout << " " << node;
    }
    cout << endl;
    
    int result;
    cin >> result;
    if (result == -1) exit(0);
    
    return (result == 1);
}

// This helper function checks if a vertex v is on the path between u1 and u2.
bool is_on_path(int v, int u1, int u2) {
    if (v == u1 || v == u2) return true;
    return ask(v, {u1, u2});
}

// Stores the final edges of the tree.
vector<pair<int, int>> final_edges;

// Recursive function to solve the problem for a given component `nodes`.
void solve(const vector<int>& nodes) {
    if (nodes.size() <= 1) {
        return;
    }
    if (nodes.size() == 2) {
        final_edges.push_back({nodes[0], nodes[1]});
        return;
    }

    // Find leaves of the induced subgraph on `nodes`.
    vector<int> leaves;
    for (int u : nodes) {
        vector<int> s;
        for (int v : nodes) {
            if (u == v) continue;
            s.push_back(v);
        }
        if (!ask(u, s)) {
            leaves.push_back(u);
        }
    }
    
    // If the component is a path, its leaves in the induced subgraph might be internal nodes
    // in the full tree. In this case, we find the endpoints of the path.
    if (leaves.size() < 2) {
        int u_endpoint = nodes[0];
        int v_endpoint = -1;
        int max_dist = 0;
        
        for (int v : nodes) {
            if (u_endpoint == v) continue;
            int dist = 0;
            vector<int> path_nodes;
            for(int w : nodes) {
                if(is_on_path(w, u_endpoint, v)) {
                    path_nodes.push_back(w);
                }
            }
            if ((int)path_nodes.size() > max_dist) {
                max_dist = path_nodes.size();
                v_endpoint = v;
            }
        }
        leaves = {u_endpoint, v_endpoint};
    }

    int l1 = leaves[0];
    int l2 = leaves.back();

    // Identify all nodes on the path between l1 and l2.
    vector<int> path;
    for (int u : nodes) {
        if (is_on_path(u, l1, l2)) {
            path.push_back(u);
        }
    }

    // Sort the path nodes based on their distance from l1.
    sort(path.begin(), path.end(), [&](int u, int v) {
        return is_on_path(u, l1, v);
    });

    // Add edges of the path.
    for (size_t i = 0; i < path.size() - 1; ++i) {
        final_edges.push_back({path[i], path[i+1]});
    }

    // Group remaining nodes by their attachment point on the path.
    map<int, vector<int>> subproblems;
    for(int p_node : path) {
        subproblems[p_node].push_back(p_node);
    }
    
    vector<bool> on_path_flag(1001, false);
    for(int u : path) on_path_flag[u] = true;

    for (int u : nodes) {
        if (!on_path_flag[u]) {
            int l = 0, r = path.size() - 1;
            int attach_point = -1;
            while (l <= r) {
                if (l == r) {
                    attach_point = path[l];
                    break;
                }
                int m = l + (r - l) / 2;
                if (is_on_path(path[m], u, l2)) {
                    attach_point = path[m];
                    l = m;
                } else {
                    attach_point = path[m+1];
                    r = m;
                }
                if (l==r-1) { // Base case for 2 elements
                    if (is_on_path(path[l], u, path[r])) {
                         attach_point = path[r];
                    } else {
                         attach_point = path[l];
                    }
                    break;
                }
            }
            subproblems[attach_point].push_back(u);
        }
    }
    
    // Recurse on each subproblem.
    for(auto const& [p_node, component_nodes] : subproblems) {
        if(component_nodes.size() > 1) {
            solve(component_nodes);
        }
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    cin >> n;

    vector<int> all_nodes(n);
    iota(all_nodes.begin(), all_nodes.end(), 1);

    solve(all_nodes);

    cout << "!" << endl;
    for (const auto& edge : final_edges) {
        cout << edge.first << " " << edge.second << endl;
    }

    return 0;
}