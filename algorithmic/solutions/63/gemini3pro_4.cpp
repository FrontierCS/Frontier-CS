#include <iostream>
#include <vector>
#include <algorithm>
#include <queue>
#include <random>

using namespace std;

// Global variables
int N, M;
vector<pair<int, int>> edges;
vector<vector<int>> adj;

// Fixed DFS orientation to ensure strong connectivity within components
vector<int> fixed_orientation; // 0 for U->V, 1 for V->U
vector<int> tin, low;
int timer;
vector<pair<int, int>> dfs_edges; // To help build strong orientation

void dfs_strong(int u, int p = -1) {
    tin[u] = low[u] = ++timer;
    for (int v : adj[u]) {
        if (v == p) continue;
        if (tin[v]) {
            // Back edge
            low[u] = min(low[u], tin[v]);
            // Orient back edge from descendant to ancestor (u -> v)
            // But in our storage edges are U_i, V_i.
            // We need to map (u, v) to edge index.
            // For simplicity, we just store the decision later.
        } else {
            // Tree edge
            dfs_strong(v, u);
            low[u] = min(low[u], low[v]);
            // Orient tree edge parent to child (u -> v)
        }
    }
}

// Map edge pair to index
int get_edge_index(int u, int v) {
    // This is slow if linear scan. Map is better but O(log M).
    // Given constraints and structure, we can precompute a map or just iterate.
    // Since M <= 15000, we can use a sorted list or map.
    // Let's use lower_bound on sorted edges.
    // Actually, simple linear scan is too slow for 600 queries if we do it every time.
    // Better: precompute adjacency with edge indices.
    return -1; // Placeholder
}

struct EdgeInfo {
    int to;
    int id;
};
vector<vector<EdgeInfo>> adj_with_id;

// We need a base orientation that makes components strongly connected.
// Strategy: Tree edges Down, Back edges Up.
// This is a known strong orientation for 2-edge-connected components.
vector<int> base_dir; // 0: U->V, 1: V->U

void precompute_strong_orientation() {
    adj_with_id.assign(N, {});
    for (int i = 0; i < M; ++i) {
        adj_with_id[edges[i].first].push_back({edges[i].second, i});
        adj_with_id[edges[i].second].push_back({edges[i].first, i});
    }

    tin.assign(N, 0);
    low.assign(N, 0);
    timer = 0;
    base_dir.assign(M, 0);
    
    // Run DFS
    vector<int> p(N, -1);
    vector<int> pe(N, -1);
    vector<int> status(N, 0); // 0: new, 1: active, 2: finished
    vector<int> stack;
    stack.push_back(0);
    
    // Iterative DFS to avoid stack overflow
    // But N=10000 recursive is fine.
    // Let's use recursive for simplicity.
}

void dfs_orientation(int u, int p = -1) {
    tin[u] = ++timer;
    for (auto& edge : adj_with_id[u]) {
        int v = edge.to;
        int id = edge.id;
        if (v == p) continue;
        if (tin[v]) {
            if (tin[v] < tin[u]) {
                // Back edge u -> v (upwards)
                // If edge is (U, V) in input:
                // If u=U, v=V: Dir U->V (0)
                // If u=V, v=U: Dir V->U (1)
                if (edges[id].first == u) base_dir[id] = 0;
                else base_dir[id] = 1;
            }
        } else {
            // Tree edge u -> v (downwards)
            if (edges[id].first == u) base_dir[id] = 0;
            else base_dir[id] = 1;
            dfs_orientation(v, u);
        }
    }
}

// Interaction
int query(const vector<int>& dirs) {
    cout << "0";
    for (int d : dirs) cout << " " << d;
    cout << endl;
    int res;
    cin >> res;
    return res;
}

