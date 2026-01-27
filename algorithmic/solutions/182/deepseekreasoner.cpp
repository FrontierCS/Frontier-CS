#include <iostream>
#include <vector>
#include <algorithm>
#include <numeric>
#include <random>
#include <chrono>
#include <set>

using namespace std;

// Fast I/O
void fast_io() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
}

const int MAXN = 10005;

int N, M;
vector<int> adj[MAXN];

// Random number generator
mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

// Store best solution
vector<int> best_cover;
int min_cover_size = 1000000000;

// To track time
auto start_time = chrono::steady_clock::now();

double get_elapsed() {
    auto now = chrono::steady_clock::now();
    return chrono::duration<double>(now - start_time).count();
}

// Function to run the dynamic degree greedy heuristic for Maximum Independent Set
// Vertex Cover = V \ Independent Set
// This heuristic prioritizes nodes with low degrees in the remaining subgraph to be in the Independent Set.
// Nodes with low degrees "block" fewer neighbors.
void solve_run(double weight_noise) {
    // status: 0 = active, 1 = in_IS, 2 = removed_by_neighbor (i.e., in VS)
    vector<int> status(N + 1, 0); 
    vector<int> current_degree(N + 1);
    
    // Calculate initial degrees (based on simple graph structure)
    for (int i = 1; i <= N; i++) {
        current_degree[i] = adj[i].size();
    }

    // Priority queue to store pairs of (priority, vertex_index)
    // priority = current_degree + random_noise
    // We use a set for efficient updates (erase + insert)
    set<pair<double, int>> pq;
    vector<double> priorities(N + 1);
    
    uniform_real_distribution<double> dist(0.0, 1.0);

    // Initialize priorities
    for (int i = 1; i <= N; i++) {
        // Tie-breaking with noise, or structural perturbation
        priorities[i] = current_degree[i] + dist(rng) * weight_noise;
        pq.insert({priorities[i], i});
    }

    int is_size = 0;
    vector<int> is_nodes;
    is_nodes.reserve(N);

    // Main greedy loop
    while (!pq.empty()) {
        // Pick vertex u with minimum priority (approx minimum degree)
        // Picking u for Independent Set means u is NOT in Vertex Cover.
        pair<double, int> top = *pq.begin();
        pq.erase(pq.begin());
        
        int u = top.second;
        status[u] = 1; // Added to Independent Set
        is_nodes.push_back(u);
        is_size++;
        
        // Find neighbors that must be removed/covered
        // In VC terms: if u is not in VC, all neighbors v MUST be in VC.
        // In MIS terms: u blocks all its neighbors.
        vector<int> neighbors_to_remove;
        for (int v : adj[u]) {
            if (status[v] == 0) {
                status[v] = 2; // Forced into Vertex Cover (removed from IS candidates)
                neighbors_to_remove.push_back(v);
                // Remove v from active set
                pq.erase({priorities[v], v});
            }
        }
        
        // Update degrees of the 'second-hop' neighbors.
        // Removing a vertex v from the graph reduces the degree of v's neighbors.
        // We removed u (status 1) and a set of v's (status 2).
        // For u: its neighbors are the v's. They are removed, so no degree update needed for them in pq (already removed).
        // For v's: their neighbors z might still be active.
        
        for (int v : neighbors_to_remove) {
            for (int z : adj[v]) {
                if (status[z] == 0) {
                    // z is active. It lost a neighbor v.
                    // Update z's priority
                    pq.erase({priorities[z], z});
                    current_degree[z]--;
                    // We assume noise is an offset, so we just decrement the integer part
                    priorities[z] -= 1.0;
                    pq.insert({priorities[z], z});
                }
            }
        }
    }
    
    // Calculate result size
    // Vertex Cover Size = N - Independent Set Size
    int vc_size = N - is_size;
    
    if (vc_size < min_cover_size) {
        min_cover_size = vc_size;
        best_cover.assign(N + 1, 1); // Default to in VC
        for (int u : is_nodes) {
            best_cover[u] = 0; // Remove IS nodes from VC
        }
    }
}

// Optimization: Simple Randomized Greedy (runs faster, explores more permutations)
void solve_fast_run() {
    vector<int> p(N);
    iota(p.begin(), p.end(), 1);
    shuffle(p.begin(), p.end(), rng);
    
    vector<bool> blocked(N + 1, false);
    vector<int> current_is;
    int k = 0;
    
    for (int u : p) {
        if (!blocked[u]) {
            current_is.push_back(u);
            k++;
            blocked[u] = true;
            for (int v : adj[u]) {
                blocked[v] = true;
            }
        }
    }
    
    int vc = N - k;
    if (vc < min_cover_size) {
        min_cover_size = vc;
        best_cover.assign(N + 1, 1);
        for (int u : current_is) best_cover[u] = 0;
    }
}

int main() {
    fast_io();
    
    if (!(cin >> N >> M)) return 0;

    for (int i = 0; i < M; i++) {
        int u, v;
        cin >> u >> v;
        if (u != v) {
            adj[u].push_back(v);
            adj[v].push_back(u);
        }
    }

    // Preprocessing: Sort and remove duplicate edges.
    // This makes degree calculations accurate (number of unique neighbors).
    for (int i = 1; i <= N; i++) {
        sort(adj[i].begin(), adj[i].end());
        adj[i].erase(unique(adj[i].begin(), adj[i].end()), adj[i].end());
    }
    
    // Initialize with full set
    best_cover.assign(N + 1, 1);
    min_cover_size = N;

    int iter = 0;
    // We aim to run for slightly less than 2.0s to be safe
    while (get_elapsed() < 1.95) {
        iter++;
        
        // Strategy mixing:
        // 1. First run: nearly deterministic Min-Degree (very small noise for Tie-Breaking)
        // 2. Next runs: Min-Degree with moderate noise (randomized heuristic)
        // 3. If we perform too many dynamic runs (should fit ~50-100), maybe switch to fast scans if time permits.
        // Given complexity, 50-100 dynamic runs are feasible.
        
        if (iter == 1) {
            solve_run(1e-6); 
        } else {
            // Use larger noise to escape local optima or explore different ties
            // Random noise scale between 0.1 and 0.9 usually works well
            solve_run(0.3);
        }
    }
    
    for (int i = 1; i <= N; i++) {
        cout << best_cover[i] << "\n";
    }

    return 0;
}