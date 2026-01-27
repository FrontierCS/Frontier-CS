#include <iostream>
#include <vector>
#include <algorithm>
#include <ctime>
#include <numeric>
#include <random>

using namespace std;

// Global variables to store graph and best solution
int N, M;
vector<vector<int>> adj;
vector<int> best_cover;
int best_k;
mt19937 rng(1337);

// Function to read input and build adjacency list
void read_input() {
    if (cin >> N >> M) {
        adj.resize(N + 1);
        for (int i = 0; i < M; ++i) {
            int u, v;
            cin >> u >> v;
            if (u == v) continue; // Ignore self-loops
            adj[u].push_back(v);
            adj[v].push_back(u);
        }
        // Deduplicate edges to simplify processing
        for (int i = 1; i <= N; ++i) {
            sort(adj[i].begin(), adj[i].end());
            adj[i].erase(unique(adj[i].begin(), adj[i].end()), adj[i].end());
        }
    }
}

// Prune function: Removes vertices from the cover if all their neighbors are already in the cover.
// This is a crucial step to minimize the vertex cover size.
void prune(vector<int>& cover, int& k) {
    vector<int> nodes;
    nodes.reserve(k);
    for (int i = 1; i <= N; ++i) {
        if (cover[i]) nodes.push_back(i);
    }
    // Random shuffle to vary the pruning order
    shuffle(nodes.begin(), nodes.end(), rng);

    for (int u : nodes) {
        if (!cover[u]) continue; // Already removed
        bool redundant = true;
        for (int v : adj[u]) {
            if (!cover[v]) {
                redundant = false;
                break;
            }
        }
        if (redundant) {
            cover[u] = 0;
            k--;
        }
    }
}

// Local Search: 1-exchange heuristic
// Tries to swap a vertex in the cover with a neighbor outside the cover.
// This preserves the validity but changes the configuration, potentially allowing further reductions.
void local_search(vector<int>& cover, int& k) {
    vector<int> nodes(N);
    iota(nodes.begin(), nodes.end(), 1);
    shuffle(nodes.begin(), nodes.end(), rng);

    for (int u : nodes) {
        if (cover[u]) {
            int count_out = 0;
            int v_out = -1;
            // Check neighbors not in cover
            for (int v : adj[u]) {
                if (!cover[v]) {
                    count_out++;
                    v_out = v;
                }
            }
            
            if (count_out == 1) {
                // If u has exactly one neighbor v outside S, we can swap u with v.
                // The edge (u, v) is covered by v. All other edges (u, w) are covered by w (since w must be in S).
                cover[u] = 0;
                cover[v_out] = 1;
                // Size k remains unchanged
            } else if (count_out == 0) {
                // Redundant vertex, can be removed (pruning usually handles this, but good to catch here)
                cover[u] = 0;
                k--;
            }
        }
    }
}

// Main solver function
void solve() {
    // Initialize best solution with a trivial full cover
    best_cover.assign(N + 1, 1);
    best_k = N;
    
    // Calculate initial degrees
    vector<int> initial_degrees(N + 1);
    for (int i = 1; i <= N; ++i) initial_degrees[i] = adj[i].size();

    vector<int> current_deg(N + 1);
    vector<int> cover(N + 1);
    
    // Buckets for O(1) retrieval of max degree vertex.
    // Size N+1 is sufficient since max degree <= N-1 (after deduplication).
    vector<vector<int>> buckets(N + 1); 

    clock_t start_time = clock();

    int iter = 0;
    // Iterate until time limit is close
    while (true) {
        if ((double)(clock() - start_time) / CLOCKS_PER_SEC > 1.95) break;
        iter++;

        // --- Construction Phase ---
        fill(cover.begin(), cover.end(), 0);
        for(int i=1; i<=N; ++i) current_deg[i] = initial_degrees[i];
        
        // Reset buckets
        for(int i=0; i<=N; ++i) buckets[i].clear();

        // Fill buckets with initial degrees, using a random order to break ties randomly
        vector<int> p(N);
        iota(p.begin(), p.end(), 1);
        shuffle(p.begin(), p.end(), rng);

        int max_d = 0;
        for (int i : p) {
            int d = current_deg[i];
            if (d > 0) {
                buckets[d].push_back(i);
                if (d > max_d) max_d = d;
            }
        }

        int current_k = 0;
        
        // Greedy loop: pick vertex with max dynamic degree
        while (max_d > 0) {
            if (buckets[max_d].empty()) {
                max_d--;
                continue;
            }
            
            // Randomize selection within the top bucket slightly to diversify search
            if (buckets[max_d].size() > 1 && (iter % 3 != 0)) {
                 int idx = uniform_int_distribution<int>(0, buckets[max_d].size() - 1)(rng);
                 swap(buckets[max_d][idx], buckets[max_d].back());
            }

            int u = buckets[max_d].back();
            buckets[max_d].pop_back();

            // Lazy update check: if actual degree is less than bucket index, skip
            if (current_deg[u] != max_d) continue;

            // Add u to cover
            cover[u] = 1;
            current_k++;
            current_deg[u] = 0; // Mark as removed

            // Update neighbors
            for (int v : adj[u]) {
                if (!cover[v] && current_deg[v] > 0) {
                    current_deg[v]--;
                    int new_d = current_deg[v];
                    if (new_d > 0) {
                        buckets[new_d].push_back(v);
                    }
                }
            }
        }

        // --- Improvement Phase ---
        // Initial pruning
        prune(cover, current_k);
        
        // Repeatedly apply local search and pruning
        for (int k_iter = 0; k_iter < 8; ++k_iter) {
             int prev_k = current_k;
             local_search(cover, current_k);
             prune(cover, current_k);
             // Break if no improvement stabilizes
             if (current_k == prev_k && k_iter > 2) break;
        }

        // --- Update Global Best ---
        if (current_k < best_k) {
            best_k = current_k;
            best_cover = cover;
        }
    }
}

int main() {
    // Fast I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    read_input();
    solve();

    // Output result
    for (int i = 1; i <= N; ++i) {
        cout << best_cover[i] << "\n";
    }
    return 0;
}