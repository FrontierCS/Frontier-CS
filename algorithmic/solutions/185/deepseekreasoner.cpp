/**
 * Problem: Maximum Clique Challenge
 * Solution: Branch and Bound with Coloring Heuristic (MCS style)
 * complexity: Non-polynomial in worst case, but efficient for N=1000 typically.
 * Time Limit: 2.0s
 */

#include <iostream>
#include <vector>
#include <algorithm>
#include <bitset>

using namespace std;

// Maximum number of vertices as per constraints
const int MAXN = 1005;

// Adjacency matrix using bitset for O(1) adjacency checks and efficient memory usage
bitset<MAXN> adj[MAXN];

int N, M;

// Global variables to store the best solution found
int max_clique_sz = 0;
vector<int> max_clique;

// Current clique in the recursion stack
vector<int> current_clique;

// Auxiliary structure for initial vertex sorting
struct Vertex {
    int id;
    int deg;
};

// Sort vertices by degree descending (Degeneracy ordering)
bool compareVertices(const Vertex& a, const Vertex& b) {
    return a.deg > b.deg;
}

/**
 * Recursive function to find maximum clique.
 * P: List of candidate vertices that can extend the current clique.
 *    Logic ensures P contains valid candidates only (neighbors of all current_clique members)
 */
void expand(vector<int>& P) {
    // If no candidates left, we hit a leaf. Check if it's the best so far.
    if (P.empty()) {
        if ((int)current_clique.size() > max_clique_sz) {
            max_clique_sz = current_clique.size();
            max_clique = current_clique;
        }
        return;
    }

    // Basic Pruning: If current clique + all candidates cannot beat max found, return.
    if ((int)current_clique.size() + (int)P.size() <= max_clique_sz) {
        return;
    }

    // Heuristic Coloring for tighter bounding:
    // We compute a coloring of the induced subgraph of P. 
    // If valid clqiue in P has size K, we need at least K colors.
    // Conversely, if we color P with C colors, max clique size is <= C.
    // We specifically compute 'suffix coloring' to prune branches dynamically.
    
    int p_size = P.size();
    vector<int> colors(p_size);

    // Compute colors for P[i] working backwards (from end to start)
    // colors[i] = smallest color not used by any neighbor in P[i+1...end]
    // This allows us to bound the max clique size extension starting with P[i] by colors[i].
    for (int i = p_size - 1; i >= 0; --i) {
        int u = P[i];
        int k = 1;
        
        // Find the smallest color k that does not conflict with neighbors appearing later in P
        while (true) {
            bool conflict = false;
            for (int j = i + 1; j < p_size; ++j) {
                // If neighbor j uses color k, k is forbidden
                if (colors[j] == k && adj[u].test(P[j])) {
                    conflict = true;
                    break;
                }
            }
            if (!conflict) break;
            k++;
        }
        colors[i] = k;
    }

    // Iterate through candidates and recurse
    for (int i = 0; i < p_size; ++i) {
        // Pruning based on coloring bound
        // colors[i] is an upper bound on valid clique size extension using subset P[i...end]
        if ((int)current_clique.size() + colors[i] <= max_clique_sz) {
            continue;
        }

        int u = P[i];
        
        // Create new candidate set for next level
        // New P = intersection of current candidates appearing after u AND neighbors of u
        // (We only consider P[i+1...end] to avoid duplicates and respect ordering)
        vector<int> new_P;
        new_P.reserve(colors[i]); // Heuristic reservation
        
        for (int j = i + 1; j < p_size; ++j) {
            int v = P[j];
            if (adj[u].test(v)) {
                new_P.push_back(v);
            }
        }

        // Add u to clique and recurse
        current_clique.push_back(u);
        expand(new_P);
        current_clique.pop_back();
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
        --u; --v;
        adj[u].set(v);
        adj[v].set(u);
    }

    // Initial vertex ordering heuristic:
    // Sort vertices by degree descending. This helps finding larger cliques earlier,
    // which makes the bounds stricter and pruning more effective.
    vector<Vertex> V(N);
    for (int i = 0; i < N; ++i) {
        V[i].id = i;
        V[i].deg = adj[i].count();
    }
    sort(V.begin(), V.end(), compareVertices);

    // Prepare initial candidate set
    vector<int> P(N);
    for (int i = 0; i < N; ++i) {
        P[i] = V[i].id;
    }

    // Find Maximum Clique
    expand(P);

    // Format output
    vector<int> result(N, 0);
    for (int u : max_clique) {
        result[u] = 1;
    }

    for (int i = 0; i < N; ++i) {
        cout << result[i] << "\n";
    }

    return 0;
}