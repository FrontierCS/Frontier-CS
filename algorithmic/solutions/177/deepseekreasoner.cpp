#include <bits/stdc++.h>
using namespace std;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    cin >> n >> m;
    
    vector<vector<int>> adj(n);
    for (int i = 0; i < m; i++) {
        int u, v;
        cin >> u >> v;
        u--; v--;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    
    const int NUM_RESTARTS = 10;
    const int MAX_PASSES = 100;
    
    vector<int> best_colors(n);
    int best_conflicts = INT_MAX;
    
    random_device rd;
    mt19937 rng(rd());
    uniform_int_distribution<int> col_dist(0, 2);
    
    for (int restart = 0; restart < NUM_RESTARTS; restart++) {
        // random initial colors
        vector<int> colors(n);
        for (int i = 0; i < n; i++) {
            colors[i] = col_dist(rng);
        }
        
        // count neighbors of each color for every vertex
        vector<array<int,3>> cnt(n, {0,0,0});
        for (int v = 0; v < n; v++) {
            for (int w : adj[v]) {
                cnt[v][colors[w]]++;
            }
        }
        
        // local improvement
        bool changed = true;
        int passes = 0;
        while (changed && passes < MAX_PASSES) {
            changed = false;
            vector<int> order(n);
            iota(order.begin(), order.end(), 0);
            shuffle(order.begin(), order.end(), rng);
            
            for (int v : order) {
                int cur = colors[v];
                int cur_bad = cnt[v][cur];
                int best_c = cur;
                int best_bad = cur_bad;
                for (int c = 0; c < 3; c++) {
                    if (c == cur) continue;
                    if (cnt[v][c] < best_bad) {
                        best_bad = cnt[v][c];
                        best_c = c;
                    }
                }
                if (best_c != cur) {
                    // change color of v to best_c
                    colors[v] = best_c;
                    // update neighbor counts
                    for (int w : adj[v]) {
                        cnt[w][cur]--;
                        cnt[w][best_c]++;
                    }
                    changed = true;
                }
            }
            passes++;
        }
        
        // compute total number of conflicting edges
        int total_conflicts = 0;
        for (int v = 0; v < n; v++) {
            total_conflicts += cnt[v][colors[v]];
        }
        total_conflicts /= 2;  // each edge counted twice
        
        if (total_conflicts < best_conflicts) {
            best_conflicts = total_conflicts;
            best_colors = colors;
        }
        
        // early exit if perfect coloring found
        if (best_conflicts == 0) break;
    }
    
    // output colors (1‑based)
    for (int i = 0; i < n; i++) {
        if (i > 0) cout << ' ';
        cout << best_colors[i] + 1;
    }
    cout << '\n';
    
    return 0;
}