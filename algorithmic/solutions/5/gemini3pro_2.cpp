#include <iostream>
#include <vector>
#include <algorithm>
#include <stack>
#include <random>
#include <chrono>

using namespace std;

const int MAXN = 500005;

int n, m;
int a[10];
vector<int> adj[MAXN];

// Tarjan's Algorithm for SCC
int dfn[MAXN], low[MAXN], timer;
int stk[MAXN], top;
bool in_stk[MAXN];
int scc[MAXN], scc_cnt;
int scc_size[MAXN];

void tarjan(int u) {
    dfn[u] = low[u] = ++timer;
    stk[++top] = u;
    in_stk[u] = true;
    for (int v : adj[u]) {
        if (!dfn[v]) {
            tarjan(v);
            low[u] = min(low[u], low[v]);
        } else if (in_stk[v]) {
            low[u] = min(low[u], dfn[v]);
        }
    }
    if (low[u] == dfn[u]) {
        scc_cnt++;
        int v;
        do {
            v = stk[top--];
            in_stk[v] = false;
            scc[v] = scc_cnt;
            scc_size[scc_cnt]++;
        } while (u != v);
    }
}

// Logic variables
vector<int> scc_adj[MAXN];
int in_degree[MAXN];
int scc_rank[MAXN]; // Topological order rank
int scc_sz_by_rank[MAXN];
vector<int> nodes_in_scc[MAXN];

// DFS Solver state
bool visited[MAXN];
int current_scc_visited[MAXN]; // Count of visited nodes in each scc rank
vector<int> adj_sorted[MAXN];
int out_deg_same[MAXN]; // Helper for Warnsdorff's heuristic

// Random number generator
mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

// Backtracking control
long long operations = 0;
const long long MAX_OPS = 90000000; // Heuristic operation limit
bool found = false;

struct State {
    int u;
    int idx; // current index in adj_sorted[u]
};

vector<int> best_path;

