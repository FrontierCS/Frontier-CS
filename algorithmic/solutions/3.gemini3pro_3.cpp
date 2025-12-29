#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>
#include <map>

using namespace std;

// Fast IO
void fast_io() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
}

// Wrapper for the query function
// Submits a batch of operations and returns the results
vector<int> query(const vector<int>& ops) {
    if (ops.empty()) return {};
    cout << ops.size();
    for (int x : ops) cout << " " << x;
    cout << endl;
    
    vector<int> res(ops.size());
    for (int i = 0; i < ops.size(); ++i) {
        cin >> res[i];
    }
    return res;
}

int main() {
    fast_io();
    int subtask, n;
    if (!(cin >> subtask >> n)) return 0;

    // Build Independent Set Layers
    // We peel off Independent Sets iteratively.
    // 5 layers are sufficient for N=10^5 to decompose the cycle.
    // If any nodes remain, they form the last layer.
    
    vector<int> p(n);
    iota(p.begin(), p.end(), 1);
    
    mt19937 rng(1337);
    shuffle(p.begin(), p.end(), rng);
    
    vector<int> remaining = p;
    vector<vector<int>> layers;
    
    for (int k = 0; k < 5 && !remaining.empty(); ++k) {
        // Op sequence: simply add all remaining nodes in order
        // The system returns 1 if conflict exists with prefix
        // Nodes with result 0 form an Independent Set within the prefix
        vector<int> ops = remaining;
        vector<int> res = query(ops);
        
        vector<int> layer, next_rem;
        for (int i = 0; i < remaining.size(); ++i) {
            if (res[i] == 0) {
                layer.push_back(remaining[i]);
            } else {
                next_rem.push_back(remaining[i]);
            }
        }
        layers.push_back(layer);
        remaining = next_rem;
    }
    if (!remaining.empty()) {
        layers.push_back(remaining);
    }
    
    int num_layers = layers.size();
    
    // Map nodes to local indices within their layer for bit queries
    vector<int> local_idx(n + 1);
    vector<int> layer_id(n + 1);
    for (int i = 0; i < num_layers; ++i) {
        for (int j = 0; j < layers[i].size(); ++j) {
            int u = layers[i][j];
            local_idx[u] = j;
            layer_id[u] = i;
        }
    }
    
    // Store bit query results
    // node_data[u][target_layer] = {mask0, mask1}
    vector<map<int, pair<int, int>>> node_data(n + 1);

    // Perform bit queries (0..15)
    // We batch queries to minimize calls
    // Split 16 bits into 2 batches to avoid hitting 10^7 op limit per query (safety)
    for (int batch = 0; batch < 2; ++batch) {
        vector<int> batch_ops;
        struct Rec {
            int u;
            int target_layer;
            int bit;
            int val;
            int res_idx;
        };
        vector<Rec> records;
        
        int start_bit = batch * 8;
        int end_bit = min((batch + 1) * 8, 16);
        
        for (int b = start_bit; b < end_bit; ++b) {
            for (int i = 0; i < num_layers; ++i) {
                for (int j = 0; j < num_layers; ++j) {
                    if (i == j) continue;
                    
                    for (int val = 0; val <= 1; ++val) {
                        vector<int> mask;
                        for (int v : layers[j]) {
                            if (((local_idx[v] >> b) & 1) == val) {
                                mask.push_back(v);
                            }
                        }
                        if (mask.empty()) continue;
                        
                        // Add Mask
                        batch_ops.insert(batch_ops.end(), mask.begin(), mask.end());
                        int current_op_idx = batch_ops.size(); // index of next op
                        
                        // Probe layer i
                        for (int u : layers[i]) {
                            batch_ops.push_back(u); // Add u (check)
                            records.push_back({u, j, b, val, current_op_idx});
                            current_op_idx++;
                            
                            batch_ops.push_back(u); // Remove u
                            current_op_idx++;
                        }
                        
                        // Remove Mask
                        batch_ops.insert(batch_ops.end(), mask.begin(), mask.end());
                    }
                }
            }
        }
        
        vector<int> res = query(batch_ops);
        
        for (const auto& r : records) {
            // If res is 1, it means u connects to the mask
            if (res[r.res_idx] == 1) {
                if (r.val == 0) node_data[r.u][r.target_layer].first |= (1 << r.bit);
                else node_data[r.u][r.target_layer].second |= (1 << r.bit);
            }
        }
    }
    
    // Reconstruct Graph
    vector<vector<int>> adj(n + 1);
    
    // Structure for Degree 2 candidates
    struct Candidate {
        int u;
        int diff;
        int common;
        int target_layer;
    };
    vector<Candidate> cands;
    
    for (int u = 1; u <= n; ++u) {
        for (auto& entry : node_data[u]) {
            int lay = entry.first;
            int m0 = entry.second.first;
            int m1 = entry.second.second;
            
            // If neighbors exist in this layer
            if (m0 == 0 && m1 == 0) continue; 
            
            int diff = m0 & m1;
            int common = m1 & (~m0);
            
            if (diff == 0) {
                // Unique neighbor identified (Degree 1 or Degree 2 with same bits - impossible)
                int idx = common;
                if (idx < layers[lay].size()) {
                    int v = layers[lay][idx];
                    adj[u].push_back(v);
                    adj[v].push_back(u);
                }
            } else {
                // Ambiguous (Degree 2 with differing bits)
                cands.push_back({u, diff, common, lay});
            }
        }
    }
    
    // Resolve candidates by checking mutual consistency
    for (const auto& c : cands) {
        int u = c.u;
        // Brute force check potential neighbors in target layer
        // Optimization: In a cycle, these cases are rare or layer sizes small enough
        for (int v : layers[c.target_layer]) {
            int v_idx = local_idx[v];
            
            // Condition 1: v matches u's mask
            if ((v_idx & ~c.diff) == c.common) {
                // Check Condition 2: u matches v's mask
                int u_layer = layer_id[u];
                if (node_data[v].count(u_layer)) {
                    int vm0 = node_data[v][u_layer].first;
                    int vm1 = node_data[v][u_layer].second;
                    int v_diff = vm0 & vm1;
                    int v_common = vm1 & (~vm0);
                    
                    int u_idx_val = local_idx[u];
                    if ((u_idx_val & ~v_diff) == v_common) {
                        adj[u].push_back(v);
                        adj[v].push_back(u);
                    }
                }
            }
        }
    }
    
    // Finalize Graph and Extract Cycle
    for (int i = 1; i <= n; ++i) {
        sort(adj[i].begin(), adj[i].end());
        adj[i].erase(unique(adj[i].begin(), adj[i].end()), adj[i].end());
    }
    
    vector<int> ans;
    vector<bool> visited(n + 1, false);
    int curr = 1;
    
    // Find a starting point with edges (all should have 2, but robust start)
    for(int i=1; i<=n; ++i) if(adj[i].size() > 0) { curr = i; break; }
    
    // Traverse
    for (int i = 0; i < n; ++i) {
        ans.push_back(curr);
        visited[curr] = true;
        int next = -1;
        for (int v : adj[curr]) {
            if (!visited[v]) {
                next = v;
                break;
            }
        }
        if (next == -1 && i < n - 1) {
             // Should only happen for the last edge back to start, 
             // but if graph is disconnected or error, handle gracefully?
             // Assuming connected cycle as per problem.
             // If we are at last node, neighbors are visited.
        } else {
            curr = next;
        }
    }
    
    cout << "-1";
    for (int x : ans) cout << " " << x;
    cout << endl;
    
    return 0;
}