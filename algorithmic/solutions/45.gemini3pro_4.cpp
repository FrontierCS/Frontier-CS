#include <iostream>
#include <vector>
#include <algorithm>
#include <numeric>
#include <random>
#include <map>
#include <cmath>
#include <cstring>

using namespace std;

// Fast I/O
void fast_io() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
}

// Random engine with fixed seed for reproducibility
mt19937 rng(42);

struct Edge {
    int v;
    int w;
};

struct Graph {
    int n;
    long long total_vwgt;
    vector<int> vwgt;
    vector<vector<Edge>> adj;

    Graph(int n_ = 0) : n(n_), total_vwgt(0) {
        if (n > 0) {
            vwgt.resize(n, 1);
            adj.resize(n);
        }
    }
    
    void calc_total_weight() {
        total_vwgt = 0;
        for(int w : vwgt) total_vwgt += w;
    }
};

// Coarsen the graph using Heavy Edge Matching
pair<Graph, vector<int>> coarsen_graph(const Graph& g) {
    int n = g.n;
    vector<int> match(n, -1);
    vector<int> idx(n);
    iota(idx.begin(), idx.end(), 0);
    shuffle(idx.begin(), idx.end(), rng);

    int coarse_n = 0;
    
    for (int u : idx) {
        if (match[u] != -1) continue;
        int best_v = -1;
        long long best_w = -1;
        
        for (auto& e : g.adj[u]) {
            if (match[e.v] == -1 && e.v != u) {
                if (e.w > best_w) {
                    best_w = e.w;
                    best_v = e.v;
                }
            }
        }
        
        if (best_v != -1) {
            match[u] = coarse_n;
            match[best_v] = coarse_n;
            coarse_n++;
        } else {
            match[u] = coarse_n++;
        }
    }
    
    Graph cg(coarse_n);
    vector<int> map_f2c = match;
    
    for (int i = 0; i < n; i++) cg.vwgt[match[i]] = 0;
    for (int i = 0; i < n; i++) cg.vwgt[match[i]] += g.vwgt[i];
    cg.calc_total_weight();
    
    vector<vector<pair<int,int>>> raw_edges(coarse_n);
    for (int u = 0; u < n; u++) {
        int cu = match[u];
        for (auto& e : g.adj[u]) {
            int cv = match[e.v];
            if (cu != cv) {
                raw_edges[cu].push_back({cv, e.w});
            }
        }
    }
    
    for(int i=0; i<coarse_n; ++i) {
        sort(raw_edges[i].begin(), raw_edges[i].end());
        for(size_t j=0; j<raw_edges[i].size(); ) {
            int v = raw_edges[i][j].first;
            int w = 0;
            while(j < raw_edges[i].size() && raw_edges[i][j].first == v) {
                w += raw_edges[i][j].second;
                j++;
            }
            cg.adj[i].push_back({v, w});
        }
    }
    
    return {cg, map_f2c};
}

// Initial partition using multiple random BFS trials
vector<int> initial_partition(const Graph& g) {
    int n = g.n;
    long long target = g.total_vwgt / 2;
    long long best_cut = -1;
    vector<int> best_part(n, 0);
    
    int trials = 8; 
    for (int t = 0; t < trials; t++) {
        vector<int> part(n, 0);
        vector<int> idx(n);
        iota(idx.begin(), idx.end(), 0);
        shuffle(idx.begin(), idx.end(), rng);
        
        long long current_w = 0;
        vector<int> q;
        vector<bool> visited(n, false);
        
        if (n > 0) {
            int root = idx[0];
            q.push_back(root);
            visited[root] = true;
            int head = 0;
            while(head < (int)q.size() && current_w < target) {
                int u = q[head++];
                // Heuristic: stop if we are getting too heavy relative to target
                if (current_w + g.vwgt[u] > target * 1.1 && current_w > target * 0.9) break; 
                part[u] = 1;
                current_w += g.vwgt[u];
                for(auto& e : g.adj[u]) {
                    if (!visited[e.v]) {
                        visited[e.v] = true;
                        q.push_back(e.v);
                    }
                }
            }
        }
        
        // Fill remainder if underfilled
        if (current_w < target) {
             for (int u : idx) {
                if (part[u] == 0) {
                     if (current_w + g.vwgt[u] <= target * 1.05) {
                         part[u] = 1;
                         current_w += g.vwgt[u];
                     }
                }
                if (current_w >= target) break;
            }
        }

        long long cut = 0;
        for (int u = 0; u < n; u++) {
            for (auto& e : g.adj[u]) {
                if (part[u] != part[e.v]) cut += e.w;
            }
        }
        
        if (best_cut == -1 || cut < best_cut) {
            best_cut = cut;
            best_part = part;
        }
    }
    return best_part;
}

