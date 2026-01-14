#include <iostream>
#include <vector>
#include <algorithm>
#include <ctime>
#include <cstdlib>

using namespace std;

// Fast XorShift for random numbers
struct XorShift {
    unsigned int x, y, z, w;
    XorShift() {
        x = 123456789; y = 362436069; z = 521288629; w = 88675123;
    }
    unsigned int next() {
        unsigned int t = x ^ (x << 11);
        x = y; y = z; z = w;
        return w = (w ^ (w >> 19)) ^ (t ^ (t >> 8));
    }
    // Random integer in [0, k-1]
    int next(int k) {
        if (k <= 0) return 0;
        return next() % k;
    }
} rng;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    vector<vector<int>> adj(n + 1);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    // Handle case with no edges
    if (m == 0) {
        for (int i = 1; i <= n; ++i) cout << "1" << (i == n ? "" : " ");
        cout << "\n";
        return 0;
    }

    // Initial random coloring
    vector<int> color(n + 1);
    for (int i = 1; i <= n; ++i) {
        color[i] = rng.next(3) + 1;
    }

    // Calculate initial conflicts
    long long conflicts = 0;
    for (int u = 1; u <= n; ++u) {
        for (int v : adj[u]) {
            if (u < v && color[u] == color[v]) {
                conflicts++;
            }
        }
    }

    vector<int> best_color = color;
    long long min_conflicts = conflicts;

    // Order of processing vertices
    vector<int> p(n);
    for(int i=0; i<n; ++i) p[i] = i + 1;

    clock_t start_time = clock();
    // Use a time limit (safe margin for standard 1s/2s limits)
    double time_limit = 0.85; 

    while (true) {
        // Check time limit
        if ((double)(clock() - start_time) / CLOCKS_PER_SEC > time_limit) break;

        // Shuffle processing order to avoid cyclic patterns
        for (int i = n - 1; i > 0; --i) {
            int j = rng.next(i + 1);
            swap(p[i], p[j]);
        }

        bool improved = false;
        for (int i = 0; i < n; ++i) {
            int u = p[i];
            
            // Count neighbor colors
            int c1 = 0, c2 = 0, c3 = 0;
            for (int v : adj[u]) {
                int c = color[v];
                if (c == 1) c1++;
                else if (c == 2) c2++;
                else c3++;
            }

            int cur_cost = (color[u] == 1 ? c1 : (color[u] == 2 ? c2 : c3));
            int min_cost = c1;
            if (c2 < min_cost) min_cost = c2;
            if (c3 < min_cost) min_cost = c3;

            // Greedy move: only change if it strictly reduces conflicts
            if (min_cost < cur_cost) {
                int candidates[3];
                int cand_cnt = 0;
                if (c1 == min_cost) candidates[cand_cnt++] = 1;
                if (c2 == min_cost) candidates[cand_cnt++] = 2;
                if (c3 == min_cost) candidates[cand_cnt++] = 3;
                
                int new_c = candidates[rng.next(cand_cnt)];
                
                conflicts -= (cur_cost - min_cost);
                color[u] = new_c;
                improved = true;
            }
        }

        if (conflicts < min_conflicts) {
            min_conflicts = conflicts;
            best_color = color;
        }

        // If in a local minimum, perturb the solution to escape
        if (!improved) {
            if ((double)(clock() - start_time) / CLOCKS_PER_SEC > time_limit) break;

            // Perturb: change color of ~2% of vertices randomly
            int perturb = n / 50 + 1; 
            for(int k=0; k<perturb; ++k) {
                int u = rng.next(n) + 1;
                int old_c = color[u];
                int new_c = rng.next(3) + 1;
                if (old_c == new_c) new_c = (old_c % 3) + 1;
                
                // Update conflicts for the forced move
                int c1 = 0, c2 = 0, c3 = 0;
                for (int v : adj[u]) {
                    int c = color[v];
                    if (c == 1) c1++;
                    else if (c == 2) c2++;
                    else c3++;
                }
                int old_cost = (old_c == 1 ? c1 : (old_c == 2 ? c2 : c3));
                int new_cost = (new_c == 1 ? c1 : (new_c == 2 ? c2 : c3));
                conflicts += (new_cost - old_cost);
                color[u] = new_c;
            }
        }
    }

    for (int i = 1; i <= n; ++i) {
        cout << best_color[i] << (i == n ? "" : " ");
    }
    cout << "\n";

    return 0;
}