void answer(int u, int v) {
    cout << "1 " << u << " " << v << endl;
    exit(0);
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N >> M)) return 0;

    edges.resize(M);
    adj.resize(N);
    adj_with_id.resize(N);
    for (int i = 0; i < M; ++i) {
        cin >> edges[i].first >> edges[i].second;
        adj[edges[i].first].push_back(edges[i].second);
        adj[edges[i].second].push_back(edges[i].first);
        adj_with_id[edges[i].first].push_back({edges[i].second, i});
        adj_with_id[edges[i].second].push_back({edges[i].first, i});
    }

    // Precompute base strong orientation
    tin.assign(N, 0);
    timer = 0;
    base_dir.resize(M);
    dfs_orientation(0);

    // Try finding split with random roots
    mt19937 rng(1337);
    vector<int> nodes(N);
    for(int i=0; i<N; ++i) nodes[i] = i;
    
    // We will try up to 20 roots
    int roots_to_try = 20;
    int found_split_type = 0; // 0: none, 1: A in S, B in Rest, 2: A in Rest, B in S
    vector<int> S_nodes; // The set S
    
    // Shuffle nodes to pick random roots
    shuffle(nodes.begin(), nodes.end(), rng);

    for (int k = 0; k < min(N, roots_to_try); ++k) {
        int root = nodes[k];
        
        // BFS
        vector<int> dist(N, -1);
        queue<int> q;
        q.push(root);
        dist[root] = 0;
        int max_dist = 0;
        while (!q.empty()) {
            int u = q.front(); q.pop();
            max_dist = max(max_dist, dist[u]);
            for (int v : adj[u]) {
                if (dist[v] == -1) {
                    dist[v] = dist[u] + 1;
                    q.push(v);
                }
            }
        }
        
        // Try random depths
        // We can probe ~10 depths
        vector<int> depths;
        if (max_dist > 0) {
            depths.push_back(max_dist / 2);
            for(int j=0; j<8; ++j) depths.push_back(rng() % max_dist);
            sort(depths.begin(), depths.end());
            depths.erase(unique(depths.begin(), depths.end()), depths.end());
        } else {
            // Graph is single node? N >= 2
            continue; 
        }

        for (int d : depths) {
            // Construct query for cut at depth d
            // S = {u | dist[u] <= d}
            // Cut S -> Rest
            vector<int> q_dirs = base_dir;
            vector<bool> in_S(N, false);
            for(int i=0; i<N; ++i) if (dist[i] <= d) in_S[i] = true;
            
            // Adjust cut edges
            for(int i=0; i<M; ++i) {
                int u = edges[i].first;
                int v = edges[i].second;
                bool u_in = in_S[u];
                bool v_in = in_S[v];
                if (u_in != v_in) {
                    // Cut edge
                    // We want S -> Rest
                    // If u in S, v in Rest: u -> v (0 if u is first)
                    if (u_in) q_dirs[i] = 0;
                    else q_dirs[i] = 1;
                }
            }

            if (query(q_dirs) == 0) {
                // Found split: A in S, B in Rest
                for(int i=0; i<N; ++i) if(in_S[i]) S_nodes.push_back(i);
                found_split_type = 1;
                goto SPLIT_FOUND;
            }

            // Try reverse: Rest -> S
            // If u in S, v in Rest: v -> u (1 if u is first)
            for(int i=0; i<M; ++i) {
                int u = edges[i].first;
                int v = edges[i].second;
                bool u_in = in_S[u];
                bool v_in = in_S[v];
                if (u_in != v_in) {
                    if (u_in) q_dirs[i] = 1;
                    else q_dirs[i] = 0;
                }
            }
            
            if (query(q_dirs) == 0) {
                // Found split: B in S, A in Rest
                for(int i=0; i<N; ++i) if(in_S[i]) S_nodes.push_back(i);
                found_split_type = 2;
                goto SPLIT_FOUND;
            }
        }
    }

    SPLIT_FOUND:;
    
    // If we didn't find split, we can't solve it (probabilistic failure). 
    // However, with 20 roots, failure is minimal.
    
    // Identify S_A and S_B
    // If type 1: A in S, B in Rest
    // If type 2: A in Rest, B in S
    
    vector<int> A_cand, B_cand;
    vector<bool> is_S_node(N, false);
    for(int u : S_nodes) is_S_node[u] = true;
    
    if (found_split_type == 1) {
        A_cand = S_nodes;
        for(int i=0; i<N; ++i) if(!is_S_node[i]) B_cand.push_back(i);
    } else {
        B_cand = S_nodes;
        for(int i=0; i<N; ++i) if(!is_S_node[i]) A_cand.push_back(i);
    }
    
    // Binary search for A
    while (A_cand.size() > 1) {
        int mid = A_cand.size() / 2;
        vector<int> subset;
        for(int i=0; i<mid; ++i) subset.push_back(A_cand[i]);
        
        // Check if A is in subset
        // We know B is in B_cand (disjoint from A_cand)
        // Construct cut: subset -> Rest
        vector<int> q_dirs = base_dir;
        vector<bool> in_subset(N, false);
        for(int u : subset) in_subset[u] = true;
        
        for(int i=0; i<M; ++i) {
            int u = edges[i].first;
            int v = edges[i].second;
            bool u_in = in_subset[u];
            bool v_in = in_subset[v];
            if (u_in != v_in) {
                // subset -> Rest
                if (u_in) q_dirs[i] = 0;
                else q_dirs[i] = 1;
            }
        }
        
        if (query(q_dirs) == 0) {
            // A in subset
            A_cand = subset;
        } else {
            // A not in subset
            vector<int> next_cand;
            for(int i=mid; i<A_cand.size(); ++i) next_cand.push_back(A_cand[i]);
            A_cand = next_cand;
        }
    }
    
    // Binary search for B
    while (B_cand.size() > 1) {
        int mid = B_cand.size() / 2;
        vector<int> subset;
        for(int i=0; i<mid; ++i) subset.push_back(B_cand[i]);
        
        // Check if B is in subset
        // We know A is in A_cand (disjoint from B_cand)
        // Construct cut: Rest -> subset (traps B in subset)
        // Wait. If A is in Rest, B in subset.
        // We want to block A -> B? No.
        // We want to check "Is B in subset?".
        // Query returns 1 if path exists.
        // If B in subset, A in Rest.
        // We want to prevent A -> B if B NOT in subset? No.
        
        // Correct logic:
        // Assume B in subset. Test this.
        // If B in subset, A in Rest.
        // If we block Rest -> subset. Then A cannot reach B. Result 0.
        // If B NOT in subset, then B in (B_cand \ subset).
        // Then B is in Rest relative to cut.
        // Then A (in Rest) can reach B (in Rest). Result 1.
        
        vector<int> q_dirs = base_dir;
        vector<bool> in_subset(N, false);
        for(int u : subset) in_subset[u] = true;
        
        for(int i=0; i<M; ++i) {
            int u = edges[i].first;
            int v = edges[i].second;
            bool u_in = in_subset[u];
            bool v_in = in_subset[v];
            if (u_in != v_in) {
                // Rest -> subset
                // u in Rest, v in subset: u -> v
                if (!u_in) q_dirs[i] = 0;
                else q_dirs[i] = 1;
            }
        }
        
        if (query(q_dirs) == 0) {
            // B in subset
            B_cand = subset;
        } else {
            // B not in subset
            vector<int> next_cand;
            for(int i=mid; i<B_cand.size(); ++i) next_cand.push_back(B_cand[i]);
            B_cand = next_cand;
        }
    }
    
    answer(A_cand[0], B_cand[0]);

    return 0;
}