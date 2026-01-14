#include <iostream>
#include <vector>
#include <algorithm>
#include <random>
#include <bitset>

using namespace std;

struct Edge {
    int u, v;
    int id;
};

int N, M;
vector<Edge> edges;
vector<vector<pair<int, int>>> adj; // u -> {v, edge_index}

// Global bitsets for solver
bitset<10000> current_mask;
bitset<10000> possible_v;
bitset<10000> all_ones;

struct QueryData {
    vector<int> in;
    vector<int> out;
    vector<int> node_at_dfs_order; // map dfs_index -> original_node
    int result;
};

vector<QueryData> queries;

void build_random_dfs(int root, vector<int>& p, vector<int>& order, vector<int>& in, vector<int>& out, mt19937& rng) {
    // Randomized DFS
    vector<int> stack;
    stack.push_back(root);
    
    vector<bool> visited(N, false);
    visited[root] = true;
    
    int timer = 0;
    
    // Iterative DFS to avoid stack overflow and easier control
    // To handle in/out times properly in iterative DFS, we need to handle "finish" time
    // We can simulate call stack
    struct Frame {
        int u;
        int edge_idx; // index in shuffled adj list
    };
    vector<Frame> call_stack;
    
    // Pre-shuffle adjacencies
    vector<vector<int>> my_adj(N);
    for(int u=0; u<N; ++u) {
        for(auto& p : adj[u]) my_adj[u].push_back(p.first);
        shuffle(my_adj[u].begin(), my_adj[u].end(), rng);
    }
    
    call_stack.push_back({root, 0});
    visited[root] = true;
    in[root] = timer++;
    order[in[root]] = root;
    
    while(!call_stack.empty()) {
        Frame& f = call_stack.back();
        int u = f.u;
        
        if (f.edge_idx < my_adj[u].size()) {
            int v = my_adj[u][f.edge_idx];
            f.edge_idx++;
            if (!visited[v]) {
                visited[v] = true;
                in[v] = timer++;
                order[in[v]] = v;
                call_stack.push_back({v, 0});
            }
        } else {
            out[u] = timer - 1; // inclusive
            call_stack.pop_back();
        }
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N >> M)) return 0;

    adj.resize(N);
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        edges.push_back({u, v, i});
        adj[u].push_back({v, i});
        adj[v].push_back({u, i});
    }

    mt19937 rng(1337);
    
    // Initialize bitset
    for(int i=0; i<N; ++i) all_ones[i] = 1;

    // We can ask up to 600 queries.
    // Each random DFS tree gives a constraint.
    // Try 250 queries.
    int num_queries = 250;
    // Safety check for small N? No, N>=2.
    
    vector<int> direction(M); // 0 for u->v, 1 for v->u
    vector<int> in(N), out(N), order(N);
    
    for (int q = 0; q < num_queries; ++q) {
        // Pick random root
        int root = uniform_int_distribution<int>(0, N - 1)(rng);
        
        // Build DFS tree
        fill(in.begin(), in.end(), 0);
        fill(out.begin(), out.end(), 0);
        fill(order.begin(), order.end(), 0);
        
        build_random_dfs(root, vector<int>(), order, in, out, rng);
        
        // Determine edge directions
        // We want all edges to go Ancestor -> Descendant
        // In DFS tree, u is ancestor of v iff in[u] <= in[v] && out[u] >= out[v]
        // This covers tree edges and back edges (which go Desc -> Anc in undirected sense, but we direct Anc -> Desc)
        // Simply: u -> v if in[u] < in[v]. (Since no cross edges in DFS)
        
        for (const auto& e : edges) {
            // Direction 0: U->V, 1: V->U
            if (in[e.u] < in[e.v]) {
                // u is ancestor (or 'above') v
                // Direct u -> v => direction 0
                direction[e.id] = 0;
            } else {
                // v is ancestor u
                // Direct v -> u => direction 1
                direction[e.id] = 1;
            }
        }
        
        // Output query
        cout << "0 ";
        for (int i = 0; i < M; ++i) {
            cout << direction[i] << (i == M - 1 ? "" : " ");
        }
        cout << endl;
        
        int res;
        cin >> res;
        if (res == -1) exit(0); // Error
        
        QueryData qd;
        qd.in = in;
        qd.out = out;
        qd.node_at_dfs_order = order;
        qd.result = res;
        queries.push_back(qd);
    }
    
    // Solver
    int ansA = -1, ansB = -1;
    
    for (int u = 0; u < N; ++u) {
        possible_v = all_ones;
        possible_v[u] = 0; // A != B
        
        bool possible = true;
        
        for (const auto& qd : queries) {
            // Construct mask of subtree of u
            // Subtree is range [in[u], out[u]] in dfs order
            // We need to map this range to original indices to AND with possible_v
            // Since N is 10000, O(N) per query is fine. N*Q*N is 10^4 * 250 * 10^4 = 2.5 * 10^10 -> too slow!
            // Wait. bitset operations are fast.
            // But constructing the mask naively is O(N). 
            // Total operations: N (candidates) * Q (queries) * (N/64 bitset + N construction).
            // N construction is the bottleneck.
            // 10000 * 250 * 10000 = 2.5 * 10^10 ops is too slow for 2 seconds.
            
            // Optimization:
            // Check only if current candidate set is not empty.
            // Also, instead of full bitset construction:
            // if res == 1: B MUST be in subtree.
            // if res == 0: B MUST NOT be in subtree.
            
            // We can iterate over current candidates v in possible_v.
            // For each v, check condition. If fail, remove v.
            // Initially possible_v has N bits.
            // In first few queries, it will drop quickly.
            // So complexity is Sum over queries of (size of possible_v).
            // This is much faster.
            
            int u_in = qd.in[u];
            int u_out = qd.out[u];
            bool in_subtree_req = (qd.result == 1);
            
            // Iterate set bits
            for (int v = possible_v._Find_first(); v < N; v = possible_v._Find_next(v)) {
                int v_in = qd.in[v];
                bool is_in_subtree = (v_in >= u_in && v_in <= u_out);
                
                if (in_subtree_req != is_in_subtree) {
                    possible_v[v] = 0;
                }
            }
            
            if (possible_v.none()) {
                possible = false;
                break;
            }
        }
        
        if (possible) {
            // Found A=u. Is B unique?
            // With 250 queries it should be.
            // Pick the first one.
            ansA = u;
            ansB = possible_v._Find_first();
            break;
        }
    }
    
    cout << "1 " << ansA << " " << ansB << endl;
    
    return 0;
}