#pragma GCC optimize("O3,unroll-loops")
#pragma GCC target("avx2,bmi,bmi2,lzcnt,popcnt")

#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <random>
#include <numeric>
#include <unordered_map>

using namespace std;

void fast_io() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
}

// Graph structure for the solver
struct SolverGraph {
    int n; 
    vector<vector<pair<int, int>>> adj; 
    vector<int> vw; 
    int max_vw; 
};

// Hierarchy level for Multilevel Partitioning
struct Level {
    SolverGraph g;
    vector<int> map_to_coarse;
};

// Global random engine
mt19937 rng(42);

void compute_max_vw(SolverGraph& g) {
    g.max_vw = 0;
    for(int w : g.vw) if(w > g.max_vw) g.max_vw = w;
}

// FM-based refinement
void refine(const SolverGraph& g, vector<int>& part, long long target_w) {
    long long current_w0 = 0;
    for(int i=0; i<g.n; ++i) if(part[i]==0) current_w0 += g.vw[i];
    
    // We allow moves that improve the cut, provided the balance doesn't get too bad
    // or moves that improve the balance if it's bad.
    
    for(int pass=0; pass<10; ++pass) {
        bool changed = false;
        vector<int> gain(g.n, 0);
        
        // Compute gains: reduction in cut weight if moved
        for(int u=0; u<g.n; ++u) {
            for(auto& e : g.adj[u]) {
                if(part[u] != part[e.first]) gain[u] += e.second;
                else gain[u] -= e.second;
            }
        }
        
        // Random visit order
        vector<int> order(g.n);
        iota(order.begin(), order.end(), 0);
        for(int i=g.n-1; i>0; --i) {
            uniform_int_distribution<int> d(0, i);
            int j = d(rng);
            swap(order[i], order[j]);
        }
        
        for(int u : order) {
            if(gain[u] > 0) {
                long long w_u = g.vw[u];
                long long new_w0 = (part[u] == 0) ? (current_w0 - w_u) : (current_w0 + w_u);
                
                long long dist_old = abs(current_w0 - target_w);
                long long dist_new = abs(new_w0 - target_w);
                
                // Allow if balance improves or stays within acceptable deviation
                bool bal_better = dist_new < dist_old;
                bool bal_ok = dist_new <= max((long long)g.max_vw, (long long)(target_w * 0.05)); 
                
                if (bal_better || bal_ok) {
                    part[u] = 1 - part[u];
                    current_w0 = new_w0;
                    // Update neighbors gains
                    for(auto& e : g.adj[u]) {
                        int v = e.first;
                        int w = e.second;
                        if(part[u] != part[v]) gain[v] += 2*w;
                        else gain[v] -= 2*w;
                    }
                    changed = true;
                }
            }
        }
        if(!changed) break;
    }
}

// Multilevel Bisection
vector<int> bisect(const SolverGraph& g) {
    // 1. Coarsen
    vector<Level> hierarchy;
    SolverGraph current = g;
    compute_max_vw(current);
    
    // Coarsen until small
    while(current.n > 80) {
        Level lev;
        lev.g = current; 
        lev.map_to_coarse.assign(current.n, -1);
        
        vector<int> match(current.n, -1);
        int coarse_cnt = 0;
        vector<int> ord(current.n);
        iota(ord.begin(), ord.end(), 0);
        for(int i=current.n-1; i>0; --i) {
            uniform_int_distribution<int> d(0, i);
            swap(ord[i], ord[d(rng)]);
        }
        
        // Heavy Edge Matching
        for(int u : ord) {
            if(match[u] != -1) continue;
            long long max_w = -1; 
            int best_v = -1;
            for(auto& e : current.adj[u]) {
                int v = e.first;
                if(match[v] == -1 && v != u) {
                    if((long long)e.second > max_w) {
                        max_w = e.second;
                        best_v = v;
                    }
                }
            }
            
            if(best_v != -1) {
                match[u] = best_v;
                match[best_v] = u;
                lev.map_to_coarse[u] = coarse_cnt;
                lev.map_to_coarse[best_v] = coarse_cnt;
                coarse_cnt++;
            } else {
                match[u] = u;
                lev.map_to_coarse[u] = coarse_cnt;
                coarse_cnt++;
            }
        }
        
        // Construct coarse graph
        SolverGraph next_g;
        next_g.n = coarse_cnt;
        next_g.adj.resize(coarse_cnt);
        next_g.vw.resize(coarse_cnt, 0);
        
        for(int u=0; u<current.n; ++u) {
            int cu = lev.map_to_coarse[u];
            next_g.vw[cu] += current.vw[u];
            for(auto& e : current.adj[u]) {
                int v = e.first;
                int w = e.second;
                int cv = lev.map_to_coarse[v];
                if(cu != cv) {
                    next_g.adj[cu].push_back({cv, w});
                }
            }
        }
        
        // Merge parallel edges
        for(int i=0; i<coarse_cnt; ++i) {
            sort(next_g.adj[i].begin(), next_g.adj[i].end());
            int widx = 0;
            for(size_t j=0; j<next_g.adj[i].size(); ++j) {
                if(widx > 0 && next_g.adj[i][widx-1].first == next_g.adj[i][j].first) {
                    next_g.adj[i][widx-1].second += next_g.adj[i][j].second;
                } else {
                    next_g.adj[i][widx] = next_g.adj[i][j];
                    widx++;
                }
            }
            next_g.adj[i].resize(widx);
        }
        compute_max_vw(next_g);
        hierarchy.push_back(lev);
        current = next_g;
    }
    
    // 2. Initial Partition on coarsest graph
    long long total_vw = 0;
    for(int w : current.vw) total_vw += w;
    long long target = total_vw / 2;
    
    int best_cut = -1;
    vector<int> best_p(current.n, 1);
    
    // Try multiple random BFS growths
    int num_tries = 8;
    for(int iter=0; iter<num_tries; ++iter) {
        vector<int> p(current.n, 1);
        int seed = uniform_int_distribution<int>(0, current.n-1)(rng);
        vector<int> q; q.reserve(current.n); 
        q.push_back(seed);
        p[seed] = 0;
        long long cur_w = current.vw[seed];
        size_t head = 0;
        
        while(head < q.size() && cur_w < target) {
            int u = q[head++];
            vector<int> nbrs; nbrs.reserve(current.adj[u].size());
            for(auto& e : current.adj[u]) nbrs.push_back(e.first);
            // shuffle
            for(int i=nbrs.size()-1; i>0; --i) {
                uniform_int_distribution<int> d(0, i);
                swap(nbrs[i], nbrs[d(rng)]);
            }
            
            for(int v : nbrs) {
                if(p[v] == 1) {
                    // Check if adding v keeps us within reasonable bounds (relaxed growth)
                    if(cur_w + current.vw[v] <= target + max((long long)current.max_vw, (long long)(target*0.2))) {
                        p[v] = 0;
                        cur_w += current.vw[v];
                        q.push_back(v);
                    }
                }
            }
        }
        
        refine(current, p, target);
        
        int cut = 0;
        for(int u=0; u<current.n; ++u) {
            for(auto& e : current.adj[u]) {
                if(p[u] != p[e.first]) cut += e.second;
            }
        }
        // cut is double counted, but comparison is valid
        
        if(best_cut == -1 || cut < best_cut) {
            best_cut = cut;
            best_p = p;
        }
    }
    
    // 3. Uncoarsen and Refine
    vector<int> p = best_p;
    while(!hierarchy.empty()) {
        Level lev = hierarchy.back();
        hierarchy.pop_back();
        vector<int> fine_p(lev.g.n);
        for(int i=0; i<lev.g.n; ++i) fine_p[i] = p[lev.map_to_coarse[i]];
        refine(lev.g, fine_p, target);
        p = fine_p;
    }
    return p;
}

