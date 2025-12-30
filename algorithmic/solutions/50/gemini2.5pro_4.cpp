#include <iostream>
#include <vector>
#include <queue>
#include <numeric>
#include <algorithm>

using flow_t = long long;

const flow_t INF = 1e18;

struct Edge {
    int to;
    flow_t capacity;
    int rev;
};

std::vector<std::vector<Edge>> G;
std::vector<int> level;
std::vector<int> iter;
int V_count;

void add_edge(int u, int v, flow_t cap) {
    G[u].push_back({v, cap, (int)G[v].size()});
    G[v].push_back({u, 0, (int)G[u].size() - 1});
}

bool bfs(int s, int t) {
    level.assign(V_count, -1);
    std::queue<int> q;
    level[s] = 0;
    q.push(s);
    while (!q.empty()) {
        int v = q.front();
        q.pop();
        for (const auto& edge : G[v]) {
            if (edge.capacity > 0 && level[edge.to] < 0) {
                level[edge.to] = level[v] + 1;
                q.push(edge.to);
            }
        }
    }
    return level[t] != -1;
}

flow_t dfs(int v, int t, flow_t f) {
    if (v == t) return f;
    for (int& i = iter[v]; i < (int)G[v].size(); ++i) {
        Edge& e = G[v][i];
        if (e.capacity > 0 && level[v] < level[e.to]) {
            flow_t d = dfs(e.to, t, std::min(f, e.capacity));
            if (d > 0) {
                e.capacity -= d;
                G[e.to][e.rev].capacity += d;
                return d;
            }
        }
    }
    return 0;
}

flow_t max_flow(int s, int t) {
    flow_t flow = 0;
    while (bfs(s, t)) {
        iter.assign(V_count, 0);
        flow_t f;
        while ((f = dfs(s, t, INF)) > 0) {
            flow += f;
        }
    }
    return flow;
}

std::vector<bool> visited;
void find_reachable(int u) {
    visited[u] = true;
    for (const auto& edge : G[u]) {
        if (edge.capacity > 0 && !visited[edge.to]) {
            find_reachable(edge.to);
        }
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n, m;
    std::cin >> n >> m;

    std::vector<flow_t> costs(m + 1);
    flow_t total_cost_sum = 0;
    for (int i = 1; i <= m; ++i) {
        std::cin >> costs[i];
        total_cost_sum += costs[i];
    }

    int s = 0, t = n + m + 1;
    V_count = n + m + 2;
    G.assign(V_count, std::vector<Edge>());

    flow_t penalty = total_cost_sum + 1;

    for (int i = 1; i <= n; ++i) {
        add_edge(s, i, penalty);
    }
    
    for (int i = 1; i <= n; ++i) {
        int k;
        std::cin >> k;
        for (int j = 0; j < k; ++j) {
            int set_id;
            std::cin >> set_id;
            add_edge(i, n + set_id, INF);
        }
    }
    
    for (int i = 1; i <= m; ++i) {
        add_edge(n + i, t, costs[i]);
    }

    max_flow(s, t);

    visited.assign(V_count, false);
    find_reachable(s);

    std::vector<int> chosen_sets;
    for (int i = 1; i <= m; ++i) {
        if (visited[n + i]) {
            chosen_sets.push_back(i);
        }
    }

    std::cout << chosen_sets.size() << "\n";
    if (!chosen_sets.empty()) {
        for (int i = 0; i < (int)chosen_sets.size(); ++i) {
            std::cout << chosen_sets[i] << (i == (int)chosen_sets.size() - 1 ? "" : " ");
        }
    }
    std::cout << "\n";

    return 0;
}