#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>
#include <chrono>
#include <cmath>

using namespace std;

// Constants and Globals
const int N_MAX = 1005;
int N, M, H;
int A[N_MAX];
vector<int> adj[N_MAX];
int parent[N_MAX];
vector<int> children[N_MAX];
int depth[N_MAX];
int subA[N_MAX];
int mrd[N_MAX]; // Max Relative Depth (height of subtree)

// Random number generator
mt19937 rng(1);

// Helper function to check ancestry
// Returns true if u is an ancestor of v (or u == v)
bool is_ancestor(int u, int v) {
    int curr = v;
    while (curr != -1) {
        if (curr == u) return true;
        curr = parent[curr];
    }
    return false;
}

// Update depths in the subtree rooted at u
void update_subtree_depths(int u, int d) {
    depth[u] = d;
    for (int v : children[u]) {
        update_subtree_depths(v, d + 1);
    }
}

// Calculate MRD for node u based on its current children
int calc_mrd(int u) {
    int max_d = 0;
    for (int v : children[u]) {
        max_d = max(max_d, mrd[v] + 1);
    }
    return max_d;
}

// Initialize solution
void init() {
    for (int i = 0; i < N; ++i) {
        parent[i] = -1;
        children[i].clear();
        depth[i] = 0;
        subA[i] = A[i];
        mrd[i] = 0;
    }
}

// Apply a move: move node v to become a child of new_p
void apply_move(int v, int new_p) {
    int old_p = parent[v];
    
    // 1. Structure Update
    if (old_p != -1) {
        auto& sibs = children[old_p];
        for (size_t i = 0; i < sibs.size(); ++i) {
            if (sibs[i] == v) {
                sibs[i] = sibs.back();
                sibs.pop_back();
                break;
            }
        }
    }
    
    parent[v] = new_p;
    if (new_p != -1) {
        children[new_p].push_back(v);
    }
    
    // 2. Depth Update (only v's subtree)
    int new_base_depth = (new_p == -1 ? 0 : depth[new_p] + 1);
    update_subtree_depths(v, new_base_depth);
    
    // 3. Update Ancestor Statistics (subA and mrd)
    // For old parent chain
    int curr = old_p;
    while (curr != -1) {
        subA[curr] -= subA[v];
        mrd[curr] = calc_mrd(curr);
        curr = parent[curr];
    }
    
    // For new parent chain
    curr = new_p;
    while (curr != -1) {
        subA[curr] += subA[v];
        mrd[curr] = calc_mrd(curr);
        curr = parent[curr];
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    // Input
    if (!(cin >> N >> M >> H)) return 0;
    for (int i = 0; i < N; ++i) cin >> A[i];
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    // Skip coordinates
    for (int i = 0; i < N; ++i) {
        int x, y;
        cin >> x >> y;
    }

    // Initialization
    init();

    // Setup Timer
    auto start_time = chrono::steady_clock::now();
    double time_limit = 1.95;

    // Simulated Annealing Parameters
    double T0 = 200.0; // Initial temperature
    double T1 = 0.0;   // Final temperature
    double T = T0;

    vector<int> nodes(N);
    iota(nodes.begin(), nodes.end(), 0);

    long long iter_count = 0;
    
    while (true) {
        iter_count++;
        // Check time every 1024 iterations
        if ((iter_count & 1023) == 0) {
            auto now = chrono::steady_clock::now();
            double elapsed = chrono::duration<double>(now - start_time).count();
            if (elapsed > time_limit) break;
            // Update Temperature
            T = T0 + (T1 - T0) * (elapsed / time_limit);
        }

        // Pick a random node v
        int v = nodes[rng() % N];

        // Identify best move
        int best_u = -2;
        int max_new_d = -100; // Initialize with invalid
        
        // Candidates
        vector<int> candidates;
        candidates.reserve(adj[v].size() + 1);
        candidates.push_back(-1);
        for (int u : adj[v]) candidates.push_back(u);

        // Randomize order to break ties arbitrarily
        shuffle(candidates.begin(), candidates.end(), rng);
        
        int current_p = parent[v];
        
        for (int u : candidates) {
            if (u == current_p) continue;

            // Determine new depth
            int d_u = (u == -1 ? -1 : depth[u]);
            int new_d = d_u + 1;
            
            // Optimization: we want to maximize new_d (maximize depth -> maximize score)
            // If new_d is not better than what we found, skip
            if (new_d <= max_new_d) continue; 

            // Validity Check
            // 1. Cycle: u must not be in subtree of v
            if (u != -1) {
                if (is_ancestor(v, u)) continue;
            }

            // 2. Height Constraint
            //    max depth in v's subtree will be new_d + mrd[v]
            if (new_d + mrd[v] > H) continue;

            // Found a better valid move
            max_new_d = new_d;
            best_u = u;
        }

        // If no valid move found (other than current, or worse ones), continue
        if (best_u == -2) continue;

        // Calculate Delta
        int current_d = depth[v];
        int shift = max_new_d - current_d;
        long long delta = (long long)shift * subA[v];

        // Acceptance Logic
        if (delta >= 0) {
            apply_move(v, best_u);
        } else {
            // Negative delta: accept with probability
            if (T > 1e-9) {
                double prob = exp(delta / T);
                if (generate_canonical<double, 10>(rng) < prob) {
                    apply_move(v, best_u);
                }
            }
        }
    }

    // Output
    for (int i = 0; i < N; ++i) {
        cout << parent[i] << (i == N - 1 ? "" : " ");
    }
    cout << endl;

    return 0;
}