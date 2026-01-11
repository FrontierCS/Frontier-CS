#include <iostream>
#include <vector>
#include <queue>
#include <algorithm>
#include <unordered_map>
#include <tuple>
#include <numeric>
#include <climits>

using namespace std;

int main() {
    int N, K;
    cin >> N >> K;
    int M = N + K;
    vector<int> ids(M);
    vector<int> xs(M), ys(M);
    vector<char> types(M);
    
    for (int i = 0; i < M; ++i) {
        cin >> ids[i] >> xs[i] >> ys[i] >> types[i];
    }
    
    // weight function: returns scaled weight (5 * actual cost) or LLONG_MAX for forbidden C-C edges
    auto weight = [&](int i, int j) -> long long {
        if (types[i] == 'C' && types[j] == 'C') return LLONG_MAX;
        long long dx = xs[i] - xs[j];
        long long dy = ys[i] - ys[j];
        long long d = dx * dx + dy * dy;
        if (types[i] == 'C' || types[j] == 'C') {
            return d * 5LL;
        } else {
            if (types[i] == 'S' || types[j] == 'S') {
                return d * 4LL;
            } else {
                return d * 5LL;
            }
        }
    };
    
    // Prim's MST on a given set of node indices
    auto mst = [&](vector<int>& nodes) -> pair<vector<tuple<int, int, long long>>, long long> {
        int m = nodes.size();
        vector<int> parent(m, -1);
        vector<long long> min_e(m, LLONG_MAX);
        vector<bool> used(m, false);
        min_e[0] = 0;
        long long total_scaled = 0;
        vector<tuple<int, int, long long>> edges; // (original index u, v, scaled weight)
        
        for (int i = 0; i < m; ++i) {
            int v = -1;
            for (int j = 0; j < m; ++j) {
                if (!used[j] && (v == -1 || min_e[j] < min_e[v]))
                    v = j;
            }
            if (min_e[v] == LLONG_MAX) break; // should not happen
            used[v] = true;
            if (parent[v] != -1) {
                int u = parent[v];
                long long w = min_e[v];
                edges.emplace_back(nodes[u], nodes[v], w);
                total_scaled += w;
            }
            for (int to = 0; to < m; ++to) {
                if (!used[to]) {
                    long long w = weight(nodes[v], nodes[to]);
                    if (w != LLONG_MAX && w < min_e[to]) {
                        min_e[to] = w;
                        parent[to] = v;
                    }
                }
            }
        }
        return {edges, total_scaled};
    };
    
    // Robot indices
    vector<int> robot_idx;
    for (int i = 0; i < M; ++i) {
        if (types[i] != 'C') robot_idx.push_back(i);
    }
    
    // All indices
    vector<int> all_idx(M);
    iota(all_idx.begin(), all_idx.end(), 0);
    
    auto [robots_edges, robots_total] = mst(robot_idx);
    auto [all_edges, all_total] = mst(all_idx);
    
    // Build adjacency for the full MST
    vector<unordered_map<int, long long>> adj(M);
    vector<int> deg(M, 0);
    for (auto& [u, v, w] : all_edges) {
        adj[u][v] = w;
        adj[v][u] = w;
        deg[u]++;
        deg[v]++;
    }
    
    // Prune leaf relays
    queue<int> q;
    for (int i = 0; i < M; ++i) {
        if (types[i] == 'C' && deg[i] == 1) q.push(i);
    }
    long long current_total = all_total;
    while (!q.empty()) {
        int u = q.front(); q.pop();
        if (deg[u] != 1 || types[u] != 'C') continue;
        // Get the only neighbor
        int v = adj[u].begin()->first;
        long long w = adj[u].begin()->second;
        // Remove edge
        adj[u].erase(v);
        adj[v].erase(u);
        deg[u]--;
        deg[v]--;
        current_total -= w;
        if (deg[v] == 1 && types[v] == 'C') q.push(v);
    }
    
    // Choose the better solution
    bool use_robots_mst = (robots_total <= current_total);
    
    // Prepare output
    vector<int> selected_relays;
    vector<pair<int, int>> output_edges;
    
    if (use_robots_mst) {
        // No relays selected
        for (auto& [u, v, w] : robots_edges) {
            output_edges.emplace_back(ids[u], ids[v]);
        }
    } else {
        // Use pruned tree
        for (int i = 0; i < M; ++i) {
            if (types[i] == 'C' && deg[i] > 0) selected_relays.push_back(ids[i]);
        }
        for (int u = 0; u < M; ++u) {
            for (auto& [v, w] : adj[u]) {
                if (u < v) output_edges.emplace_back(ids[u], ids[v]);
            }
        }
    }
    
    // Sort outputs
    sort(selected_relays.begin(), selected_relays.end());
    sort(output_edges.begin(), output_edges.end());
    
    // First line: selected relays
    if (selected_relays.empty()) {
        cout << "#" << endl;
    } else {
        for (size_t i = 0; i < selected_relays.size(); ++i) {
            if (i > 0) cout << "#";
            cout << selected_relays[i];
        }
        cout << endl;
    }
    
    // Second line: edges
    if (output_edges.empty()) {
        cout << endl;
    } else {
        for (size_t i = 0; i < output_edges.size(); ++i) {
            if (i > 0) cout << "#";
            cout << output_edges[i].first << "-" << output_edges[i].second;
        }
        cout << endl;
    }
    
    return 0;
}