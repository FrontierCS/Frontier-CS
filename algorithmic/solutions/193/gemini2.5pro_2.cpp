#include <iostream>
#include <vector>
#include <queue>
#include <algorithm>
#include <cmath>

const long long INF = 1e12;

struct Edge {
    int to;
    long long capacity;
    int rev;
};

std::vector<std::vector<Edge>> adj;
std::vector<int> level;
std::vector<int> iter;

void add_edge(int u, int v, long long cap) {
    adj[u].push_back({v, cap, (int)adj[v].size()});
    adj[v].push_back({u, 0, (int)adj[u].size() - 1});
}

bool bfs(int s, int t) {
    level.assign(adj.size(), -1);
    std::queue<int> q;
    level[s] = 0;
    q.push(s);
    while (!q.empty()) {
        int v = q.front();
        q.pop();
        for (const auto& edge : adj[v]) {
            if (edge.capacity > 0 && level[edge.to] < 0) {
                level[edge.to] = level[v] + 1;
                q.push(edge.to);
            }
        }
    }
    return level[t] != -1;
}

long long dfs(int v, int t, long long f) {
    if (v == t) return f;
    for (int& i = iter[v]; i < adj[v].size(); ++i) {
        Edge& e = adj[v][i];
        if (e.capacity > 0 && level[v] < level[e.to]) {
            long long d = dfs(e.to, t, std::min(f, e.capacity));
            if (d > 0) {
                e.capacity -= d;
                adj[e.to][e.rev].capacity += d;
                return d;
            }
        }
    }
    return 0;
}

void max_flow(int s, int t) {
    while (bfs(s, t)) {
        iter.assign(adj.size(), 0);
        while (dfs(s, t, INF) > 0) {}
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n, m;
    std::cin >> n >> m;

    int s = 0, t = 1;
    int var_node_start = 2;
    int aux_node_start = var_node_start + n;
    
    std::vector<std::pair<int, int>> clauses(m);
    int aux_needed = 0;
    for (int i = 0; i < m; ++i) {
        std::cin >> clauses[i].first >> clauses[i].second;
        int u = clauses[i].first;
        int v = clauses[i].second;
        if (std::abs(u) != std::abs(v)) {
            if ((u > 0 && v > 0) || (u < 0 && v < 0)) {
                aux_needed++;
            }
        }
    }
    
    int total_nodes = aux_node_start + aux_needed;
    adj.resize(total_nodes);
    int next_aux_node = aux_node_start;

    for (const auto& clause : clauses) {
        int u_lit = clause.first;
        int v_lit = clause.second;
        
        int u_var = std::abs(u_lit), v_var = std::abs(v_lit);
        bool u_neg = u_lit < 0, v_neg = v_lit < 0;

        int u_node = var_node_start + u_var - 1;
        int v_node = var_node_start + v_var - 1;

        if (u_neg) {
            if (v_neg) { // ¬u ∨ ¬v
                if (u_var == v_var) { // ¬u
                    add_edge(s, u_node, 1);
                } else {
                    int aux = next_aux_node++;
                    add_edge(s, aux, 1);
                    add_edge(aux, u_node, INF);
                    add_edge(aux, v_node, INF);
                }
            } else { // ¬u ∨ v
                if (u_var != v_var) {
                    add_edge(v_node, u_node, 1);
                }
            }
        } else {
            if (v_neg) { // u ∨ ¬v
                if (u_var != v_var) {
                    add_edge(u_node, v_node, 1);
                }
            } else { // u ∨ v
                if (u_var == v_var) { // u
                    add_edge(u_node, t, 1);
                } else {
                    int aux = next_aux_node++;
                    add_edge(aux, t, 1);
                    add_edge(u_node, aux, INF);
                    add_edge(v_node, aux, INF);
                }
            }
        }
    }

    max_flow(s, t);

    std::vector<bool> visited(total_nodes, false);
    std::queue<int> q;

    q.push(s);
    visited[s] = true;

    while (!q.empty()) {
        int u = q.front();
        q.pop();

        for (const auto& edge : adj[u]) {
            if (edge.capacity > 0 && !visited[edge.to]) {
                visited[edge.to] = true;
                q.push(edge.to);
            }
        }
    }

    for (int i = 0; i < n; ++i) {
        int node_idx = var_node_start + i;
        if (visited[node_idx]) {
            std::cout << 0 << (i == n - 1 ? "" : " ");
        } else {
            std::cout << 1 << (i == n - 1 ? "" : " ");
        }
    }
    std::cout << std::endl;

    return 0;
}