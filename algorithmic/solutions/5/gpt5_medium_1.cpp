#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if(!(cin >> n >> m)) return 0;
    vector<long long> a(10);
    for(int i = 0; i < 10; ++i) cin >> a[i]; // unused for construction
    
    vector<vector<int>> adj(n+1), inv(n+1);
    vector<int> indeg(n+1, 0);
    adj.reserve(n+1);
    inv.reserve(n+1);
    for(int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        inv[v].push_back(u);
        indeg[v]++;
    }
    
    // Attempt: If DAG, compute exact longest path in DAG
    auto topo_indeg = indeg;
    queue<int> q;
    for(int i = 1; i <= n; ++i) if(topo_indeg[i] == 0) q.push(i);
    vector<int> topo;
    topo.reserve(n);
    while(!q.empty()) {
        int u = q.front(); q.pop();
        topo.push_back(u);
        for(int v : adj[u]) {
            if(--topo_indeg[v] == 0) q.push(v);
        }
    }
    auto output_path = [&](const vector<int>& path){
        cout << (int)path.size() << "\n";
        for(size_t i = 0; i < path.size(); ++i) {
            if(i) cout << ' ';
            cout << path[i];
        }
        cout << "\n";
    };
    if((int)topo.size() == n) {
        vector<int> dp(n+1, 1), par(n+1, -1);
        int best_len = 1, best_v = topo[0];
        for(int u : topo) {
            for(int v : adj[u]) {
                if(dp[v] < dp[u] + 1) {
                    dp[v] = dp[u] + 1;
                    par[v] = u;
                    if(dp[v] > best_len) {
                        best_len = dp[v];
                        best_v = v;
                    }
                }
            }
        }
        vector<int> path;
        int cur = best_v;
        while(cur != -1) {
            path.push_back(cur);
            cur = par[cur];
        }
        reverse(path.begin(), path.end());
        output_path(path);
        return 0;
    }
    
    // For heuristics, sort adjacency lists for edge existence checks
    for(int i = 1; i <= n; ++i) {
        sort(adj[i].begin(), adj[i].end());
        // inv not required sorted for logic but sorting may improve cache locality
        // sort(inv[i].begin(), inv[i].end());
    }
    
    auto hasEdge = [&](int u, int v)->bool{
        const auto &au = adj[u];
        return binary_search(au.begin(), au.end(), v);
    };
    
    // Longest path under a given permutation order (keep only forward edges)
    auto run_order = [&](const vector<int>& order)->vector<int> {
        vector<int> pos(n+1, 0);
        for(int i = 0; i < n; ++i) pos[order[i]] = i;
        vector<int> dp(n+1, 1), par(n+1, -1);
        int best_len = 1, best_v = order[0];
        for(int i = 0; i < n; ++i) {
            int u = order[i];
            for(int v : adj[u]) {
                if(pos[u] < pos[v]) {
                    int cand = dp[u] + 1;
                    if(dp[v] < cand) {
                        dp[v] = cand;
                        par[v] = u;
                        if(cand > best_len) {
                            best_len = cand;
                            best_v = v;
                        }
                    }
                }
            }
        }
        vector<int> path;
        int cur = best_v;
        while(cur != -1) {
            path.push_back(cur);
            cur = par[cur];
        }
        reverse(path.begin(), path.end());
        return path;
    };
    
    // Insertion-based improvement to extend a path
    auto improve_by_insertion = [&](const vector<int>& init_path)->vector<int> {
        if(init_path.empty()) return init_path;
        vector<int> nxt(n+1, -1), prv(n+1, -1);
        vector<char> inPath(n+1, 0);
        int head = init_path.front();
        int tail = init_path.back();
        for(size_t i = 0; i + 1 < init_path.size(); ++i) {
            nxt[init_path[i]] = init_path[i+1];
            prv[init_path[i+1]] = init_path[i];
        }
        for(int v : init_path) inPath[v] = 1;
        
        vector<int> remaining;
        remaining.reserve(n - (int)init_path.size());
        for(int v = 1; v <= n; ++v) if(!inPath[v]) remaining.push_back(v);
        
        std::mt19937_64 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());
        shuffle(remaining.begin(), remaining.end(), rng);
        
        auto insert_between = [&](int u, int v, int w){
            // u -> v -> w; currently u->w edge existed in path (u->w adjacency not needed)
            nxt[u] = v; prv[v] = u;
            nxt[v] = w; prv[w] = v;
        };
        
        auto try_insert_vertex = [&](int v)->bool {
            if(inPath[v]) return false;
            if(head != -1) {
                if(hasEdge(tail, v)) {
                    // append
                    nxt[tail] = v; prv[v] = tail; nxt[v] = -1; tail = v; inPath[v] = 1; return true;
                }
                if(hasEdge(v, head)) {
                    // prepend
                    prv[head] = v; nxt[v] = head; prv[v] = -1; head = v; inPath[v] = 1; return true;
                }
            }
            // Choose smaller list to scan
            if(inv[v].size() <= adj[v].size()) {
                for(int u : inv[v]) {
                    if(!inPath[u]) continue;
                    int w = nxt[u];
                    if(w != -1 && hasEdge(v, w)) {
                        insert_between(u, v, w);
                        inPath[v] = 1;
                        return true;
                    }
                }
            } else {
                for(int w : adj[v]) {
                    if(!inPath[w]) continue;
                    int u = prv[w];
                    if(u != -1 && hasEdge(u, v)) {
                        insert_between(u, v, w);
                        inPath[v] = 1;
                        return true;
                    }
                }
            }
            return false;
        };
        
        const int max_passes = 2;
        for(int pass = 0; pass < max_passes; ++pass) {
            bool any = false;
            for(int v : remaining) {
                if(!inPath[v]) {
                    if(try_insert_vertex(v)) any = true;
                }
            }
            if(!any) break;
        }
        
        // Build the resulting path
        vector<int> path;
        path.reserve(n);
        int cur = head;
        while(cur != -1) {
            path.push_back(cur);
            cur = nxt[cur];
        }
        return path;
    };
    
    // Main heuristic loop
    vector<int> order(n);
    iota(order.begin(), order.end(), 1);
    std::mt19937_64 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());
    
    vector<int> best_path;
    int tries = 10; // number of random orders
    for(int it = 0; it < tries; ++it) {
        shuffle(order.begin(), order.end(), rng);
        vector<int> candidate = run_order(order);
        if(candidate.size() > best_path.size()) best_path = move(candidate);
    }
    
    // Improve by insertion
    best_path = improve_by_insertion(best_path);
    
    // Refine using order built from current best path
    vector<char> inBest(n+1, 0);
    for(int v : best_path) inBest[v] = 1;
    vector<int> order2;
    order2.reserve(n);
    for(int v : best_path) order2.push_back(v);
    vector<int> rest;
    rest.reserve(n - best_path.size());
    for(int v = 1; v <= n; ++v) if(!inBest[v]) rest.push_back(v);
    shuffle(rest.begin(), rest.end(), rng);
    for(int v : rest) order2.push_back(v);
    vector<int> candidate2 = run_order(order2);
    if(candidate2.size() > best_path.size()) best_path = move(candidate2);
    
    // Another insertion pass after refinement
    best_path = improve_by_insertion(best_path);
    
    if(best_path.empty()) {
        // Fallback: at least one vertex
        best_path.push_back(1);
    }
    
    output_path(best_path);
    return 0;
}