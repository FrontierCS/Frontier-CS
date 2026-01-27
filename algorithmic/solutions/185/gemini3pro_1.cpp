#include <iostream>
#include <vector>
#include <bitset>
#include <algorithm>
#include <ctime>

using namespace std;

// Maximum number of vertices as per constraints
const int MAXN = 1005;

// Adjacency matrix using bitsets for efficient space and intersection checks
bitset<MAXN> adj[MAXN];
int N, M;

// Global variables to store the best clique found
vector<int> best_sol;
int max_sz = 0;

// Time management
clock_t start_time;
const double TIME_LIMIT = 1.95; 

/**
 * Recursive Branch and Bound function to find Maximum Clique
 * 
 * Logic based on MaxCliqueDyn / MCQ (Tomita et al.):
 * 1. Color the candidate vertices greedily.
 * 2. If |current_clique| + |colors| <= |best_clique|, prune.
 * 3. Iterate vertices grouped by color classes, from highest color to lowest.
 *    This ensures that when processing a vertex with color k, we only consider 
 *    candidates from color classes < k, strictly bounding the potential clique size.
 */
void solve(vector<int>& R, vector<int>& current_sol) {
    // Periodically check time limit
    if ((double)(clock() - start_time) / CLOCKS_PER_SEC > TIME_LIMIT) return;

    if (R.empty()) {
        if (current_sol.size() > max_sz) {
            max_sz = current_sol.size();
            best_sol = current_sol;
        }
        return;
    }

    // Basic size pruning
    if (current_sol.size() + R.size() <= max_sz) return;

    // Coloring Heuristic
    // color_groups[k] will store vertices assigned color k+1
    vector<vector<int>> color_groups;
    // Heuristic: reserve based on expected chromatic number (unknown, but small fraction of R usually)
    color_groups.reserve(min((int)R.size(), 50)); 

    // Greedy coloring of the induced subgraph G[R]
    for (int u : R) {
        bool placed = false;
        // Try to fit u into existing color classes
        for (int c = 0; c < color_groups.size(); ++c) {
            bool conflict = false;
            // Check if u is connected to any vertex in this color class
            // Since color classes are independent sets, u can join if no neighbors in it
            for (int v : color_groups[c]) {
                if (adj[u][v]) {
                    conflict = true;
                    break;
                }
            }
            if (!conflict) {
                color_groups[c].push_back(u);
                placed = true;
                break;
            }
        }
        // If not placed, create a new color class
        if (!placed) {
            color_groups.push_back({u});
        }
    }

    // Coloring Bound Pruning
    if (current_sol.size() + color_groups.size() <= max_sz) return;

    // Iterate through color classes in reverse order (Largest Color First)
    for (int k = color_groups.size() - 1; k >= 0; --k) {
        // Pruning: Max extension from here is k+1 (this vertex + 1 from each lower class)
        if (current_sol.size() + (k + 1) <= max_sz) return;

        for (int u : color_groups[k]) {
            // Re-check bound as max_sz might have increased in recursion
            if (current_sol.size() + (k + 1) <= max_sz) return;
            
            // Check time
            if ((double)(clock() - start_time) / CLOCKS_PER_SEC > TIME_LIMIT) return;

            // Construct new candidate set
            // We only consider vertices from color groups strictly smaller than k
            // that are neighbors of u.
            vector<int> next_R;
            next_R.reserve(k); 

            for (int j = 0; j < k; ++j) {
                for (int v : color_groups[j]) {
                    if (adj[u][v]) {
                        next_R.push_back(v);
                    }
                }
            }
            
            current_sol.push_back(u);
            solve(next_R, current_sol);
            current_sol.pop_back();
        }
    }
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N >> M)) return 0;

    start_time = clock();

    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        // Convert to 0-based indexing
        u--; v--;
        adj[u][v] = 1;
        adj[v][u] = 1;
    }

    // Initial candidates: all vertices
    // Sort vertices by degree descending. High degree vertices are more likely 
    // to be part of large cliques and this helps the initial coloring.
    vector<int> R(N);
    vector<pair<int, int>> deg(N);
    for (int i = 0; i < N; ++i) {
        deg[i] = { (int)adj[i].count(), i };
    }
    sort(deg.rbegin(), deg.rend());
    
    for(int i = 0; i < N; ++i) {
        R[i] = deg[i].second;
    }

    vector<int> current_sol;
    current_sol.reserve(N);
    
    // Start search
    solve(R, current_sol);

    // Output results
    vector<int> result(N, 0);
    for (int u : best_sol) {
        result[u] = 1;
    }

    for (int i = 0; i < N; ++i) {
        cout << result[i] << "\n";
    }

    return 0;
}