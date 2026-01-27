#include <iostream>
#include <vector>
#include <algorithm>
#include <numeric>
#include <ctime>
#include <random>

using namespace std;

// Maximum number of vertices as per constraints
const int MAXN = 505;
vector<int> adjList[MAXN];
int N, M;

struct Solution {
    vector<int> colors;
    int num_colors;
    Solution() : num_colors(10000) {}
};

Solution best_sol;
static int used_by[MAXN]; 
static int token_global = 0;

// Fast Greedy Coloring using a specific permutation p
Solution greedy_coloring(const vector<int>& p) {
    Solution sol;
    sol.colors.resize(N + 1, 0);
    sol.num_colors = 0;

    // Iterate through vertices in the given order
    for (int u : p) {
        token_global++;
        // Reset timestamp if near overflow (approx 2 billion)
        if (token_global >= 2000000000) { 
             fill(used_by, used_by + MAXN, 0);
             token_global = 1;
        }

        // Mark colors currently used by neighbors
        for (int v : adjList[u]) {
            int c_v = sol.colors[v];
            if (c_v != 0) {
                used_by[c_v] = token_global;
            }
        }
        
        // Find the smallest color not used by any neighbor
        int c = 1;
        while (used_by[c] == token_global) {
            c++;
        }
        
        sol.colors[u] = c;
        if (c > sol.num_colors) sol.num_colors = c;
    }
    return sol;
}

// DSatur Heuristic for initial high-quality solution
Solution dsatur_initial() {
    Solution sol;
    sol.colors.assign(N + 1, 0);
    sol.num_colors = 0;
    
    vector<int> degrees(N + 1);
    for(int i=1; i<=N; ++i) degrees[i] = adjList[i].size();
    
    vector<int> sat(N + 1, 0); // Saturation degree
    vector<bool> colored(N + 1, false);
    
    // Matrix to track if a vertex v has a neighbor of color c
    // Used to update saturation degrees efficiently
    static bool adj_colors[MAXN][MAXN]; 
    for(int i=0;i<=N;i++) for(int j=0;j<=N;j++) adj_colors[i][j]=false;

    int colored_cnt = 0;
    while(colored_cnt < N) {
        int u = -1;
        int max_sat = -1;
        int max_deg = -1;
        
        // Select uncolored vertex with max saturation, tie-break with max degree
        for (int v = 1; v <= N; ++v) {
            if (!colored[v]) {
                if (sat[v] > max_sat) {
                    max_sat = sat[v];
                    max_deg = degrees[v];
                    u = v;
                } else if (sat[v] == max_sat) {
                    if (degrees[v] > max_deg) {
                        max_deg = degrees[v];
                        u = v;
                    }
                }
            }
        }
        
        if (u == -1) break;

        colored[u] = true;
        colored_cnt++;
        
        // Assign lowest valid color
        int c = 1;
        while (adj_colors[u][c]) c++;
        
        sol.colors[u] = c;
        if (c > sol.num_colors) sol.num_colors = c;
        
        // Update neighbors' saturation info
        for (int v : adjList[u]) {
            if (!colored[v]) {
                if (!adj_colors[v][c]) {
                    adj_colors[v][c] = true;
                    sat[v]++;
                }
            }
        }
    }
    return sol;
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    if (!(cin >> N >> M)) return 0;
    
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        adjList[u].push_back(v);
        adjList[v].push_back(u);
    }
    
    // Step 1: Generate initial solution with DSatur
    best_sol = dsatur_initial();
    
    // Step 2: Iterated Greedy Optimization
    // Try to improve solution by reordering vertices based on color classes
    mt19937 rng(1337);
    vector<int> p(N);
    iota(p.begin(), p.end(), 1); // Initialize p with 1, 2, ..., N
    
    clock_t start_time = clock();
    int iter = 0;
    
    // Pre-allocate working vectors
    vector<int> current_p;
    current_p.reserve(N);
    vector<int> class_indices;
    class_indices.reserve(N);
    
    while (true) {
        iter++;
        // Check time limit periodically (every 256 iterations)
        if ((iter & 255) == 0) {
            if ((double)(clock() - start_time) / CLOCKS_PER_SEC > 1.95) break;
        }
        
        current_p.clear();
        
        // Strategy Selection:
        // Mostly use heuristics based on current best solution, 
        // occasionally randomize to escape local optima.
        
        if (iter % 20 == 0) {
             // Random Shuffle
             current_p = p;
             shuffle(current_p.begin(), current_p.end(), rng);
        } else {
            // Group vertices by their color in the best solution found so far
            int k = best_sol.num_colors;
            vector<vector<int>> classes(k + 1);
            for (int i = 1; i <= N; ++i) {
                int c = best_sol.colors[i];
                if (c > k) c = k; 
                classes[c].push_back(i);
            }
            
            class_indices.resize(k);
            iota(class_indices.begin(), class_indices.end(), 1);
            
            // Heuristic: Process smallest color classes first.
            // Vertices in small color classes are often constrained/difficult.
            // Coloring them early gives them access to lower colors.
            if (iter % 10 == 0) {
                 shuffle(class_indices.begin(), class_indices.end(), rng);
            } else {
                 sort(class_indices.begin(), class_indices.end(), [&](int a, int b) {
                     if (classes[a].size() != classes[b].size())
                        return classes[a].size() < classes[b].size();
                     return a < b;
                 });
            }
            
            // Construct new permutation from ordered classes
            for (int c_idx : class_indices) {
                // Optionally shuffle within class (though independent set order matters less)
                for (int u : classes[c_idx]) {
                    current_p.push_back(u);
                }
            }
        }
        
        Solution sol = greedy_coloring(current_p);
        
        // Accept better or equal solutions to traverse the search space plateau
        if (sol.num_colors <= best_sol.num_colors) {
            best_sol = sol;
        }
    }
    
    // Output result
    for (int i = 1; i <= N; ++i) {
        cout << best_sol.colors[i] << "\n";
    }
    
    return 0;
}