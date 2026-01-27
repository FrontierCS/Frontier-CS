#include <iostream>
#include <vector>
#include <algorithm>
#include <bitset>
#include <chrono>

using namespace std;

// Max vertices constraint N <= 1000
const int MAXN = 1005;

// Adjacency matrix stored as bitsets for efficiency
bitset<MAXN> adj[MAXN];
int deg[MAXN]; // Degree of each vertex

int N, M;

// To store the best clique found
vector<int> best_clique;
int max_sz = 0; // Size of the best clique found

// Current clique being built during recursion
vector<int> current_path;

// Helper array for coloring heuristic (greedy coloring)
// Global to avoid reallocation, used with rolling 'cookie' (timestamp) logic
int used_for_color[MAXN];
int cookie = 0;

// Timer to handle the 2.0s limit
auto start_time = chrono::high_resolution_clock::now();

// Check if we are approaching the time limit
bool is_time_out() {
    auto now = chrono::high_resolution_clock::now();
    chrono::duration<double> diff = now - start_time;
    // Buffer time for cleanup and I/O
    return diff.count() > 1.95;
}

// Recursive function to solve Maximum Clique problem
// Algorithm based on Tomita's MCQ (Max Clique with Coloring)
// P: Candidate set of vertices that can extend the current clique
void solve(vector<int>& P) {
    if (is_time_out()) return;

    if (P.empty()) {
        // Found a maximal clique in this branch
        if ((int)current_path.size() > max_sz) {
            max_sz = current_path.size();
            best_clique = current_path;
        }
        return;
    }

    // Basic pruning: if even taking all candidates won't beat best, stop
    if ((int)current_path.size() + (int)P.size() <= max_sz) return;

    // --- Coloring Heuristic ---
    // Calculate colors for vertices in P.
    // We compute colors based on the subgraph induced by P.
    // The number of colors required for a subset is an upper bound on the clique size in that subset.
    // We process from the end to start to support the pruning logic in the main loop.
    
    int m = P.size();
    vector<int> colors(m);

    for (int i = m - 1; i >= 0; --i) {
        int u = P[i];
        cookie++; // Increment cookie effectively resets the used array
        
        // Check neighbors that appear later in P
        // If u is connected to P[j] (where j > i), u cannot share P[j]'s color
        for (int j = i + 1; j < m; ++j) {
            int v = P[j];
            if (adj[u][v]) {
                // Mark color[j] as used
                used_for_color[colors[j]] = cookie;
            }
        }
        
        // Assign smallest unused color
        int c = 1;
        while (used_for_color[c] == cookie) c++;
        colors[i] = c;
    }

    // --- Branching ---
    for (int i = 0; i < m; ++i) {
        if (is_time_out()) return;

        // Pruning using coloring bound
        // colors[i] is the chromatic number of the suffix P[i...end].
        // This is an upper bound on the largest clique we can find using P[i] and any subset of P[i+1...end].
        if ((int)current_path.size() + colors[i] <= max_sz) {
            // Since colors are computed to be bounds on suffixes, if this fails, subsequent suffixes also fail usually
            // In strict MCQ algorithm, this is a definite return point.
            return;
        }

        int u = P[i];
        current_path.push_back(u);

        // Create new candidate set for recursive call
        // New candidates must be:
        // 1. Neighbors of u (clique property)
        // 2. From the suffix {P[i+1]...P[end]} (to avoid duplicates and use loop order)
        vector<int> new_P;
        new_P.reserve(m - 1 - i);

        for (int j = i + 1; j < m; ++j) {
            int v = P[j];
            if (adj[u][v]) {
                new_P.push_back(v);
            }
        }

        solve(new_P);

        // Backtrack
        current_path.pop_back();
    }
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    start_time = chrono::high_resolution_clock::now();

    if (!(cin >> N >> M)) return 0;

    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        if (u == v) continue;
        adj[u][v] = 1;
        adj[v][u] = 1;
        deg[u]++;
        deg[v]++;
    }

    // Initial candidates are all vertices
    vector<int> P;
    P.reserve(N);
    for (int i = 1; i <= N; ++i) P.push_back(i);

    // Initial heuristic: Sort vertices by degree descending.
    // This helps in finding a large clique earlier, which improves pruning.
    sort(P.begin(), P.end(), [&](int a, int b) {
        return deg[a] > deg[b];
    });

    solve(P);

    // Format output
    vector<int> result(N + 1, 0);
    for (int u : best_clique) {
        result[u] = 1;
    }

    for (int i = 1; i <= N; ++i) {
        cout << result[i] << "\n";
    }

    return 0;
}