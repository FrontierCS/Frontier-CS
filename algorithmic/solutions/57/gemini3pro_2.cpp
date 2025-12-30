#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <cmath>
#include <map>

using namespace std;

int n;
vector<vector<int>> adj;
vector<long long> F;
vector<int> toggled;

// Helper to query F values
long long query_type_1(const vector<int>& nodes) {
    cout << "? 1 " << nodes.size();
    for (int u : nodes) cout << " " << u;
    cout << endl;
    long long res;
    cin >> res;
    return res;
}

// Helper to toggle
void query_type_2(int u) {
    cout << "? 2 " << u << endl;
    // No response to read
}

// Compute component sizes and mapping for a splitter u
// Returns:
// map_node_to_comp: for each v, which component of T\{u} it belongs to. -1 if v==u.
// comp_sizes: size of each component
// parent_in_comp: for each component, which neighbor of u leads to it (to find parent)
void analyze_splitter(int u, vector<int>& map_node_to_comp, vector<int>& comp_sizes, vector<int>& neighbor_leading_to_comp) {
    map_node_to_comp.assign(n + 1, -1);
    comp_sizes.clear();
    neighbor_leading_to_comp.clear();
    
    int comp_id = 0;
    for (int v : adj[u]) {
        if (map_node_to_comp[v] == -1) {
            // New component
            neighbor_leading_to_comp.push_back(v);
            int size = 0;
            vector<int> q;
            q.push_back(v);
            map_node_to_comp[v] = comp_id;
            size++;
            
            int head = 0;
            while(head < q.size()){
                int curr = q[head++];
                for (int nxt : adj[curr]) {
                    if (nxt != u && map_node_to_comp[nxt] == -1) {
                        map_node_to_comp[nxt] = comp_id;
                        q.push_back(nxt);
                        size++;
                    }
                }
            }
            comp_sizes.push_back(size);
            comp_id++;
        }
    }
}

void solve() {
    cin >> n;
    adj.assign(n + 1, vector<int>());
    for (int i = 0; i < n - 1; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    // Step 1: Query all F[u]
    // This takes N queries.
    F.resize(n);
    for (int i = 1; i <= n; ++i) {
        F[i - 1] = query_type_1({i});
    }

    // Identify candidates
    vector<int> candidates;
    for (int i = 1; i <= n; ++i) {
        if (abs(F[i - 1]) == 1) {
            candidates.push_back(i);
        }
    }

    toggled.assign(n + 1, 0);
    long long current_global_sum = 0;
    for (long long x : F) current_global_sum += x;

    // Disambiguation loop
    // We try to filter candidates by performing extra queries.
    // Each step uses 2 queries: one toggle and one global sum check.
    while (candidates.size() > 1) {
        int best_u = -1;
        int min_max_group = 1e9;

        // Try all nodes as splitter to find the one that best separates the candidates
        // "Best" means minimizing the maximum group size of candidates that yield the same Delta S.
        for (int u = 1; u <= n; ++u) {
            vector<int> map_node_to_comp;
            vector<int> comp_sizes;
            vector<int> neighbor_leads;
            analyze_splitter(u, map_node_to_comp, comp_sizes, neighbor_leads);

            map<long long, int> group_counts;
            int max_grp = 0;

            for (int r : candidates) {
                long long delta = 0;
                int val_u_initial = 0;
                int subtree_size = 0;

                // Determine val_u_initial assuming root r
                // and subtree size of u assuming root r
                if (r == u) {
                    val_u_initial = F[u - 1]; // val(root) = f(root)
                    subtree_size = n;
                } else {
                    int c_id = map_node_to_comp[r];
                    // parent of u is the neighbor leading to r
                    int p = neighbor_leads[c_id];
                    val_u_initial = F[u - 1] - F[p - 1];
                    // Subtree of u is V \ Component_containing_r
                    subtree_size = n - comp_sizes[c_id];
                }

                // Current value accounts for previous toggles
                // If toggled[u] is 1, value is inverted relative to initial
                int current_val_u = val_u_initial * (toggled[u] ? -1 : 1);
                delta = -2LL * current_val_u * subtree_size;
                
                group_counts[delta]++;
                if (group_counts[delta] > max_grp) max_grp = group_counts[delta];
            }

            if (max_grp < min_max_group) {
                min_max_group = max_grp;
                best_u = u;
            }
        }

        if (min_max_group == candidates.size()) {
            // Cannot distinguish remaining candidates. 
            // This implies they produce identical observable behavior (and likely identical values).
            break; 
        }

        // Perform toggle
        query_type_2(best_u);
        toggled[best_u] ^= 1;
        
        // Query global sum
        vector<int> all_nodes(n);
        iota(all_nodes.begin(), all_nodes.end(), 1);
        long long new_sum = query_type_1(all_nodes);
        long long observed_delta = new_sum - current_global_sum;
        current_global_sum = new_sum;

        // Filter candidates
        vector<int> next_candidates;
        
        // Re-analyze for best_u to filter
        vector<int> map_node_to_comp;
        vector<int> comp_sizes;
        vector<int> neighbor_leads;
        analyze_splitter(best_u, map_node_to_comp, comp_sizes, neighbor_leads);

        for (int r : candidates) {
            int val_u_initial = 0;
            int subtree_size = 0;
            if (r == best_u) {
                val_u_initial = F[best_u - 1];
                subtree_size = n;
            } else {
                int c_id = map_node_to_comp[r];
                int p = neighbor_leads[c_id];
                val_u_initial = F[best_u - 1] - F[p - 1];
                subtree_size = n - comp_sizes[c_id];
            }
            
            // IMPORTANT: use PRE-TOGGLE state for prediction
            // The toggled array was updated, so previous state is toggled[best_u] ^ 1
            int prev_toggled = toggled[best_u] ^ 1;
            int current_val_u = val_u_initial * (prev_toggled ? -1 : 1);
            long long pred_delta = -2LL * current_val_u * subtree_size;

            if (pred_delta == observed_delta) {
                next_candidates.push_back(r);
            }
        }
        candidates = next_candidates;
    }

    // Output answer based on the first remaining candidate
    int r = candidates[0];
    
    // Build tree from r to compute parents
    vector<int> parent(n + 1, 0);
    vector<int> q;
    q.push_back(r);
    vector<bool> visited(n + 1, false);
    visited[r] = true;
    int head = 0;
    while(head < q.size()){
        int u = q[head++];
        for(int v : adj[u]){
            if(!visited[v]){
                visited[v] = true;
                parent[v] = u;
                q.push_back(v);
            }
        }
    }

    cout << "!";
    for (int i = 1; i <= n; ++i) {
        int initial_val;
        if (i == r) initial_val = F[i - 1];
        else initial_val = F[i - 1] - F[parent[i] - 1];
        
        int final_val = initial_val * (toggled[i] ? -1 : 1);
        cout << " " << final_val;
    }
    cout << endl;
}

int main() {
    ios_base::sync_with_stdio(false); // Can be used with interactive problems if flushes are correct
    // However, cout << endl flushes automatically. 
    int t;
    if (cin >> t) {
        while (t--) {
            solve();
        }
    }
    return 0;
}