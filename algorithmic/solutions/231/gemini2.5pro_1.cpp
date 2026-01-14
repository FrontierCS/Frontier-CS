#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <set>
#include <map>
#include <tuple>

using namespace std;

const int N_MAX = 1000;
vector<int> adj[N_MAX + 1];
int g[N_MAX + 1];
bool visited[N_MAX + 1];
vector<int> topo_order;
int topo_idx[N_MAX + 1];

void dfs_topo(int u) {
    visited[u] = true;
    for (int v : adj[u]) {
        if (!visited[v]) {
            dfs_topo(v);
        }
    }
    topo_order.push_back(u);
}

void compute_grundy(int n) {
    topo_order.clear();
    fill(visited + 1, visited + n + 1, false);
    for (int i = 1; i <= n; ++i) {
        if (!visited[i]) {
            dfs_topo(i);
        }
    }
    reverse(topo_order.begin(), topo_order.end());
    
    for(int i = 0; i < n; ++i) {
        topo_idx[topo_order[i]] = i;
    }

    // Process in reverse topological order
    for (int i = n - 1; i >= 0; --i) {
        int u = topo_order[i];
        set<int> seen_grundy_values;
        for (int v : adj[u]) {
            seen_grundy_values.insert(g[v]);
        }
        int current_g = 0;
        while (seen_grundy_values.count(current_g)) {
            current_g++;
        }
        g[u] = current_g;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n, m, t;
    cin >> n >> m >> t;

    vector<pair<int, int>> initial_edges;
    int out_degree[N_MAX + 1] = {0};
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        initial_edges.push_back({u, v});
        out_degree[u]++;
    }

    const int K_CONTROLLED = 64;
    vector<pair<int, int>> out_degrees_sorted;
    for (int i = 1; i <= n; ++i) {
        out_degrees_sorted.push_back({out_degree[i], i});
    }
    sort(out_degrees_sorted.begin(), out_degrees_sorted.end());

    vector<int> controlled_nodes;
    for (int i = 0; i < K_CONTROLLED; ++i) {
        controlled_nodes.push_back(out_degrees_sorted[i].second);
    }
    sort(controlled_nodes.begin(), controlled_nodes.end());

    vector<tuple<char, int, int>> changes;
    set<pair<int, int>> current_edges(initial_edges.begin(), initial_edges.end());

    for (int u : controlled_nodes) {
        vector<pair<int, int>> to_remove;
        for (auto const& edge : current_edges) {
            if (edge.first == u) {
                to_remove.push_back(edge);
            }
        }
        for (auto const& edge : to_remove) {
            changes.emplace_back('-', edge.first, edge.second);
            current_edges.erase(edge);
        }
    }

    for (int i = 0; i < K_CONTROLLED; ++i) {
        for (int j = 0; j < i; ++j) {
            int u = controlled_nodes[i];
            int v = controlled_nodes[j];
            changes.emplace_back('+', u, v);
        }
    }

    cout << changes.size() << endl;
    fflush(stdout);
    for (const auto& change : changes) {
        cout << get<0>(change) << " " << get<1>(change) << " " << get<2>(change) << endl;
        fflush(stdout);
    }

    for (const auto& edge : current_edges) {
        adj[edge.first].push_back(edge.second);
    }
    for (int i = 0; i < K_CONTROLLED; ++i) {
        for (int j = 0; j < i; ++j) {
            adj[controlled_nodes[i]].push_back(controlled_nodes[j]);
        }
    }

    compute_grundy(n);
    
    map<int, int> g_to_node;
    for(int node : controlled_nodes){
        g_to_node[g[node]] = node;
    }
    
    const int MAX_BITS = 10;
    vector<vector<int>> query_sets(MAX_BITS);
    for(int i = 0; i < MAX_BITS; ++i) {
        int target_xor = 1 << i;
        if (target_xor >= K_CONTROLLED) continue;

        vector<int> q_set;
        for(int j = 0; j < 6; ++j) {
            if((target_xor >> j) & 1) {
                if (g_to_node.count(1 << j)) {
                    q_set.push_back(g_to_node[1 << j]);
                }
            }
        }
        query_sets[i] = q_set;
    }

    for (int round = 0; round < t; ++round) {
        vector<int> candidates(n);
        iota(candidates.begin(), candidates.end(), 1);
        
        for (int i = 0; i < MAX_BITS; ++i) {
            if (candidates.size() <= 1) break;
            
            if (query_sets[i].empty()) continue;

            cout << "? " << query_sets[i].size();
            int query_nim_sum = 0;
            for (int node : query_sets[i]) {
                cout << " " << node;
                query_nim_sum ^= g[node];
            }
            cout << endl;
            fflush(stdout);

            string result;
            cin >> result;

            if (result == "Draw") {
                // This shouldn't happen with our graph modification as we avoid cycles.
                // If it does, we can't infer anything about g-values, so we don't filter.
            } else if (result == "Lose") {
                vector<int> next_candidates;
                for (int u : candidates) {
                    if ((g[u] ^ query_nim_sum) == 0) {
                        next_candidates.push_back(u);
                    }
                }
                candidates = next_candidates;
            } else { // Win
                vector<int> next_candidates;
                for (int u : candidates) {
                    if ((g[u] ^ query_nim_sum) != 0) {
                        next_candidates.push_back(u);
                    }
                }
                candidates = next_candidates;
            }
        }
        
        cout << "! " << candidates[0] << endl;
        fflush(stdout);
        string final_response;
        cin >> final_response;
        if (final_response == "Wrong") {
            return 0;
        }
    }

    return 0;
}