#include <iostream>
#include <vector>
#include <algorithm>
#include <numeric>

// Using a slightly larger buffer for safety
const int MAXN = 500005;

// Graph representation
std::vector<int> adj[MAXN];
int n, m;
int a[10];

// Tarjan's algorithm variables for SCC
int dfn[MAXN], low[MAXN], timer;
int stk[MAXN], top;
bool on_stk[MAXN];
int scc[MAXN], scc_cnt;
std::vector<int> scc_nodes[MAXN];
int scc_size[MAXN];

// SCC condensation graph and properties
std::vector<int> scc_adj[MAXN];
int scc_indegree[MAXN];
int scc_out_u[MAXN], scc_in_v[MAXN]; // Transition vertices between SCCs

// Adjacency lists for subgraphs induced by each SCC
std::vector<int> scc_internal_adj[MAXN];

void tarjan(int u) {
    dfn[u] = low[u] = ++timer;
    stk[++top] = u;
    on_stk[u] = true;

    for (int v : adj[u]) {
        if (!dfn[v]) {
            tarjan(v);
            low[u] = std::min(low[u], low[v]);
        } else if (on_stk[v]) {
            low[u] = std::min(low[u], dfn[v]);
        }
    }

    if (dfn[u] == low[u]) {
        ++scc_cnt;
        int v;
        do {
            v = stk[top--];
            on_stk[v] = false;
            scc[v] = scc_cnt;
            scc_nodes[scc_cnt].push_back(v);
            scc_size[scc_cnt]++;
        } while (u != v);
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::cin >> n >> m;
    for (int i = 0; i < 10; ++i) {
        std::cin >> a[i];
    }

    for (int i = 0; i < m; ++i) {
        int u, v;
        std::cin >> u >> v;
        adj[u].push_back(v);
    }

    for (int i = 1; i <= n; ++i) {
        if (!dfn[i]) {
            tarjan(i);
        }
    }
    
    for (int u = 1; u <= n; ++u) {
        for (int v : adj[u]) {
            if (scc[u] != scc[v]) {
                scc_adj[scc[u]].push_back(scc[v]);
                scc_indegree[scc[v]]++;
                scc_out_u[scc[u]] = u;
                scc_in_v[scc[v]] = v;
            } else {
                scc_internal_adj[u].push_back(v);
            }
        }
    }

    int start_scc = -1;
    for (int i = 1; i <= scc_cnt; ++i) {
        if (scc_indegree[i] == 0) {
            start_scc = i;
            break;
        }
    }
    
    std::vector<int> scc_path;
    if (start_scc != -1) {
        int current_scc = start_scc;
        while(true) {
            scc_path.push_back(current_scc);
            if (!scc_adj[current_scc].empty()) {
                current_scc = scc_adj[current_scc][0];
            } else {
                break;
            }
        }
    }

    std::vector<int> final_path;
    final_path.reserve(n);

    int entry_node = -1;

    for (size_t i = 0; i < scc_path.size(); ++i) {
        int scc_id = scc_path[i];
        
        if (scc_size[scc_id] == 1) {
            final_path.push_back(scc_nodes[scc_id][0]);
        } else {
            int start_node;
            int exit_node = scc_out_u[scc_id];

            if (entry_node != -1) {
                start_node = entry_node;
            } else { // First SCC in path
                if (exit_node != 0) { // Not the only SCC
                    start_node = scc_internal_adj[exit_node][0];
                } else { // The only SCC
                    start_node = scc_nodes[scc_id][0];
                }
            }
            
            int current_node = start_node;
            for (int j = 0; j < scc_size[scc_id]; ++j) {
                final_path.push_back(current_node);
                if (exit_node != 0 && current_node == exit_node) break;
                current_node = scc_internal_adj[current_node][0];
            }
        }

        if (!scc_adj[scc_id].empty()) {
            entry_node = scc_in_v[scc_adj[scc_id][0]];
        }
    }

    std::cout << final_path.size() << "\n";
    for (size_t i = 0; i < final_path.size(); ++i) {
        std::cout << final_path[i] << (i == final_path.size() - 1 ? "" : " ");
    }
    std::cout << "\n";

    return 0;
}