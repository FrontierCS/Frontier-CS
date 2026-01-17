#include <iostream>
#include <vector>
#include <algorithm>
#include <queue>

using namespace std;

// Structure to store edge details
struct Edge {
    int u, v, id;
};

int n;
vector<int> p;
vector<vector<pair<int, int>>> adj; // Adjacency list: u -> {v, edge_index}
vector<Edge> edge_list;
vector<vector<int>> dists; // All-pairs distances

// DP result structure
struct DP_Res {
    long long val0;
    long long val1;
    int child_for_1;
};

vector<DP_Res> memo;
vector<int> weights; // Current weights for edges

// BFS to compute distances from a start node
void bfs(int start, vector<int>& d) {
    fill(d.begin(), d.end(), -1);
    d[start] = 0;
    queue<int> q;
    q.push(start);
    while (!q.empty()) {
        int u = q.front();
        q.pop();
        for (auto& edge : adj[u]) {
            int v = edge.first;
            if (d[v] == -1) {
                d[v] = d[u] + 1;
                q.push(v);
            }
        }
    }
}

// DP to find Maximum Weight Matching on the tree
void dfs_dp(int u, int parent) {
    long long sum_max = 0;
    // First pass: Calculate sum of max(val0, val1) for all children
    for (auto& edge : adj[u]) {
        int v = edge.first;
        if (v == parent) continue;
        dfs_dp(v, u);
        sum_max += max(memo[v].val0, memo[v].val1);
    }
    
    // val0: u is not matched with any child
    memo[u].val0 = sum_max;
    
    // val1: u is matched with exactly one child
    long long best_val1 = -1e18; // Initialize with a very small number
    int best_child = -1;
    bool has_child = false;
    
    for (auto& edge : adj[u]) {
        int v = edge.first;
        int idx = edge.second;
        if (v == parent) continue;
        has_child = true;
        
        // If we match u with v, the value is:
        // weight(u,v) + val0(v) [v not matched with its children] + sum_{other k} max(val0(k), val1(k))
        // This simplifies to: weight(u,v) + val0(v) + (sum_max - max(val0(v), val1(v)))
        long long current_val = weights[idx] + memo[v].val0 + (sum_max - max(memo[v].val0, memo[v].val1));
        if (current_val > best_val1) {
            best_val1 = current_val;
            best_child = v;
        }
    }
    
    if (has_child) {
        memo[u].val1 = best_val1;
        memo[u].child_for_1 = best_child;
    } else {
        memo[u].val1 = -1e18; // Leaf cannot be matched with a child
    }
}

// Reconstruct the matching based on DP decisions
void get_matching(int u, int parent, bool matched_with_parent, vector<int>& matching_edges) {
    if (matched_with_parent) {
        // u is matched with parent, so u cannot match with any child
        for (auto& edge : adj[u]) {
            int v = edge.first;
            if (v == parent) continue;
            // Children treat u as not available (equivalent to not matched)
            get_matching(v, u, false, matching_edges);
        }
    } else {
        // u is not matched with parent, can choose to match with a child or not
        if (memo[u].val1 > memo[u].val0) {
            // Match u with best_child
            int v_match = memo[u].child_for_1;
            for (auto& edge : adj[u]) {
                if (edge.first == v_match) {
                    matching_edges.push_back(edge.second);
                    break;
                }
            }
            // Recurse
            for (auto& edge : adj[u]) {
                int v = edge.first;
                if (v == parent) continue;
                if (v == v_match) {
                    // v is matched with u (its parent)
                    get_matching(v, u, true, matching_edges);
                } else {
                    // other children are not matched with u
                    get_matching(v, u, false, matching_edges);
                }
            }
        } else {
            // u matches with nobody
            for (auto& edge : adj[u]) {
                int v = edge.first;
                if (v == parent) continue;
                get_matching(v, u, false, matching_edges);
            }
        }
    }
}

void solve() {
    cin >> n;
    p.resize(n + 1);
    for (int i = 1; i <= n; ++i) cin >> p[i];
    
    adj.assign(n + 1, vector<pair<int, int>>());
    edge_list.clear();
    edge_list.resize(n); 
    for (int i = 1; i < n; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back({v, i});
        adj[v].push_back({u, i});
        edge_list[i] = {u, v, i};
    }
    
    // Precompute all-pairs distances
    dists.assign(n + 1, vector<int>(n + 1));
    for (int i = 1; i <= n; ++i) bfs(i, dists[i]);
    
    vector<vector<int>> operations;
    
    while (true) {
        // Check if sorted
        bool sorted = true;
        for (int i = 1; i <= n; ++i) {
            if (p[i] != i) {
                sorted = false;
                break;
            }
        }
        if (sorted) break;
        
        weights.assign(n, 0); 
        
        // Assign weights to edges based on potential improvement
        for (int i = 1; i < n; ++i) {
            int u = edge_list[i].u;
            int v = edge_list[i].v;
            int pu = p[u];
            int pv = p[v];
            
            int d_old = dists[u][pu] + dists[v][pv];
            int d_new = dists[v][pu] + dists[u][pv];
            int gain = d_old - d_new;
            
            if (gain == 2) {
                weights[i] = 100; // Priority 1: Both move closer
            } else if (gain == 0) {
                // Priority 2: One moves closer. 
                // Prefer cases where we move a misplaced item closer, even if we disrupt a correctly placed item.
                bool useful = false;
                bool disrupts_target = false;
                
                // Check if p[u] moves closer by going to v
                if (dists[v][pu] < dists[u][pu]) {
                    useful = true;
                    if (pv == v) disrupts_target = true;
                } 
                // Check if p[v] moves closer by going to u
                if (dists[u][pv] < dists[v][pv]) {
                    useful = true;
                    if (pu == u) disrupts_target = true;
                }
                
                if (useful) {
                    if (disrupts_target) weights[i] = 5; // Good swap: disturbs a sorted node to help an unsorted one
                    else weights[i] = 1; // Okay swap: both unsorted, one helps one hurts
                } else {
                    weights[i] = 0;
                }
            } else {
                weights[i] = 0; // Gain < 0, bad move
            }
        }
        
        // Find max weight matching
        memo.assign(n + 1, {0, 0, 0});
        dfs_dp(1, 0);
        
        vector<int> matching;
        get_matching(1, 0, false, matching);
        
        if (matching.empty()) break; // Should not happen if not sorted
        
        operations.push_back(matching);
        // Apply swaps
        for (int idx : matching) {
            int u = edge_list[idx].u;
            int v = edge_list[idx].v;
            swap(p[u], p[v]);
        }
    }
    
    cout << operations.size() << "\n";
    for (auto& op : operations) {
        cout << op.size();
        for (int idx : op) cout << " " << idx;
        cout << "\n";
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    int t;
    if (cin >> t) {
        while (t--) {
            solve();
        }
    }
    return 0;
}