// Refinement using simplified FM/Greedy approach
void refine(const Graph& g, vector<int>& part) {
    int n = g.n;
    long long w[2] = {0, 0};
    for(int i=0; i<n; ++i) w[part[i]] += g.vwgt[i];
    
    int max_passes = 6;
    
    for(int pass=0; pass<max_passes; ++pass) {
        bool improved = false;
        vector<int> idx(n);
        iota(idx.begin(), idx.end(), 0);
        shuffle(idx.begin(), idx.end(), rng);
        
        for (int u : idx) {
            int p = part[u];
            int other = 1 - p;
            
            long long gain = 0;
            for (auto& e : g.adj[u]) {
                if (part[e.v] == other) gain += e.w;
                else gain -= e.w;
            }
            
            if (gain > 0) {
                // Check balance constraints
                long long new_w_other = w[other] + g.vwgt[u];
                long long new_w_p = w[p] - g.vwgt[u];
                
                long long imb_curr = abs(w[0] - w[1]);
                long long imb_new = abs(new_w_other - new_w_p);
                
                // Allow move if it reduces imbalance or keeps it within tolerance
                long long tolerance = max((long long)g.vwgt[u], (long long)(g.total_vwgt * 0.02));

                if (imb_new < imb_curr || imb_new <= tolerance) {
                    part[u] = other;
                    w[p] -= g.vwgt[u];
                    w[other] += g.vwgt[u];
                    improved = true;
                }
            }
        }
        if (!improved) break;
    }
}

// Multilevel Bisection
vector<int> multilevel_bisection(const Graph& g) {
    if (g.n < 80) {
        vector<int> p = initial_partition(g);
        refine(g, p);
        return p;
    }
    
    auto res = coarsen_graph(g);
    vector<int> c_part = multilevel_bisection(res.first);
    
    vector<int> part(g.n);
    for (int i = 0; i < g.n; i++) part[i] = c_part[res.second[i]];
    
    refine(g, part);
    return part;
}

vector<int> global_map; 

// Recursive solver for k-way partition
void solve_recursive_range(const Graph& g, int L, int R, vector<int>& p_global, const vector<int>& nodes) {
    if (L == R) {
        for (int u : nodes) p_global[u] = L;
        return;
    }
    
    int sub_n = nodes.size();
    if (sub_n == 0) return;

    Graph subg(sub_n);
    // Use global_map for O(sub_n) mapping
    for(int i=0; i<sub_n; ++i) global_map[nodes[i]] = i;
    
    for(int i=0; i<sub_n; ++i) {
        int u = nodes[i];
        subg.vwgt[i] = g.vwgt[u];
        for(auto& e : g.adj[u]) {
            int v_local = global_map[e.v];
            if(v_local != -1) {
                subg.adj[i].push_back({v_local, e.w});
            }
        }
    }
    for(int i=0; i<sub_n; ++i) global_map[nodes[i]] = -1; // reset
    
    subg.calc_total_weight();
    
    vector<int> local_part = multilevel_bisection(subg);
    
    vector<int> left_nodes, right_nodes;
    left_nodes.reserve(sub_n); 
    right_nodes.reserve(sub_n);
    
    for(int i=0; i<sub_n; ++i) {
        if(local_part[i] == 0) left_nodes.push_back(nodes[i]);
        else right_nodes.push_back(nodes[i]);
    }

    if(left_nodes.empty() || right_nodes.empty()) {
        left_nodes.clear(); right_nodes.clear();
        int half = sub_n/2;
        for(int i=0; i<half; ++i) left_nodes.push_back(nodes[i]);
        for(int i=half; i<sub_n; ++i) right_nodes.push_back(nodes[i]);
    }

    int mid = L + (R - L) / 2;
    solve_recursive_range(g, L, mid, p_global, left_nodes);
    solve_recursive_range(g, mid + 1, R, p_global, right_nodes);
}

int main() {
    fast_io();
    int n, m, k;
    double eps;
    if (!(cin >> n >> m >> k >> eps)) return 0;
    
    vector<vector<int>> raw_adj(n + 1);
    for(int i=0; i<m; ++i) {
        int u, v;
        cin >> u >> v;
        if (u != v) {
            raw_adj[u].push_back(v);
            raw_adj[v].push_back(u);
        }
    }
    
    Graph g(n);
    for(int i=1; i<=n; ++i) {
        sort(raw_adj[i].begin(), raw_adj[i].end());
        raw_adj[i].erase(unique(raw_adj[i].begin(), raw_adj[i].end()), raw_adj[i].end());
        
        for(int v : raw_adj[i]) {
            g.adj[i-1].push_back({v-1, 1});
        }
    }
    g.calc_total_weight();
    
    vector<int> p_global(n);
    vector<int> nodes(n);
    iota(nodes.begin(), nodes.end(), 0);
    global_map.assign(n, -1);
    
    solve_recursive_range(g, 1, k, p_global, nodes);
    
    for(int i=0; i<n; ++i) {
        cout << p_global[i] << (i == n-1 ? "" : " ");
    }
    cout << "\n";
    
    return 0;
}