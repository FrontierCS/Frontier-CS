#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <cassert>

using namespace std;

// Function to issue a query
int ask(int v, const vector<int>& s) {
    if (s.empty()) {
        return 0;
    }
    cout << "? " << s.size() << " " << v;
    for (int node : s) {
        cout << " " << node;
    }
    cout << endl;
    int response;
    cin >> response;
    if (response == -1) exit(0);
    return response;
}

vector<pair<int, int>> edges;

void solve(vector<int> V, int root) {
    if (V.size() <= 1) {
        return;
    }

    vector<int> U;
    for (int node : V) {
        if (node != root) {
            U.push_back(node);
        }
    }
    if (U.empty()) return;

    vector<vector<int>> components;
    if (!U.empty()) {
        vector<int> representatives;
        for (int u : U) {
            bool assigned = false;
            for (size_t i = 0; i < representatives.size(); ++i) {
                if (ask(root, {u, representatives[i]}) == 0) {
                    components[i].push_back(u);
                    assigned = true;
                    break;
                }
            }
            if (!assigned) {
                representatives.push_back(u);
                components.push_back({u});
            }
        }
    }

    for (const auto& comp : components) {
        vector<int> query_set = comp;
        query_set.push_back(root);

        vector<int> path_cand;
        for (int u : comp) {
            if (ask(u, query_set)) {
                path_cand.push_back(u);
            }
        }
        
        int child = -1;
        if (path_cand.empty()) {
            // This case can happen if comp has one element, which is the child
            child = comp[0];
        } else if (path_cand.size() == 1) {
            child = path_cand[0];
        } else {
            int current_ancestor = path_cand[0];
            for (size_t i = 1; i < path_cand.size(); ++i) {
                if (ask(current_ancestor, {root, path_cand[i]}) == 0) {
                    current_ancestor = path_cand[i];
                }
            }
            child = current_ancestor;
        }
        
        edges.push_back({root, child});
        solve(comp, child);
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    cin >> n;

    if (n == 1) {
        cout << "!" << endl;
        return 0;
    }
    if (n == 2) {
        cout << "!" << endl;
        cout << "1 2" << endl;
        return 0;
    }
    
    vector<int> leaves;
    vector<int> all_nodes_except_i(n - 1);
    for (int i = 1; i <= n; ++i) {
        int current = 0;
        for (int j = 1; j <= n; ++j) {
            if (i == j) continue;
            all_nodes_except_i[current++] = j;
        }
        if (ask(i, all_nodes_except_i) == 0) {
            leaves.push_back(i);
        }
    }
    
    int root = leaves[0];
    vector<int> nodes(n);
    iota(nodes.begin(), nodes.end(), 1);
    
    solve(nodes, root);
    
    cout << "!" << endl;
    for (const auto& edge : edges) {
        cout << edge.first << " " << edge.second << endl;
    }

    return 0;
}