struct Task {
    vector<int> nodes;
    int p_start;
    int p_end;
};

int main() {
    fast_io();
    int n, m, k;
    double eps;
    if (!(cin >> n >> m >> k >> eps)) return 0;

    vector<pair<int, int>> raw_edges;
    raw_edges.reserve(m);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        if (u != v) {
            if (u > v) swap(u, v);
            raw_edges.push_back({u, v});
        }
    }
    sort(raw_edges.begin(), raw_edges.end());
    raw_edges.erase(unique(raw_edges.begin(), raw_edges.end()), raw_edges.end());

    SolverGraph initial_g;
    initial_g.n = n;
    initial_g.adj.resize(n);
    initial_g.vw.resize(n, 1);
    
    // Convert to 0-based and build adj
    for(auto &e : raw_edges) {
        int u = e.first - 1;
        int v = e.second - 1;
        initial_g.adj[u].push_back({v, 1});
        initial_g.adj[v].push_back({u, 1});
    }

    vector<int> partition(n);
    vector<Task> stack;
    vector<int> all_nodes(n);
    iota(all_nodes.begin(), all_nodes.end(), 0);
    stack.push_back({all_nodes, 1, k});

    // Reuse map array to avoid reallocations
    vector<int> glob_to_loc(n + 1, -1);

    while(!stack.empty()) {
        Task t = stack.back();
        stack.pop_back();

        if (t.p_start == t.p_end) {
            for(int u : t.nodes) partition[u] = t.p_start;
            continue;
        }

        int mid_part = t.p_start + (t.p_end - t.p_start) / 2;
        int size = t.nodes.size();

        // Map nodes
        for(int i=0; i<size; ++i) glob_to_loc[t.nodes[i]] = i;

        // Extract Subgraph
        SolverGraph sub;
        sub.n = size;
        sub.adj.resize(size);
        sub.vw.resize(size);

        for(int i=0; i<size; ++i) {
            int u = t.nodes[i];
            sub.vw[i] = initial_g.vw[u];
            for(auto& e : initial_g.adj[u]) {
                int v = e.first;
                int local_v = glob_to_loc[v];
                if(local_v != -1) {
                    sub.adj[i].push_back({local_v, e.second});
                }
            }
        }
        
        // Cleanup map
        for(int u : t.nodes) glob_to_loc[u] = -1;

        // Solve bisection
        vector<int> split = bisect(sub);

        vector<int> left_nodes, right_nodes;
        left_nodes.reserve(size/2 + 1);
        right_nodes.reserve(size/2 + 1);

        for(int i=0; i<size; ++i) {
            if(split[i] == 0) left_nodes.push_back(t.nodes[i]);
            else right_nodes.push_back(t.nodes[i]);
        }

        // Handle empty splits fallback
        if(left_nodes.empty() || right_nodes.empty()) {
            left_nodes.clear(); right_nodes.clear();
            for(int i=0; i<size; ++i) {
                if(i < size/2) left_nodes.push_back(t.nodes[i]);
                else right_nodes.push_back(t.nodes[i]);
            }
        }

        stack.push_back({right_nodes, mid_part + 1, t.p_end});
        stack.push_back({left_nodes, t.p_start, mid_part});
    }

    for (int i = 0; i < n; ++i) {
        cout << partition[i] << (i == n - 1 ? "" : " ");
    }
    cout << "\n";

    return 0;
}