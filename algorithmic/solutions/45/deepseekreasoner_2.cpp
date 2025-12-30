#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    
    int n, m, k;
    double eps;
    cin >> n >> m >> k >> eps;
    
    vector<vector<int>> adj(n);
    for (int i = 0; i < m; i++) {
        int u, v;
        cin >> u >> v;
        u--; v--;
        if (u == v) continue;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    
    // Remove self-loops and parallel edges
    for (int i = 0; i < n; i++) {
        sort(adj[i].begin(), adj[i].end());
        adj[i].erase(unique(adj[i].begin(), adj[i].end()), adj[i].end());
    }
    
    // Balance constraint
    int ideal = (n + k - 1) / k;               // ceil(n/k)
    int max_part_size = floor((1.0 + eps) * ideal);
    
    // Special case k == 1
    if (k == 1) {
        for (int i = 0; i < n; i++) cout << "1 ";
        cout << '\n';
        return 0;
    }
    
    // Random balanced initial partition
    vector<int> part(n);
    vector<int> part_size(k, 0);
    int base = n / k;
    int rem = n % k;
    vector<int> target_sizes(k);
    for (int i = 0; i < k; i++) {
        target_sizes[i] = base + (i < rem ? 1 : 0);
    }
    
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
    vector<int> vertices(n);
    iota(vertices.begin(), vertices.end(), 0);
    shuffle(vertices.begin(), vertices.end(), rng);
    
    int idx = 0;
    for (int i = 0; i < k; i++) {
        for (int j = 0; j < target_sizes[i]; j++) {
            part[vertices[idx]] = i;
            part_size[i]++;
            idx++;
        }
    }
    
    // Refinement passes
    const int ITER = 5;
    
    auto ec_refine = [&]() -> bool {
        bool improved = false;
        vector<int> order(n);
        iota(order.begin(), order.end(), 0);
        shuffle(order.begin(), order.end(), rng);
        
        for (int v : order) {
            int cur = part[v];
            // Collect neighbor parts
            vector<int> neigh_parts;
            neigh_parts.reserve(adj[v].size());
            for (int u : adj[v]) {
                neigh_parts.push_back(part[u]);
            }
            sort(neigh_parts.begin(), neigh_parts.end());
            
            int cnt_cur = 0;
            int i = 0;
            int best_gain = -1;
            int best_part = -1;
            while (i < neigh_parts.size()) {
                int p = neigh_parts[i];
                int cnt = 0;
                while (i < neigh_parts.size() && neigh_parts[i] == p) {
                    cnt++; i++;
                }
                if (p == cur) {
                    cnt_cur = cnt;
                } else {
                    int gain = cnt - cnt_cur;
                    if (gain > best_gain && part_size[p] < max_part_size) {
                        best_gain = gain;
                        best_part = p;
                    }
                }
            }
            if (best_gain > 0) {
                // Move vertex v
                part_size[cur]--;
                part_size[best_part]++;
                part[v] = best_part;
                improved = true;
            }
        }
        return improved;
    };
    
    auto cv_refine = [&]() -> bool {
        bool improved = false;
        vector<int> order(n);
        iota(order.begin(), order.end(), 0);
        shuffle(order.begin(), order.end(), rng);
        
        for (int v : order) {
            int cur = part[v];
            // Collect neighbor parts with counts
            vector<int> neigh_parts;
            neigh_parts.reserve(adj[v].size());
            for (int u : adj[v]) {
                neigh_parts.push_back(part[u]);
            }
            sort(neigh_parts.begin(), neigh_parts.end());
            
            vector<pair<int,int>> counts;   // (part, count)
            int idx = 0;
            while (idx < neigh_parts.size()) {
                int p = neigh_parts[idx];
                int cnt = 0;
                while (idx < neigh_parts.size() && neigh_parts[idx] == p) {
                    cnt++; idx++;
                }
                counts.push_back({p, cnt});
            }
            
            int cnt_cur = 0;
            for (auto& [p, c] : counts) {
                if (p == cur) {
                    cnt_cur = c;
                    break;
                }
            }
            int old_F = counts.size();
            if (cnt_cur > 0) old_F--;   // exclude own part if present
            
            int best_q = -1;
            int best_F_reduction = 0;
            for (auto& [q, cnt_q] : counts) {
                if (q == cur) continue;
                if (part_size[q] >= max_part_size) continue;
                int ec_gain = cnt_q - cnt_cur;
                if (ec_gain < 0) continue;
                int new_F = counts.size() - 1;   // q is in counts
                if (new_F < old_F) {
                    int reduction = old_F - new_F;
                    if (reduction > best_F_reduction) {
                        best_F_reduction = reduction;
                        best_q = q;
                    }
                }
            }
            if (best_q != -1) {
                part_size[cur]--;
                part_size[best_q]++;
                part[v] = best_q;
                improved = true;
            }
        }
        return improved;
    };
    
    for (int iter = 0; iter < ITER; iter++) {
        bool ec_improved = ec_refine();
        bool cv_improved = cv_refine();
        if (!ec_improved && !cv_improved) break;
    }
    
    // Output partition (1-indexed)
    for (int i = 0; i < n; i++) {
        cout << part[i] + 1 << " \n"[i == n-1];
    }
    
    return 0;
}