#pragma GCC optimize("O3")
#pragma GCC target("avx2,bmi,bmi2,popcnt,lzcnt")

#include <iostream>
#include <vector>
#include <algorithm>
#include <bitset>
#include <ctime>

using namespace std;

// Maximum number of vertices as per constraints
const int MAXN = 1005;
const double TIME_LIMIT = 1.95; // Time limit buffer

// Global variables
int N, M;
bitset<MAXN> adj[MAXN]; // Adjacency matrix using bitset for efficiency
vector<int> current_clique; // Stores the clique currently being built
vector<int> best_solution; // Stores the best clique found so far
int max_clique_size = 0;

clock_t start_time;
bool time_out = false;

// Check if time limit is exceeded
inline bool check_time() {
    if (time_out) return true;
    if ((double)(clock() - start_time) / CLOCKS_PER_SEC > TIME_LIMIT) {
        time_out = true;
        return true;
    }
    return false;
}

/**
 * Bron-Kerbosch algorithm with Pivot, Bitsets, and Size Pruning.
 * 
 * P: Candidate vertices that can extend the current clique
 * X: Excluded vertices (candidates that have already been processed)
 */
void solve(bitset<MAXN> P, bitset<MAXN> X) {
    if (time_out) return;

    // Pruning: If current clique size + potential candidates <= best found, prune.
    if (current_clique.size() + P.count() <= max_clique_size) {
        return;
    }

    if (P.none()) {
        // No candidates left. Check if this is a new maximum.
        // Even if X is not empty (non-maximal in global sense), it's a valid clique.
        if (current_clique.size() > max_clique_size) {
            max_clique_size = current_clique.size();
            best_solution = current_clique;
        }
        return;
    }

    // Periodic time check (every 1024 calls to reduce overhead)
    static int calls = 0;
    if ((++calls & 1023) == 0) {
        if (check_time()) return;
    }

    // Pivot Selection:
    // Choose a pivot u in P U X that maximizes |P n N(u)| using a heuristic.
    // Heuristic: Since vertices are reordered by degree descending, the first 
    // vertex in P | X has the highest global degree and is a good pivot candidate.
    
    int pivot = -1;
    // Compute Union of P and X
    bitset<MAXN> PUX = P | X;
    
    // Find first set bit in PUX
    // Since N <= 1000, a simple loop is efficient enough given O3 optimization.
    // We could use _Find_first() if available, but loop is standard compliant.
    for (int u = 0; u < N; ++u) {
        if (PUX[u]) {
            pivot = u;
            break;
        }
    }
    
    // Candidates to branch on: P \ N(pivot)
    // Minimizes branching factor.
    bitset<MAXN> branch_candidates = P & ~adj[pivot];

    for (int v = 0; v < N; ++v) {
        if (branch_candidates[v]) {
            // Optimization: Double check upper bound before recursing
            // Count intersection size of P and N(v)
            if (current_clique.size() + 1 + (P & adj[v]).count() <= max_clique_size) {
                 // Even if we pick v, we can't beat max_clique_size using remaining P
                 // Update sets and continue (equivalent to backtracking this branch immediately)
                 P.reset(v);
                 X.set(v);
                 continue;
            }

            // Add v to current clique
            current_clique.push_back(v);
            
            // Recurse with restricted candidates and exclusion sets
            // newP = P intersect N(v)
            // newX = X intersect N(v)
            solve(P & adj[v], X & adj[v]);
            
            // Backtrack
            current_clique.pop_back();
            
            if (time_out) return;
            
            // Move v from P to X (v is processed)
            P.reset(v);
            X.set(v);
        }
    }
}

// Structure for vertex reordering
struct Node {
    int id; // Original 1-based index
    int deg;
};

// Sort nodes by degree descending
bool compareNodes(const Node& a, const Node& b) {
    return a.deg > b.deg;
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    start_time = clock();

    if (!(cin >> N >> M)) return 0;

    vector<pair<int, int>> edges(M);
    vector<int> deg(N + 1, 0);

    for (int i = 0; i < M; ++i) {
        cin >> edges[i].first >> edges[i].second;
        deg[edges[i].first]++;
        deg[edges[i].second]++;
    }

    // Heuristic: Reorder vertices by degree descending.
    // This helps the branch and bound prune earlier.
    vector<Node> nodes(N);
    for (int i = 0; i < N; ++i) {
        nodes[i] = {i + 1, deg[i + 1]};
    }
    sort(nodes.begin(), nodes.end(), compareNodes);

    // Mappings between original (1-based) and internal reordered (0-based) indices
    vector<int> old_to_new(N + 1);
    vector<int> new_to_old(N);

    for (int i = 0; i < N; ++i) {
        new_to_old[i] = nodes[i].id;
        old_to_new[nodes[i].id] = i;
    }

    // Build Adjacency Matrix with reordered indices
    for (int i = 0; i < M; ++i) {
        int u = edges[i].first;
        int v = edges[i].second;
        if (u == v) continue; // Ignore self-loops
        
        int nu = old_to_new[u];
        int nv = old_to_new[v];
        
        // Undirected graph
        adj[nu].set(nv);
        adj[nv].set(nu);
    }

    // Initial Candidate Set P contains all vertices 0..N-1
    bitset<MAXN> P;
    for (int i = 0; i < N; ++i) P.set(i);
    
    // Initial Excluded Set X is empty
    bitset<MAXN> X;
    
    // Reserve memory to prevent reallocation overhead
    current_clique.reserve(N);
    best_solution.reserve(N);

    // Start Solver
    solve(P, X);
    
    // Prepare Output
    // Map best solution found back to original indices
    vector<int> output(N + 1, 0);
    for (int idx : best_solution) {
        output[new_to_old[idx]] = 1;
    }
    
    for (int i = 1; i <= N; ++i) {
        cout << output[i] << "\n";
    }

    return 0;
}