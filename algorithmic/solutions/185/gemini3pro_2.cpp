#include <iostream>
#include <vector>
#include <algorithm>
#include <bitset>
#include <chrono>

using namespace std;

// Maximum number of vertices as per constraints
const int MAXN = 1005;

// Global variables to store graph and solution
int N, M;
bitset<MAXN> adj[MAXN];
vector<int> current_clique;
vector<int> best_clique;
int max_sz = 0;

// Timer to handle the 2.0s limit
auto start_time = chrono::high_resolution_clock::now();
const double TIME_LIMIT = 1.95;

// Check if we are running out of time
bool time_limit_exceeded() {
    auto now = chrono::high_resolution_clock::now();
    chrono::duration<double> diff = now - start_time;
    return diff.count() > TIME_LIMIT;
}

// Recursive function to find maximum clique
// P: The set of candidate vertices for the current step
void expand(const vector<int>& P) {
    // Check time limit
    if (time_limit_exceeded()) return;

    // Base case: No more candidates
    if (P.empty()) {
        if ((int)current_clique.size() > max_sz) {
            max_sz = current_clique.size();
            best_clique = current_clique;
        }
        return;
    }

    // Basic Pruning: If current clique size + remaining candidates cannot beat max_sz
    if ((int)current_clique.size() + (int)P.size() <= max_sz) return;

    // Graph Coloring Heuristic
    // Divide P into color classes (Independent Sets).
    // groups[i] contains vertices of color i.
    // We use a simple greedy coloring.
    // Vertices in the same group are not connected to each other.
    vector<vector<int>> groups;
    
    // Iterate through candidates and assign first valid color
    for (int u : P) {
        bool inserted = false;
        // Try to fit u into existing color classes
        for (int c = 0; c < (int)groups.size(); ++c) {
            bool conflict = false;
            // Check for edges with existing vertices in this color class
            for (int v : groups[c]) {
                if (adj[u][v]) {
                    conflict = true;
                    break;
                }
            }
            if (!conflict) {
                groups[c].push_back(u);
                inserted = true;
                break;
            }
        }
        // If not fits in any, create new color class
        if (!inserted) {
            groups.push_back({u});
        }
    }

    int k = groups.size(); // Number of colors used

    // Pruning with Coloring:
    // We can pick at most one vertex from each color class.
    // If current + k <= max_sz, we can't improve.
    if ((int)current_clique.size() + k <= max_sz) return;

    // Branching: Iterate through color classes in reverse order
    // This ordering (highest color first) often finds larger cliques faster.
    // Candidates for the next step are restricted to lower color classes.
    for (int c = k - 1; c >= 0; --c) {
        // Bound check: Candidates for extension are restricted to groups 0 to c.
        // So max extension is c + 1 (size of groups 0..c).
        // Since we are processing group c, the potential new candidates will come from 0..c-1.
        // The max clique size using vertex from group c + subsequent candidates is bounded by 1 + c.
        // current_size + 1 + c <= max_sz implies current + c + 1 <= max_sz
        if ((int)current_clique.size() + (c + 1) <= max_sz) return;

        // Iterate over vertices in the current color class
        for (int u : groups[c]) {
            // Re-check bound
            if ((int)current_clique.size() + (c + 1) <= max_sz) return;

            // Add u to current clique
            current_clique.push_back(u);

            // Construct new candidate set
            // Candidates must be neighbors of u AND belong to color classes 0 to c-1
            // This restriction avoids duplicate search branches.
            vector<int> new_P;
            new_P.reserve(c); 

            for (int cc = 0; cc < c; ++cc) {
                for (int v : groups[cc]) {
                    if (adj[u][v]) {
                        new_P.push_back(v);
                    }
                }
            }

            // Recursive step
            expand(new_P);

            // Backtrack
            current_clique.pop_back();
        }
    }
}

int main() {
    // Fast I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N >> M)) return 0;

    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        // Convert to 0-based indexing
        u--; v--;
        adj[u][v] = 1;
        adj[v][u] = 1;
    }

    // Initial candidates: all vertices
    // Heuristic: Sort by degree descending.
    // This helps the greedy coloring to be more effective (fewer colors) 
    // and explores dense regions first.
    vector<int> P(N);
    vector<pair<int, int>> degs(N);
    for (int i = 0; i < N; ++i) {
        degs[i] = { (int)adj[i].count(), i };
    }
    // Sort descending
    sort(degs.rbegin(), degs.rend());

    for (int i = 0; i < N; ++i) {
        P[i] = degs[i].second;
    }

    // Start search
    expand(P);

    // Prepare output
    vector<int> result(N, 0);
    for (int u : best_clique) {
        result[u] = 1;
    }

    for (int i = 0; i < N; ++i) {
        cout << result[i] << "\n";
    }

    return 0;
}