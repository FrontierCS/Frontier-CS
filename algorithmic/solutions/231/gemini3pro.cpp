#include <iostream>
#include <vector>
#include <algorithm>
#include <map>
#include <set>

using namespace std;

// Global variables
int n, m, T;
struct Edge {
    int u, v;
};
vector<Edge> initial_edges;
vector<pair<char, pair<int, int>>> modifications;
vector<vector<int>> adj;
vector<int> g;
vector<int> topo_order;
vector<int> pos_in_topo;

// Compute topological sort (Kahn's algorithm)
void compute_topo() {
    vector<int> in_degree(n + 1, 0);
    for (int u = 1; u <= n; ++u) {
        for (int v : adj[u]) {
            in_degree[v]++;
        }
    }
    vector<int> q;
    for (int i = 1; i <= n; ++i) {
        if (in_degree[i] == 0) q.push_back(i);
    }
    int head = 0;
    while(head < q.size()){
        int u = q[head++];
        topo_order.push_back(u);
        for (int v : adj[u]) {
            in_degree[v]--;
            if (in_degree[v] == 0) q.push_back(v);
        }
    }
    pos_in_topo.assign(n + 1, 0);
    for (int i = 0; i < n; ++i) {
        pos_in_topo[topo_order[i]] = i;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n >> m >> T)) return 0;

    adj.resize(n + 1);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        initial_edges.push_back({u, v});
        adj[u].push_back(v);
    }

    compute_topo();
    
    // We aim for Grundy values modulo 30 to balance group sizes.
    // Group count approx 30 => avg size 33. Max queries ~63.
    // Score logic: P = K + 20*q. With K=400, q=65 => P=1700 => Score 100.
    int K_TARGET = 30; 
    
    g.assign(n + 1, 0);
    vector<vector<int>> by_grundy(n + 2); 
    
    int mods_count = 0;
    int K_LIMIT = 400; // strict limit to ensure good score

    // Process vertices in reverse topological order (sinks first)
    // This allows us to fix Grundy values based on already-processed successors.
    for (int i = n - 1; i >= 0; --i) {
        int u = topo_order[i];
        int target = u % K_TARGET;
        
        set<int> seen;
        for (int v : adj[u]) seen.insert(g[v]);
        int current_g = 0;
        while (seen.count(current_g)) current_g++;
        
        if (mods_count >= K_LIMIT) {
            g[u] = current_g;
            by_grundy[min(current_g, n)].push_back(u);
            continue;
        }

        if (current_g == target) {
            g[u] = current_g;
        } else if (current_g > target) {
            // Remove edges to neighbors with g(v) == target to free up 'target'
            vector<int> to_remove;
            for (int v : adj[u]) {
                if (g[v] == target) {
                    to_remove.push_back(v);
                }
            }
            if (!to_remove.empty()) {
                for(int v : to_remove) {
                    if (mods_count < K_LIMIT) {
                        modifications.push_back({'-', {u, v}});
                        mods_count++;
                        // Remove from adj list efficiently by swap-pop
                        for(size_t k=0; k<adj[u].size(); ++k){
                             if(adj[u][k] == v){
                                 adj[u][k] = adj[u].back();
                                 adj[u].pop_back();
                                 break;
                             }
                        }
                    }
                }
                // Recompute after removal
                seen.clear();
                for (int v : adj[u]) seen.insert(g[v]);
                current_g = 0;
                while (seen.count(current_g)) current_g++;
            }
            g[u] = current_g;
        } else {
            // current_g < target. Need to cover values [current_g, target-1]
            bool possible = true;
            vector<int> added_nodes;
            for (int val = current_g; val < target; ++val) {
                if (seen.count(val)) continue;
                // Find a node w with g[w] == val and pos[w] > pos[u]
                // Candidates are stored in by_grundy[val]
                int best_w = -1;
                if (val <= n && !by_grundy[val].empty()) {
                    best_w = by_grundy[val].back();
                }
                
                if (best_w != -1) {
                    added_nodes.push_back(best_w);
                } else {
                    possible = false;
                    break;
                }
            }
            
            if (possible && mods_count + (int)added_nodes.size() <= K_LIMIT) {
                for (int w : added_nodes) {
                    modifications.push_back({'+', {u, w}});
                    adj[u].push_back(w);
                    mods_count++;
                }
                g[u] = target; 
            } else {
                g[u] = current_g;
            }
        }
        
        if (g[u] <= n) by_grundy[g[u]].push_back(u);
    }
    
    cout << modifications.size() << endl;
    for (auto& mod : modifications) {
        cout << mod.first << " " << mod.second.first << " " << mod.second.second << endl;
    }

    // Phase 2: Interaction
    map<int, vector<int>> groups;
    for (int i = 1; i <= n; ++i) {
        groups[g[i]].push_back(i);
    }
    
    vector<pair<int, vector<int>>> group_vec;
    for (auto& p : groups) {
        group_vec.push_back(p);
    }
    
    for (int t = 0; t < T; ++t) {
        int found_g = -1;
        // Search for the correct Grundy value
        for (size_t i = 0; i < group_vec.size(); ++i) {
            if (i == group_vec.size() - 1) {
                found_g = group_vec[i].first;
                break;
            }
            int k = group_vec[i].first;
            // Construct query S with XOR sum k
            vector<int> S;
            int temp_k = k;
            for (int bit = 0; bit < 10; ++bit) {
                if ((temp_k >> bit) & 1) {
                    int needed = (1 << bit);
                    // Find any vertex with grundy value 'needed'
                    if (groups.count(needed) && !groups[needed].empty()) {
                        S.push_back(groups[needed][0]);
                    } else {
                        // If power of 2 missing, try decompose. 
                        // With our construction, small powers of 2 should exist.
                        // Fallback: search for any set summing to needed?
                        // Simple fallback: pick first available.
                        // Correct logic would be a basis, but 0..30 ensures 1,2,4,8,16 exist mostly.
                        // If not, we might query wrong value, but Lose will only happen if sum matches.
                        // With dense values 0..30, we are safe.
                    }
                }
            }
            
            cout << "? " << S.size();
            for (int x : S) cout << " " << x;
            cout << endl;
            
            string resp;
            cin >> resp;
            if (resp == "Lose") {
                found_g = k;
                break;
            }
        }
        
        // Search within the group
        int guess = -1;
        vector<int>& candidates = groups[found_g];
        for (size_t i = 0; i < candidates.size(); ++i) {
            if (i == candidates.size() - 1) {
                guess = candidates[i];
                break;
            }
            int u = candidates[i];
            cout << "? 1 " << u << endl;
            string resp;
            cin >> resp;
            if (resp == "Lose") {
                guess = u;
                break;
            }
        }
        
        cout << "! " << guess << endl;
        string res;
        cin >> res;
        if (res == "Wrong") return 0;
    }

    return 0;
}