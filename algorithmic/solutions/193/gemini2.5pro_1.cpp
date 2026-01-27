#include <iostream>
#include <vector>
#include <queue>
#include <algorithm>
#include <map>

const long long INF = 1e18;

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

long long dfs(int u, int t, long long f) {
    if (u == t) return f;
    for (int& i = iter[u]; i < adj[u].size(); ++i) {
        Edge& e = adj[u][i];
        if (e.capacity > 0 && level[u] < level[e.to]) {
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
        while ((f = dfs(s, t, INF)) > 0) {
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
        std::cout << std::endl;
        return 0;
    }

    std::vector<std::pair<int, int>> pos_pos_clauses;
    std::vector<std::pair<int, int>> neg_neg_clauses;
    std::map<std::pair<int, int>, int> mixed_clauses_cap;

    for (int i = 0; i < m; ++i) {
        int u_in, v_in;
        std::cin >> u_in >> v_in;
        if (u_in > 0 && v_in > 0) {
            pos_pos_clauses.push_back({u_in, v_in});
        } else if (u_in < 0 && v_in < 0) {
            neg_neg_clauses.push_back({-u_in, -v_in});
        } else if (u_in < 0 && v_in > 0) {
            mixed_clauses_cap[{-u_in, v_in}]++;
        } else {
            mixed_clauses_cap[{-v_in, u_in}]++;
        }
    }

    int S = 0;
    int aux_pos_pos_base = n + 1;
    int aux_neg_neg_base = aux_pos_pos_base + pos_pos_clauses.size();
    int T = aux_neg_neg_base + neg_neg_clauses.size();
    V_count = T + 1;

    adj.resize(V_count);

    int current_aux = aux_pos_pos_base;
    for (const auto& p : pos_pos_clauses) {
        int u = p.first;
        int v = p.second;
        add_edge(S, current_aux, 1);
        add_edge(current_aux, u, INF);
        add_edge(current_aux, v, INF);
        current_aux++;
    }

    current_aux = aux_neg_neg_base;
    for (const auto& p : neg_neg_clauses) {
        int u = p.first;
        int v = p.second;
        add_edge(u, current_aux, INF);
        add_edge(v, current_aux, INF);
        add_edge(current_aux, T, 1);
        current_aux++;
    }

    for (const auto& pair : mixed_clauses_cap) {
        int u = pair.first.first;
        int v = pair.first.second;
        int cap = pair.second;
        add_edge(u, v, cap);
    }

    max_flow(S, T);

    std::vector<bool> s_partition(V_count, false);
    std::queue<int> q;

    q.push(S);
    s_partition[S] = true;

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
        if (s_partition[i]) {
            std::cout << "1" << (i == n ? "" : " ");
        } else {
            std::cout << "0" << (i == n ? "" : " ");
        }
    }
    std::cout << std::endl;

    return 0;
}