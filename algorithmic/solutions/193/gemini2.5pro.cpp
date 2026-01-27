#include <iostream>
#include <vector>
#include <queue>
#include <algorithm>
#include <cmath>

const long long FLOW_INF = 1e18;

struct Edge {
    int to;
    long long capacity;
    int rev;
};

std::vector<std::vector<Edge>> adj;
std::vector<int> level;
std::vector<int> iter;
int V_count;

void add_edge(int u, int v, long long cap) {
    adj[u].push_back({v, cap, (int)adj[v].size()});
    adj[v].push_back({u, 0, (int)adj[u].size() - 1});
}

bool bfs(int s, int t) {
    level.assign(V_count, -1);
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
    for (int& i = iter[v]; i < (int)adj[v].size(); ++i) {
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

long long max_flow(int s, int t) {
    long long flow = 0;
    while (bfs(s, t)) {
        iter.assign(V_count, 0);
        long long f;
        while ((f = dfs(s, t, FLOW_INF)) > 0) {
            flow += f;
        }
    }
    return flow;
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
        std::cout << "\n";
        return 0;
    }

    // Node mapping:
    // S: 0
    // Variables x_1, ..., x_n: nodes 1, ..., n
    // Clause auxiliary nodes: n+1, ..., n+m
    // T: n+m+1
    int s = 0;
    int t = n + m + 1;
    V_count = n + m + 2;
    adj.resize(V_count);

    int aux_node_idx = n + 1;
    long long large_cap = m + 1; // "Infinity", must be > total finite capacity sum

    for (int k = 0; k < m; ++k) {
        int u_in, v_in;
        std::cin >> u_in >> v_in;
        
        int u_var = std::abs(u_in);
        int v_var = std::abs(v_in);
        bool u_neg = u_in < 0;
        bool v_neg = v_in < 0;

        // Partition: S-part means TRUE, T-part means FALSE for a variable.
        if (!u_neg && !v_neg) { // clause (x_u V x_v)
            int c_node = aux_node_idx++;
            add_edge(s, c_node, 1);
            add_edge(c_node, u_var, large_cap);
            add_edge(c_node, v_var, large_cap);
        } else if (u_neg && v_neg) { // clause (!x_u V !x_v)
            int c_node = aux_node_idx++;
            add_edge(c_node, t, 1);
            add_edge(u_var, c_node, large_cap);
            add_edge(v_var, c_node, large_cap);
        } else if (!u_neg && v_neg) { // clause (x_u V !x_v)
            add_edge(v_var, u_var, 1);
        } else { // clause (!x_u V x_v)
            add_edge(u_var, v_var, 1);
        }
    }
    
    max_flow(s, t);

    // After max_flow, find S-partition by reachability from S in residual graph.
    std::vector<bool> s_partition(V_count, false);
    std::queue<int> q;
    q.push(s);
    s_partition[s] = true;
    while (!q.empty()) {
        int u = q.front();
        q.pop();
        for (const auto& edge : adj[u]) {
            if (edge.capacity > 0 && !s_partition[edge.to]) {
                s_partition[edge.to] = true;
                q.push(edge.to);
            }
        }
    }

    for (int i = 1; i <= n; ++i) {
        // v_i in S-partition -> x_i = TRUE (1)
        // v_i in T-partition -> x_i = FALSE (0)
        std::cout << (s_partition[i] ? "1" : "0") << (i == n ? "" : " ");
    }
    std::cout << "\n";

    return 0;
}