#include <iostream>
#include <vector>
#include <queue>
#include <map>
#include <algorithm>
#include <cmath>

const int INF = 1e9 + 7;

struct Edge {
    int to;
    int capacity;
    int rev;
};

std::vector<std::vector<Edge>> adj;
std::vector<int> level;
std::vector<int> iter;
int V_count;

void add_edge(int u, int v, int cap) {
    adj[u].push_back({v, cap, (int)adj[v].size()});
    adj[v].push_back({u, 0, (int)adj[u].size() - 1});
}

bool bfs(int s, int t) {
    level.assign(V_count, -1);
    std::queue<int> q;
    level[s] = 0;
    q.push(s);
    while (!q.empty()) {
        int u = q.front();
        q.pop();
        for (const auto& edge : adj[u]) {
            if (edge.capacity > 0 && level[edge.to] < 0) {
                level[edge.to] = level[u] + 1;
                q.push(edge.to);
            }
        }
    }
    return level[t] != -1;
}

int dfs(int u, int t, int f) {
    if (u == t) return f;
    for (int& i = iter[u]; i < (int)adj[u].size(); ++i) {
        Edge& e = adj[u][i];
        if (e.capacity > 0 && level[u] < level[e.to]) {
            int d = dfs(e.to, t, std::min(f, e.capacity));
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
        iter.assign(V_count, 0);
        while (dfs(s, t, INF) > 0) {
        }
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n, m;
    std::cin >> n >> m;

    if (m == 0) {
        for (int i = 0; i < n; ++i) {
            std::cout << "0" << (i == n - 1 ? "" : " ");
        }
        std::cout << std::endl;
        return 0;
    }

    int s = 0, t = 1;
    int var_node_start = 2;
    int aux_node_start = var_node_start + n;
    
    std::vector<std::pair<int, int>> clauses(m);
    int same_sign_clauses_count = 0;
    for (int i = 0; i < m; ++i) {
        std::cin >> clauses[i].first >> clauses[i].second;
        if ((clauses[i].first > 0 && clauses[i].second > 0) || (clauses[i].first < 0 && clauses[i].second < 0)) {
            same_sign_clauses_count++;
        }
    }

    V_count = aux_node_start + same_sign_clauses_count;
    adj.resize(V_count);
    
    int next_aux = aux_node_start;
    std::map<std::pair<int, int>, int> mixed_caps;

    for (const auto& clause : clauses) {
        int u_lit = clause.first;
        int v_lit = clause.second;

        int u_var = std::abs(u_lit);
        int v_var = std::abs(v_lit);
        bool u_sign = u_lit > 0;
        bool v_sign = v_lit > 0;

        int u_node = var_node_start + u_var - 1;
        int v_node = var_node_start + v_var - 1;

        if (u_sign && v_sign) { // x_u or x_v
            int aux = next_aux++;
            add_edge(s, aux, 1);
            add_edge(aux, u_node, INF);
            add_edge(aux, v_node, INF);
        } else if (!u_sign && !v_sign) { // not x_u or not x_v
            int aux = next_aux++;
            add_edge(aux, t, 1);
            add_edge(u_node, aux, INF);
            add_edge(v_node, aux, INF);
        } else if (!u_sign && v_sign) { // not x_u or x_v
            mixed_caps[{u_node, v_node}]++;
        } else { // x_u or not x_v
            mixed_caps[{v_node, u_node}]++;
        }
    }

    for (auto const& [nodes, cap] : mixed_caps) {
        add_edge(nodes.first, nodes.second, cap);
    }
    
    max_flow(s, t);

    std::vector<bool> visited(V_count, false);
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
        int var_node = var_node_start + i;
        std::cout << (visited[var_node] ? "1" : "0") << (i == n - 1 ? "" : " ");
    }
    std::cout << std::endl;

    return 0;
}