void solve() {
    // 1. Find SCCs
    for (int i = 1; i <= n; i++) if (!dfn[i]) tarjan(i);
    
    // 2. Build Condensation Graph
    for (int u = 1; u <= n; u++) {
        for (int v : adj[u]) {
            if (scc[u] != scc[v]) {
                scc_adj[scc[u]].push_back(scc[v]);
                in_degree[scc[v]]++;
            }
        }
    }
    
    // 3. Topological Sort of SCCs
    vector<int> q;
    for (int i = 1; i <= scc_cnt; i++) {
        sort(scc_adj[i].begin(), scc_adj[i].end());
        scc_adj[i].erase(unique(scc_adj[i].begin(), scc_adj[i].end()), scc_adj[i].end());
        if (in_degree[i] == 0) q.push_back(i);
    }
    
    vector<int> topo_order;
    int head = 0;
    while(head < q.size()){
        int u = q[head++];
        topo_order.push_back(u);
        for(int v : scc_adj[u]){
            in_degree[v]--;
            if(in_degree[v] == 0) q.push_back(v);
        }
    }
    
    // 4. Assign ranks based on topological order
    // Since a Hamiltonian Path exists, the condensation graph must allow a linear traversal.
    // The topological sort index effectively gives the order of SCCs in that path.
    for(int i=0; i<topo_order.size(); ++i){
        scc_rank[topo_order[i]] = i;
        scc_sz_by_rank[i] = scc_size[topo_order[i]];
        nodes_in_scc[i].reserve(scc_size[topo_order[i]]);
    }
    
    for(int i=1; i<=n; ++i){
        nodes_in_scc[scc_rank[scc[i]]].push_back(i);
    }

    // 5. Calculate 'out_deg_same' for Warnsdorff's heuristic
    for(int u=1; u<=n; ++u){
        int r_u = scc_rank[scc[u]];
        for(int v : adj[u]){
            if(scc_rank[scc[v]] == r_u) {
                out_deg_same[u]++;
            }
        }
    }

    // 6. Sort adjacency lists with heuristic
    // Heuristic: Prefer same-SCC neighbors first (sorted by their out-degree), then next-SCC neighbors.
    for(int u=1; u<=n; ++u){
        int r_u = scc_rank[scc[u]];
        vector<pair<int, int>> neighbors; // {priority, v}
        for(int v : adj[u]){
            int r_v = scc_rank[scc[v]];
            if(r_v == r_u) {
                neighbors.push_back({0, v}); 
            } else if (r_v == r_u + 1) {
                neighbors.push_back({1, v});
            }
            // Edges skipping SCCs (u -> u+k where k>1) or going back are ignored
            // because they violate the Hamiltonian Path structure (must visit all nodes).
        }
        
        sort(neighbors.begin(), neighbors.end(), [&](const pair<int,int>& a, const pair<int,int>& b){
            if(a.first != b.first) return a.first < b.first;
            if(a.first == 0) {
                 // For same SCC, use Warnsdorff's rule: pick neighbor with fewer available moves.
                 return out_deg_same[a.second] < out_deg_same[b.second];
            }
            return false; 
        });
        
        for(auto &p : neighbors) adj_sorted[u].push_back(p.second);
    }

    // 7. Randomized DFS with Backtracking/Restarts
    vector<int>& start_nodes = nodes_in_scc[0];
    vector<State> dfs_stack;
    dfs_stack.reserve(n);
    
    while(operations < MAX_OPS && !found) {
        // Reset state for new attempt
        for(int i=1; i<=n; ++i) visited[i] = false;
        for(int i=0; i<scc_cnt; ++i) current_scc_visited[i] = 0;
        dfs_stack.clear();
        
        if(start_nodes.empty()) break; 
        int start_node = start_nodes[rng() % start_nodes.size()];
        
        visited[start_node] = true;
        current_scc_visited[scc_rank[scc[start_node]]]++;
        dfs_stack.push_back({start_node, 0});
        
        // Save initial path
        if(dfs_stack.size() > best_path.size()){
            best_path.clear();
            for(auto &st : dfs_stack) best_path.push_back(st.u);
        }

        while(!dfs_stack.empty()){
            operations++;
            if(operations > MAX_OPS) break;
            
            State &top_state = dfs_stack.back();
            int u = top_state.u;
            
            if(dfs_stack.size() == n) {
                found = true;
                break;
            }
            
            int next_v = -1;
            int r_u = scc_rank[scc[u]];
            
            // Try to find a valid next neighbor
            while(top_state.idx < adj_sorted[u].size()){
                int v = adj_sorted[u][top_state.idx];
                top_state.idx++;
                
                if(!visited[v]){
                    int r_v = scc_rank[scc[v]];
                    bool can_go = false;
                    if(r_v == r_u) {
                        can_go = true;
                    } else if (r_v == r_u + 1) {
                        // Can only move to next SCC if we visited all nodes in current SCC
                        if(current_scc_visited[r_u] == scc_sz_by_rank[r_u]){
                            can_go = true;
                        }
                    }
                    
                    if(can_go){
                        next_v = v;
                        break;
                    }
                }
            }
            
            if(next_v != -1) {
                visited[next_v] = true;
                current_scc_visited[scc_rank[scc[next_v]]]++;
                dfs_stack.push_back({next_v, 0});
                
                // Update best path if this path is longer
                if(dfs_stack.size() > best_path.size()){
                    best_path.clear();
                    for(auto &st : dfs_stack) best_path.push_back(st.u);
                }
            } else {
                // Backtrack
                visited[u] = false;
                current_scc_visited[scc_rank[scc[u]]]--;
                dfs_stack.pop_back();
            }
        }
        
        if(found) {
             best_path.clear();
             for(auto &st : dfs_stack) best_path.push_back(st.u);
             break; 
        }
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    if(!(cin >> n >> m)) return 0;
    for(int i=0; i<10; ++i) cin >> a[i];
    for(int i=0; i<m; ++i){
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
    }
    
    solve();
    
    cout << best_path.size() << "\n";
    for(int i=0; i<best_path.size(); ++i){
        cout << best_path[i] << (i == best_path.size()-1 ? "" : " ");
    }
    cout << "\n";
    
    return 0;
}