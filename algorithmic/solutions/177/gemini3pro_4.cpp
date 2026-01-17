#include <iostream>
#include <vector>
#include <algorithm>
#include <random>
#include <ctime>
#include <numeric>

using namespace std;

const int MAXN = 60005;
vector<int> adj[MAXN];
int color[MAXN];
int best_color[MAXN];
int n, m;

// Random generator
mt19937 rng(1337);

int count_total_conflicts() {
    int conflicts = 0;
    for (int u = 1; u <= n; ++u) {
        for (int v : adj[u]) {
            if (u < v) {
                if (color[u] == color[v]) {
                    conflicts++;
                }
            }
        }
    }
    return conflicts;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n >> m)) return 0;

    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    if (m == 0) {
        for (int i = 1; i <= n; ++i) cout << 1 << (i == n ? "" : " ");
        cout << "\n";
        return 0;
    }

    // Initialize with random colors
    for (int i = 1; i <= n; ++i) {
        color[i] = (rng() % 3) + 1;
        best_color[i] = color[i];
    }

    int cur_conflicts = count_total_conflicts();
    int min_conflicts = cur_conflicts;

    // To iterate nodes in random order
    vector<int> nodes(n);
    iota(nodes.begin(), nodes.end(), 1);

    // Initial shuffle
    shuffle(nodes.begin(), nodes.end(), rng);

    clock_t start_time = clock();
    double time_limit = 0.95; // Seconds

    while (true) {
        // Descent Phase (Hill Climbing)
        bool local_improved = true;
        while (local_improved) {
            local_improved = false;
            
            // Check time periodically
            if ((clock() - start_time) / (double)CLOCKS_PER_SEC > time_limit) goto end_search;

            for (int i = 0; i < n; ++i) {
                int u = nodes[i];
                
                int cnt[4] = {0, 0, 0, 0};
                for (int v : adj[u]) {
                    cnt[color[v]]++;
                }
                
                int c_curr = color[u];
                int cost_curr = cnt[c_curr];
                
                // Find minimum cost among colors 1, 2, 3
                int c1 = cnt[1];
                int c2 = cnt[2];
                int c3 = cnt[3];
                int mn = c1;
                if (c2 < mn) mn = c2;
                if (c3 < mn) mn = c3;
                
                // If we can improve strictly
                if (mn < cost_curr) {
                    // Collect candidates
                    int cands[3];
                    int ptr = 0;
                    if (c1 == mn) cands[ptr++] = 1;
                    if (c2 == mn) cands[ptr++] = 2;
                    if (c3 == mn) cands[ptr++] = 3;
                    
                    int best_c = cands[0];
                    if (ptr > 1) {
                         best_c = cands[rng() % ptr];
                    }
                    
                    color[u] = best_c;
                    cur_conflicts -= (cost_curr - mn);
                    local_improved = true;
                }
            }
        }

        // Update Global Best
        if (cur_conflicts < min_conflicts) {
            min_conflicts = cur_conflicts;
            for(int i=1; i<=n; ++i) best_color[i] = color[i];
            if (min_conflicts == 0) break;
        }

        if ((clock() - start_time) / (double)CLOCKS_PER_SEC > time_limit) break;

        // Perturbation (Iterated Local Search)
        // Change colors of random nodes to escape local optimum
        int perturb_count = 50 + (rng() % 150);
        for(int k=0; k<perturb_count; ++k) {
            int u = (rng() % n) + 1;
            int old_c = color[u];
            int new_c = (rng() % 3) + 1;
            if (old_c != new_c) {
                int cnt[4] = {0,0,0,0};
                for(int v : adj[u]) cnt[color[v]]++;
                
                cur_conflicts -= cnt[old_c];
                cur_conflicts += cnt[new_c];
                color[u] = new_c;
            }
        }
    }

    end_search:;

    for (int i = 1; i <= n; ++i) {
        cout << best_color[i] << (i == n ? "" : " ");
    }
    cout << "\n";

    return 0;
}