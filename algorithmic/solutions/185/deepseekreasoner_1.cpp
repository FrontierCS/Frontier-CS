#pragma GCC optimize("O3,unroll-loops")
#pragma GCC target("avx2,bmi,bmi2,lzcnt,popcnt")

#include <iostream>
#include <vector>
#include <algorithm>
#include <bitset>
#include <ctime>

using namespace std;

// Maximum number of vertices as per constraints
const int MAXN = 1005;

// Global variables to store graph and solution
int N, M;
bitset<MAXN> adj[MAXN]; // Adjacency bitsets
vector<int> best_clique; // Best clique found so far
int max_clique_size = 0; // Size of the best clique

// Timing for heuristic cut-off
clock_t start_clock;
const double TIME_LIMIT = 1.95; // Seconds

struct Candidate {
    int id;
    int color;
};

// Recursive function to solve Maximum Clique using Branch and Bound with Coloring (MaxCliqueDyn / Tomita algorithm)
// P: List of candidate vertices that can extend the current clique
// R: List of vertices in the current clique
void expand(vector<int>& P, vector<int>& R) {
    // Check time limit periodically (every 1024 calls)
    static int ops = 0;
    if ((++ops & 1023) == 0) {
        if ((double)(clock() - start_clock) / CLOCKS_PER_SEC > TIME_LIMIT) return;
    }

    // Update global best if current clique is larger
    if (R.size() > max_clique_size) {
        max_clique_size = R.size();
        best_clique = R;
    }

    // Basic pruning: if candidates can't improve best solution
    if (R.size() + P.size() <= max_clique_size) return;
    if (P.empty()) return;

    // --- Coloring Heuristic ---
    // Color the vertices in P such that adjacent vertices have different colors.
    // Vertices with the same color form an independent set (no edges between them).
    // A clique can contain at most one vertex from each color class.
    
    // color_classes[k] stores the bitset of vertices assigned color k (0-indexed)
    vector<bitset<MAXN>> color_classes;
    color_classes.reserve(P.size());

    vector<Candidate> sorted_P;
    sorted_P.reserve(P.size());

    // Greedy coloring
    for (int v : P) {
        int k = 0;
        bool placed = false;
        // Try to place v in existing color classes
        while (k < color_classes.size()) {
            // If v is NOT adjacent to ANY vertex currently in color_classes[k],
            // then v is independent of them (since color_classes[k] is an independent set).
            // This condition is !(adj[v] & mask).any()
            if (!(adj[v] & color_classes[k]).any()) {
                color_classes[k].set(v);
                sorted_P.push_back({v, k + 1});
                placed = true;
                break;
            }
            k++;
        }
        // Create new color class if needed
        if (!placed) {
            color_classes.emplace_back();
            color_classes.back().set(v);
            sorted_P.push_back({v, k + 1});
        }
    }

    // Stronger Pruning: The number of color classes is an upper bound on Max Clique in P
    if (R.size() + color_classes.size() <= max_clique_size) return;

    // Sort candidates by color in descending order.
    // Logic: If we are processing a vertex with color k, and we sorted descending,
    // the remaining candidate vertices (including current) have colors <= k.
    // Thus Max Clique from this point is bounded by k.
    sort(sorted_P.begin(), sorted_P.end(), [](const Candidate& a, const Candidate& b) {
        return a.color > b.color;
    });

    // Iterate through sorted candidates
    for (int i = 0; i < sorted_P.size(); ++i) {
        int v = sorted_P[i].id;
        int color = sorted_P[i].color;

        // Pruning: bound check
        if (R.size() + color <= max_clique_size) return;

        // Add v to current clique
        R.push_back(v);

        // Filter P to get new candidates: P intersection N(v)
        // Optimization: We only need to consider vertices that come AFTER v in sorted_P
        // because vertices before v are either already processed (backtracked) or incompatible.
        vector<int> next_P;
        next_P.reserve(sorted_P.size() - i);
        
        for (int j = i + 1; j < sorted_P.size(); ++j) {
            int u = sorted_P[j].id;
            if (adj[v][u]) { // Check adjacency using bitset
                next_P.push_back(u);
            }
        }

        expand(next_P, R);

        // Backtrack
        R.pop_back();

        // Check time to exit early
        if ((double)(clock() - start_clock) / CLOCKS_PER_SEC > TIME_LIMIT) return;
    }
}

int main() {
    // Fast I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N >> M)) return 0;
    
    start_clock = clock();

    // Read edges
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v; // 0-based indexing
        adj[u][v] = 1;
        adj[v][u] = 1;
    }

    // Initial ordering of vertices for the first call
    // Sorting by degree descending typically helps upper bounds converge faster
    vector<int> P(N);
    vector<pair<int, int>> deg(N);
    for (int i = 0; i < N; ++i) {
        deg[i] = { (int)adj[i].count(), i };
    }
    sort(deg.rbegin(), deg.rend());
    for (int i = 0; i < N; ++i) P[i] = deg[i].second;

    vector<int> R;
    R.reserve(N);

    // Solve
    expand(P, R);

    // Construct result vector
    vector<int> result(N, 0);
    for (int v : best_clique) {
        result[v] = 1;
    }

    // Output results
    for (int i = 0; i < N; ++i) {
        cout << result[i] << "\n";
    }

    return 0;
}