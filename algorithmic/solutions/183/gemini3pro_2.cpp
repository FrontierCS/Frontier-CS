#include <iostream>
#include <vector>
#include <algorithm>
#include <bitset>
#include <ctime>
#include <numeric>
#include <random>

using namespace std;

// Globals
const int MAXN = 10005;
int N, M;
vector<int> adj[MAXN];
bitset<MAXN> adj_mat[MAXN];
int degree[MAXN]; // Initial degrees

// For the best solution found
vector<int> best_solution;
int best_k = -1;

// Timing
clock_t start_time;

// Random number generator
mt19937 rng(1337);

void read_input() {
    if (!(cin >> N >> M)) return;
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v; // 0-based
        adj[u].push_back(v);
        adj[v].push_back(u);
        adj_mat[u][v] = 1;
        adj_mat[v][u] = 1;
        degree[u]++;
        degree[v]++;
    }
}

// Greedy Construction: Randomized Min-Degree Heuristic
// Returns a list of vertices in the Independent Set
vector<int> run_greedy() {
    vector<int> current_deg(N);
    vector<bool> removed(N, false);
    
    // Buckets for dynamic degrees
    // We use a vector of vectors as a lazy priority queue
    // buckets[d] stores vertices with degree d
    static vector<int> buckets[MAXN];
    for(int i=0; i<=N; ++i) buckets[i].clear();

    // Randomize initial order to break ties randomly
    vector<int> p(N);
    iota(p.begin(), p.end(), 0);
    shuffle(p.begin(), p.end(), rng);

    int min_d = MAXN;
    for (int i : p) {
        current_deg[i] = degree[i];
        buckets[current_deg[i]].push_back(i);
        if (current_deg[i] < min_d) min_d = current_deg[i];
    }
    
    // Ensure min_d is correct initially
    if (min_d > N) min_d = 0; 
    while (min_d < N && buckets[min_d].empty()) min_d++;

    vector<int> S;
    S.reserve(N);

    int remaining_vertices = N;
    
    while (remaining_vertices > 0) {
        // Find a valid vertex with minimum degree
        int u = -1;
        while (min_d < N) {
            if (buckets[min_d].empty()) {
                min_d++;
                continue;
            }
            // Pick from back (O(1))
            int cand = buckets[min_d].back();
            buckets[min_d].pop_back();
            
            if (!removed[cand] && current_deg[cand] == min_d) {
                u = cand;
                break;
            }
        }
        
        if (u == -1) break; // Should not happen if remaining > 0

        // Add u to S
        S.push_back(u);
        removed[u] = true;
        remaining_vertices--;

        // Remove u, its neighbors, and update neighbors of neighbors
        for (int v : adj[u]) {
            if (removed[v]) continue;
            
            removed[v] = true;
            remaining_vertices--;
            
            // v is removed, so its neighbors w lose a connection to v
            // This reduces the degree of w in the remaining subgraph
            for (int w : adj[v]) {
                if (!removed[w]) {
                    current_deg[w]--;
                    if (current_deg[w] < min_d) min_d = current_deg[w];
                    buckets[current_deg[w]].push_back(w);
                }
            }
        }
    }
    return S;
}

// Local Search: (1, 2)-swaps
// Attempts to find a vertex v in S such that removing v allows adding 2 vertices {u, w} from V \ S
// Returns true if an improvement was made
bool improve_via_swap(vector<int>& S, vector<bool>& in_set) {
    // 1. Compute "tightness" for all vertices NOT in S
    // tightness[u] = number of neighbors in S
    // We only care about u with tightness == 1
    
    static int tightness[MAXN];
    static int sole_neighbor[MAXN]; // If tightness is 1, who is the neighbor in S?
    
    // Initialize
    fill(tightness, tightness + N, 0);
    
    // Compute tightness by iterating neighbors of S
    for (int v : S) {
        for (int u : adj[v]) {
            if (!in_set[u]) {
                if (tightness[u] == 0) sole_neighbor[u] = v;
                else sole_neighbor[u] = -1; // If > 1, irrelevant
                tightness[u]++;
            }
        }
    }
    
    // Group candidates by their sole neighbor in S
    // candidates[v] = list of u such that u is not in S and N(u) \cap S = {v}
    static vector<int> candidates[MAXN];
    for (int v : S) candidates[v].clear();
    
    bool possible = false;
    for (int u = 0; u < N; ++u) {
        if (!in_set[u] && tightness[u] == 1) {
            int v = sole_neighbor[u];
            if (v != -1) {
                candidates[v].push_back(u);
                if (candidates[v].size() >= 2) possible = true;
            }
        }
    }

    if (!possible) return false;

    // Check for any independent pair in candidates[v]
    for (int v : S) {
        if (candidates[v].size() < 2) continue;
        
        const auto& cands = candidates[v];
        // Check pairs
        for (size_t i = 0; i < cands.size(); ++i) {
            for (size_t j = i + 1; j < cands.size(); ++j) {
                int u1 = cands[i];
                int u2 = cands[j];
                // Check if edge exists between u1 and u2
                if (!adj_mat[u1][u2]) {
                    // Found valid swap!
                    // Remove v, add u1, u2
                    in_set[v] = false;
                    in_set[u1] = true;
                    in_set[u2] = true;
                    
                    // Update S vector
                    for (size_t k = 0; k < S.size(); ++k) {
                        if (S[k] == v) {
                            S[k] = u1;
                            break;
                        }
                    }
                    S.push_back(u2);
                    return true;
                }
            }
        }
    }
    
    return false;
}

void solve() {
    start_time = clock();
    read_input();
    
    // Initial solution
    best_k = -1;
    
    int iter = 0;
    // Iterate until time limit is approached
    while (true) {
        iter++;
        // Check time budget (1.95s safe margin for 2.0s limit)
        double elapsed = (double)(clock() - start_time) / CLOCKS_PER_SEC;
        if (elapsed > 1.95) break; 
        if (iter > 1 && elapsed > 1.9) break; // Heuristic break

        // Generate a constructive solution
        vector<int> S = run_greedy();
        vector<bool> in_set(N, false);
        for(int x : S) in_set[x] = true;
        
        // Hill Climbing with (1,2)-swaps
        while (true) {
            // Check time inside the potentially expensive loop
            if ((iter % 5 == 0) && (double)(clock() - start_time) / CLOCKS_PER_SEC > 1.95) break;
            
            if (!improve_via_swap(S, in_set)) {
                break; // Local optimum reached
            }
        }
        
        if ((int)S.size() > best_k) {
            best_k = S.size();
            best_solution = S;
        }
    }
    
    // Output
    // If somehow loop didn't run (unlikely), best_solution might be empty if not handled.
    // The loop condition ensures at least one run if time permits, but if time is super tight at start?
    // With 2s limit, at least one run is guaranteed.
    
    vector<int> res(N, 0);
    if (best_k != -1) {
        for (int x : best_solution) res[x] = 1;
    }
    
    for (int i = 0; i < N; ++i) {
        cout << res[i] << "\n";
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    solve();
    return 0;
}