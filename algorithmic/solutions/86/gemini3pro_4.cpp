#include <iostream>
#include <vector>
#include <algorithm>
#include <numeric>
#include <random>

using namespace std;

int N;
vector<vector<int>> adj;

// Helper to ask query
int ask(int u, int v, int w) {
    cout << "0 " << u << " " << v << " " << w << endl;
    int res;
    cin >> res;
    return res;
}

// DFS to compute subtree sizes and collect nodes in the current component
void get_subtree_sizes(int u, int p, vector<int>& sz, vector<int>& nodes) {
    sz[u] = 1;
    nodes.push_back(u);
    for (int v : adj[u]) {
        if (v != p) {
            get_subtree_sizes(v, u, sz, nodes);
            sz[u] += sz[v];
        }
    }
}

// Find centroid of the component
int get_centroid(int u, int p, int total_nodes, const vector<int>& sz) {
    for (int v : adj[u]) {
        if (v != p && sz[v] > total_nodes / 2) {
            return get_centroid(v, u, total_nodes, sz);
        }
    }
    return u;
}

// Helper to get any leaf in the subtree rooted at u (blocking p)
int get_any_leaf(int u, int p) {
    bool is_leaf = true;
    for (int v : adj[u]) {
        if (v != p) {
            is_leaf = false;
            return get_any_leaf(v, u);
        }
    }
    return u;
}

// DFS to check if target is in the subtree of curr (blocking par)
bool contains_node(int curr, int par, int target) {
    if (curr == target) return true;
    for (int nx : adj[curr]) {
        if (nx != par) {
            if (contains_node(nx, curr, target)) return true;
        }
    }
    return false;
}

// Helper to compute size of subtree
int compute_size(int u, int p) {
    int s = 1;
    for (int v : adj[u]) {
        if (v != p) s += compute_size(v, u);
    }
    return s;
}

void insert_node(int k, int start_node) {
    struct Frame {
        int u;
        int p; 
    };
    
    vector<Frame> stack;
    stack.push_back({start_node, 0});
    
    while (!stack.empty()) {
        Frame fr = stack.back();
        stack.pop_back();
        int u = fr.u;
        int p = fr.p;
        
        vector<int> sz(N + 1, 0);
        vector<int> nodes;
        get_subtree_sizes(u, p, sz, nodes);
        int total = sz[u];
        int C = get_centroid(u, p, total, sz);
        
        struct Component {
            int neighbor;
            int size;
            int leaf;
        };
        vector<Component> comps;
        
        // Map nodes to bool for quick check
        vector<bool> in_comp(N + 1, false);
        for(int x : nodes) in_comp[x] = true;
        
        for (int v : adj[C]) {
            if (in_comp[v]) {
                int s = compute_size(v, C);
                int lf = get_any_leaf(v, C);
                comps.push_back({v, s, lf});
            }
        }
        
        sort(comps.begin(), comps.end(), [](const Component& a, const Component& b){
            return a.size > b.size;
        });
        
        int found_idx = -1;
        vector<int> active_indices(comps.size());
        iota(active_indices.begin(), active_indices.end(), 0);
        
        while (active_indices.size() >= 2) {
            int idx_a = active_indices[0];
            int idx_b = active_indices[1];
            active_indices.erase(active_indices.begin());
            active_indices.erase(active_indices.begin()); 
            
            int la = comps[idx_a].leaf;
            int lb = comps[idx_b].leaf;
            
            int res = ask(la, lb, k);
            
            if (res == C) {
                // k is not in A and not in B
                continue;
            } else if (res == k) {
                // k is on path between la and lb
                int res2 = ask(la, C, k);
                if (res2 == k || contains_node(comps[idx_a].neighbor, C, res2)) {
                    found_idx = idx_a;
                } else {
                    found_idx = idx_b;
                }
                break;
            } else {
                // res is a node in T
                if (contains_node(comps[idx_a].neighbor, C, res)) {
                    found_idx = idx_a;
                } else {
                    found_idx = idx_b;
                }
                break;
            }
        }
        
        if (found_idx == -1 && active_indices.size() == 1) {
            int idx = active_indices[0];
            int l = comps[idx].leaf;
            int res = ask(l, C, k);
            if (res != C) {
                found_idx = idx;
            }
        }
        
        if (found_idx == -1) {
            // Attach k to C
            adj[C].push_back(k);
            adj[k].push_back(C);
            return;
        } else {
            // Check for edge split
            int v = comps[found_idx].neighbor;
            int res = ask(C, v, k);
            if (res == k) {
                // Split edge (C, v)
                auto it1 = find(adj[C].begin(), adj[C].end(), v);
                if(it1 != adj[C].end()) adj[C].erase(it1);
                auto it2 = find(adj[v].begin(), adj[v].end(), C);
                if(it2 != adj[v].end()) adj[v].erase(it2);
                
                adj[C].push_back(k);
                adj[k].push_back(C);
                adj[k].push_back(v);
                adj[v].push_back(k);
                return;
            } else {
                // Recurse into component v
                stack.push_back({v, C});
            }
        }
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    if (!(cin >> N)) return 0;
    adj.resize(N + 1);
    
    vector<int> p(N);
    iota(p.begin(), p.end(), 1);
    
    random_device rd;
    mt19937 g(rd());
    shuffle(p.begin(), p.end(), g);
    
    if (N > 1) {
        adj[p[0]].push_back(p[1]);
        adj[p[1]].push_back(p[0]);
    }
    
    for (int i = 2; i < N; ++i) {
        insert_node(p[i], p[0]);
    }
    
    cout << "1";
    for (int u = 1; u <= N; ++u) {
        for (int v : adj[u]) {
            if (u < v) {
                cout << " " << u << " " << v;
            }
        }
    }
    cout << endl;
    
    return 0;
}