#include <iostream>
#include <vector>
#include <algorithm>
#include <stack>
#include <random>
#include <chrono>
#include <queue>

using namespace std;

const int MAXN = 500005;
const int INF = 1e9;

vector<int> adj[MAXN];
vector<int> rev_adj[MAXN]; // Reverse edges for BFS
int n, m;
int a_scores[10];

// SCC
int dfn[MAXN], low[MAXN], timer;
int scc[MAXN], scc_cnt;
bool in_stack[MAXN];
stack<int> st;
int scc_size[MAXN];

// Topological sort
int scc_rank[MAXN]; 

// DFS
bool visited[MAXN];
vector<int> path;
vector<int> best_path;
int cnt_visited_in_scc[MAXN];

// Heuristics
bool is_exit[MAXN];
int dist_to_exit[MAXN];

// Random
mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

void tarjan(int u) {
    dfn[u] = low[u] = ++timer;
    st.push(u);
    in_stack[u] = true;
    
    for (int v : adj[u]) {
        if (!dfn[v]) {
            tarjan(v);
            low[u] = min(low[u], low[v]);
        } else if (in_stack[v]) {
            low[u] = min(low[u], dfn[v]);
        }
    }
    
    if (low[u] == dfn[u]) {
        scc_cnt++;
        while (true) {
            int v = st.top();
            st.pop();
            in_stack[v] = false;
            scc[v] = scc_cnt;
            scc_size[scc_cnt]++;
            if (u == v) break;
        }
    }
}

auto start_time = chrono::steady_clock::now();
bool time_limit_exceeded() {
    auto curr = chrono::steady_clock::now();
    return chrono::duration_cast<chrono::milliseconds>(curr - start_time).count() > 3800;
}

bool solve_dfs(int u) {
    if (time_limit_exceeded()) return false;
    
    visited[u] = true;
    path.push_back(u);
    int u_scc = scc[u];
    cnt_visited_in_scc[u_scc]++;
    
    if (path.size() > best_path.size()) {
        best_path = path;
    }
    
    if (best_path.size() == n) return true;
    
    int u_rank = scc_rank[u_scc];
    
    for (int v : adj[u]) {
        if (visited[v]) continue;
        
        int v_scc = scc[v];
        int v_rank = scc_rank[v_scc];
        
        if (v_rank == u_rank) {
            if (solve_dfs(v)) return true;
        } else if (v_rank == u_rank + 1) {
            if (cnt_visited_in_scc[u_scc] == scc_size[u_scc]) {
                if (solve_dfs(v)) return true;
            }
        }
        
        if (time_limit_exceeded()) break;
    }
    
    visited[u] = false;
    path.pop_back();
    cnt_visited_in_scc[u_scc]--;
    return false;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    if (!(cin >> n >> m)) return 0;
    
    for (int i = 0; i < 10; ++i) cin >> a_scores[i];
    
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        rev_adj[v].push_back(u);
    }
    
    for (int i = 1; i <= n; ++i) {
        if (!dfn[i]) tarjan(i);
    }
    
    for (int i = 1; i <= scc_cnt; ++i) {
        scc_rank[i] = scc_cnt - i;
    }
    
    // Identify exit nodes and compute distances
    for (int u = 1; u <= n; ++u) {
        dist_to_exit[u] = INF;
        int r = scc_rank[scc[u]];
        for (int v : adj[u]) {
            if (scc_rank[scc[v]] == r + 1) {
                is_exit[u] = true;
                break;
            }
        }
    }
    
    // BFS for distances within each SCC
    // We can do one global BFS if we are careful, but doing it per SCC is safer/clearer.
    // Actually, we can just iterate all nodes, if is_exit push to queue.
    // Then run BFS on reverse edges, but ONLY traversing edges within same SCC.
    queue<int> q;
    for (int u = 1; u <= n; ++u) {
        if (is_exit[u]) {
            dist_to_exit[u] = 0;
            q.push(u);
        }
    }
    
    while (!q.empty()) {
        int u = q.front();
        q.pop();
        
        int u_scc = scc[u];
        for (int v : rev_adj[u]) {
            if (scc[v] == u_scc) { // Internal edges only
                if (dist_to_exit[v] == INF) {
                    dist_to_exit[v] = dist_to_exit[u] + 1;
                    q.push(v);
                }
            }
        }
    }
    
    // Sort adjacency lists
    for (int i = 1; i <= n; ++i) {
        shuffle(adj[i].begin(), adj[i].end(), rng); // Randomize initially
        
        sort(adj[i].begin(), adj[i].end(), [&](int a, int b) {
            int r_a = scc_rank[scc[a]];
            int r_b = scc_rank[scc[b]];
            int r_u = scc_rank[scc[i]];
            
            // Priority 1: Rank. Prefer same rank.
            bool same_rank_a = (r_a == r_u);
            bool same_rank_b = (r_b == r_u);
            
            if (same_rank_a != same_rank_b) {
                return same_rank_a; // Same rank first
            }
            
            if (same_rank_a) {
                // Both same rank. Prefer larger dist_to_exit.
                // If dists are equal (e.g. INF), order doesn't matter.
                // Note: non-exit nodes have dist > 0 (or INF). Exit nodes have dist 0.
                // So sorting by dist desc puts non-exits first.
                return dist_to_exit[a] > dist_to_exit[b];
            } else {
                // Both next rank. Prefer larger dist_to_exit in NEXT component.
                // This helps choosing the best entry point for the next SCC.
                return dist_to_exit[a] > dist_to_exit[b];
            }
        });
    }
    
    // Select start nodes
    int first_scc_id = scc_cnt; // Rank 0
    vector<int> starts;
    for (int i = 1; i <= n; ++i) {
        if (scc[i] == first_scc_id) {
            starts.push_back(i);
        }
    }
    
    // Sort starts by dist_to_exit descending
    sort(starts.begin(), starts.end(), [&](int a, int b) {
        return dist_to_exit[a] > dist_to_exit[b];
    });
    
    // Run DFS
    for (int start_node : starts) {
        if (solve_dfs(start_node)) break;
        if (time_limit_exceeded()) break;
    }
    
    cout << best_path.size() << "\n";
    for (size_t i = 0; i < best_path.size(); ++i) {
        cout << best_path[i] << (i == best_path.size() - 1 ? "" : " ");
    }
    cout << "\n";
    
    return 0;
}