#include <iostream>
#include <vector>
#include <algorithm>
#include <random>
#include <chrono>

using namespace std;

// Fast I/O
void fast_io() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
}

const int MAXN = 60005;
vector<int> adj[MAXN];
int color[MAXN];
int best_color[MAXN];
int n, m;

// Random number generator
mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

// Helper to count conflicts for a specific node u with a given color c
// This function assumes 'color' array holds the current colors of neighbors
inline int get_local_conflicts(int u, int c) {
    int cnt = 0;
    for (int v : adj[u]) {
        if (color[v] == c) cnt++;
    }
    return cnt;
}

int main() {
    fast_io();

    if (!(cin >> n >> m)) return 0;

    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    // Initial random assignment
    for (int i = 1; i <= n; ++i) {
        color[i] = rng() % 3 + 1;
    }

    // Calculate initial global conflicts
    long long current_conflicts = 0;
    for (int u = 1; u <= n; ++u) {
        for (int v : adj[u]) {
            if (u < v && color[u] == color[v]) {
                current_conflicts++;
            }
        }
    }

    // Save initial state as best found so far
    long long best_conflicts = current_conflicts;
    for(int i=1; i<=n; ++i) best_color[i] = color[i];

    // Create a processing order for nodes
    vector<int> nodes(n);
    for(int i=0; i<n; ++i) nodes[i] = i+1;
    shuffle(nodes.begin(), nodes.end(), rng);

    auto start_time = chrono::steady_clock::now();
    // Set a time limit slightly less than typical contest limits (1s or 2s).
    // 0.95s is safe for 1s limit.
    double time_limit = 0.95; 

    int iter = 0;
    // Main optimization loop: Hill Climbing with Random Restarts/Perturbation
    while (true) {
        iter++;
        // Check time every 16 iterations to minimize overhead
        if ((iter & 15) == 0) { 
            auto now = chrono::steady_clock::now();
            chrono::duration<double> elapsed = now - start_time;
            if (elapsed.count() > time_limit) break;
        }

        bool improved = false;
        
        // Randomize start offset to process nodes in different cyclic orders each pass
        // This simulates a random permutation order without the cost of reshuffling O(N)
        int start_offset = rng() % n;

        for (int i = 0; i < n; ++i) {
            int u = nodes[(start_offset + i) % n];
            int c_curr = color[u];
            int conflicts_curr = get_local_conflicts(u, c_curr);
            
            // Try all 3 colors to find which one minimizes conflicts
            int confs[4]; // 1-based indexing for colors 1, 2, 3
            confs[c_curr] = conflicts_curr;
            int min_c_val = conflicts_curr;
            
            for (int c = 1; c <= 3; ++c) {
                if (c == c_curr) continue;
                confs[c] = get_local_conflicts(u, c);
                if (confs[c] < min_c_val) {
                    min_c_val = confs[c];
                }
            }
            
            // Collect all candidate colors that achieve the minimum conflict count
            vector<int> candidates;
            for (int c = 1; c <= 3; ++c) {
                if (confs[c] == min_c_val) {
                    candidates.push_back(c);
                }
            }
            
            // Pick a candidate. If multiple are optimal, pick randomly.
            // This randomness helps traverse plateaus in the search space.
            int choice = c_curr;
            if (!candidates.empty()) {
                choice = candidates[rng() % candidates.size()];
            }
            
            // Apply change if the color is different
            // Note: choice can be equal to c_curr if current color is already optimal
            // However, we only count it as a "move" if we change color or if we want to force moves.
            // Here we only update if color changes.
            if (choice != c_curr) {
                current_conflicts += (confs[choice] - conflicts_curr);
                color[u] = choice;
                improved = true;
            }
        }

        // Check if we found a new global best
        if (current_conflicts < best_conflicts) {
            best_conflicts = current_conflicts;
            for(int i=1; i<=n; ++i) best_color[i] = color[i];
            // If we found a valid 3-coloring (0 conflicts), we can stop early
            if (best_conflicts == 0) break;
        }

        // If no improvement in a full pass (local optimum), apply perturbation
        if (!improved) {
            // Perturbation: Change ~0.5% of nodes randomly to escape local optimum
            int perturb_size = 1 + (n / 200); 
            for(int k=0; k<perturb_size; ++k) {
                int u = rng() % n + 1;
                int c_old = color[u];
                int c_new = rng() % 3 + 1;
                if(c_old != c_new) {
                    int c1 = get_local_conflicts(u, c_old);
                    int c2 = get_local_conflicts(u, c_new);
                    color[u] = c_new;
                    current_conflicts += (c2 - c1);
                }
            }
        }
    }

    // Output results
    for (int i = 1; i <= n; ++i) {
        cout << best_color[i] << (i == n ? "" : " ");
    }
    cout << "\n";

    return 0;
}