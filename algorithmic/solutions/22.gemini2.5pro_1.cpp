#include <iostream>
#include <vector>
#include <algorithm>
#include <map>
#include <queue>

using namespace std;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    cin >> n;

    vector<vector<int>> adj(n + 1);
    vector<pair<int, int>> tree_edges;
    for (int i = 2; i <= n; ++i) {
        int p;
        cin >> p;
        adj[p].push_back(i);
        adj[i].push_back(p);
        tree_edges.push_back({p, i});
    }

    vector<int> leaves;
    for (int i = 2; i <= n; ++i) {
        if (adj[i].size() == 1) {
            leaves.push_back(i);
        }
    }

    vector<pair<int, int>> all_edges = tree_edges;
    int k = leaves.size();
    if (k > 1) {
        for (int i = 0; i < k; ++i) {
            all_edges.push_back({leaves[i], leaves[(i + 1) % k]});
        }
    }

    for(auto& p : all_edges) {
        if (p.first > p.second) {
            swap(p.first, p.second);
        }
    }
    sort(all_edges.begin(), all_edges.end());
    all_edges.erase(unique(all_edges.begin(), all_edges.end()), all_edges.end());
    
    int num_edges = all_edges.size();
    int K = n + num_edges;

    cout << K << endl;

    vector<vector<int>> bags(K + 1);
    for (int i = 1; i <= n; ++i) {
        bags[i] = {i};
    }

    map<pair<int, int>, int> edge_to_id;
    int current_id = n + 1;
    for (const auto& edge : all_edges) {
        edge_to_id[edge] = current_id;
        bags[current_id] = {edge.first, edge.second};
        current_id++;
    }

    for (int i = 1; i <= K; ++i) {
        cout << bags[i].size();
        for (int v : bags[i]) {
            cout << " " << v;
        }
        cout << endl;
    }

    vector<vector<int>> incidence_adj(K + 1);
    for (const auto& edge : all_edges) {
        int u = edge.first;
        int v = edge.second;
        int edge_id = edge_to_id[edge];
        incidence_adj[u].push_back(edge_id);
        incidence_adj[edge_id].push_back(u);
        incidence_adj[v].push_back(edge_id);
        incidence_adj[edge_id].push_back(v);
    }
    
    vector<pair<int, int>> new_tree_edges;
    if (K > 0) {
        vector<bool> visited(K + 1, false);
        queue<int> q;

        q.push(1);
        visited[1] = true;

        while (!q.empty()) {
            int u = q.front();
            q.pop();

            for (int v : incidence_adj[u]) {
                if (!visited[v]) {
                    visited[v] = true;
                    new_tree_edges.push_back({u, v});
                    q.push(v);
                }
            }
        }
    }

    for (const auto& edge : new_tree_edges) {
        cout << edge.first << " " << edge.second << endl;
    }

    return 0;
}