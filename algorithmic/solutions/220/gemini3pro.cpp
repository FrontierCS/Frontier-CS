#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

using namespace std;

// Dinic's Algorithm for Maximum Flow
struct Edge {
    int to;
    int capacity;
    int flow;
    int rev;
};

vector<vector<Edge>> adj;
vector<int> level;
vector<int> ptr;

void add_edge(int from, int to, int cap) {
    adj[from].push_back({to, cap, 0, (int)adj[to].size()});
    adj[to].push_back({from, 0, 0, (int)adj[from].size() - 1});
}

bool bfs(int s, int t) {
    fill(level.begin(), level.end(), -1);
    level[s] = 0;
    vector<int> q;
    q.push_back(s);
    int head = 0;
    while (head < q.size()) {
        int v = q[head++];
        for (const auto& edge : adj[v]) {
            if (edge.capacity - edge.flow > 0 && level[edge.to] == -1) {
                level[edge.to] = level[v] + 1;
                q.push_back(edge.to);
            }
        }
    }
    return level[t] != -1;
}

int dfs(int v, int t, int pushed) {
    if (pushed == 0) return 0;
    if (v == t) return pushed;
    for (int& cid = ptr[v]; cid < adj[v].size(); ++cid) {
        auto& edge = adj[v][cid];
        int tr = edge.to;
        if (level[v] + 1 != level[tr] || edge.capacity - edge.flow == 0) continue;
        int push = dfs(tr, t, min(pushed, edge.capacity - edge.flow));
        if (push == 0) continue;
        edge.flow += push;
        adj[tr][edge.rev].flow -= push;
        return push;
    }
    return 0;
}

int dinic(int s, int t) {
    int flow = 0;
    while (bfs(s, t)) {
        fill(ptr.begin(), ptr.end(), 0);
        while (int pushed = dfs(s, t, 1e9)) {
            flow += pushed;
        }
    }
    return flow;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    if (!(cin >> n)) return 0;

    vector<vector<int>> counts(n + 1, vector<int>(n + 1, 0));
    for (int i = 1; i <= n; ++i) {
        for (int j = 0; j < n; ++j) {
            int c;
            cin >> c;
            counts[i][c]++;
        }
    }

    struct Op {
        vector<int> moves;
    };
    vector<Op> ops;

    while (true) {
        bool all_solid = true;
        vector<bool> is_solid(n + 1, false);
        for (int i = 1; i <= n; ++i) {
            if (counts[i][i] == n) {
                is_solid[i] = true;
            } else {
                all_solid = false;
            }
        }

        if (all_solid) break;

        // Build flow network
        int S = 0;
        int T = 2 * n + 1;
        adj.assign(T + 1, vector<Edge>());
        level.resize(T + 1);
        ptr.resize(T + 1);

        for (int i = 1; i <= n; ++i) {
            add_edge(S, i, 1);
            add_edge(n + i, T, 1);
            if (is_solid[i]) {
                // Forced to pass card i (shift 0, but valid for solid)
                add_edge(i, n + i, 1);
            } else {
                // For non-solid, prefer shift > 0 (v != i)
                for (int v = 1; v <= n; ++v) {
                    if (counts[i][v] > 0 && v != i) {
                        add_edge(i, n + v, 1);
                    }
                }
            }
        }

        int flow = dinic(S, T);
        
        // If we couldn't match everyone with priority edges, add secondary edges
        if (flow < n) {
             for (int i = 1; i <= n; ++i) {
                if (!is_solid[i] && counts[i][i] > 0) {
                     add_edge(i, n + i, 1);
                }
            }
            flow += dinic(S, T);
        }

        Op current_op;
        vector<int> d(n + 1);

        for (int i = 1; i <= n; ++i) {
            for (const auto& e : adj[i]) {
                if (e.to > n && e.to <= 2 * n && e.flow == 1) {
                    int val = e.to - n;
                    d[i] = val;
                    break;
                }
            }
        }
        
        vector<int> line_moves;
        for(int i=1; i<=n; ++i) line_moves.push_back(d[i]);
        ops.push_back({line_moves});

        vector<vector<int>> next_counts = counts;
        for (int i = 1; i <= n; ++i) {
            int val = d[i];
            next_counts[i][val]--;
            int next_player = (i % n) + 1;
            next_counts[next_player][val]++;
        }
        counts = next_counts;
    }

    cout << ops.size() << "\n";
    for (const auto& op : ops) {
        for (int i = 0; i < n; ++i) {
            cout << op.moves[i] << (i == n - 1 ? "" : " ");
        }
        cout << "\n";
    }

    return 0;
}