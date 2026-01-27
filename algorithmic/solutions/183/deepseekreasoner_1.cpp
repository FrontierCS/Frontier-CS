/*
 Maximum Independent Set Heuristic Solution
 Approach: Iterated Local Search with Tabu mechanism and (1,2)-swap capability via force-add and kernels.
*/
#include <iostream>
#include <vector>
#include <algorithm>
#include <random>
#include <chrono>
#include <numeric>

using namespace std;

// Constants and Globals
const int MAXN = 10005;
vector<int> adj[MAXN];
bool in_set[MAXN];          // Current solution status
int tightness[MAXN];        // Number of neighbors currently in S
int pos_in_set[MAXN];       // Position in the sets[k] vector for O(1) removal

// Sets for tightness 0, 1, 2. 
// sets[k] contains vertices v NOT in S such that tightness[v] == k.
// We maintain these to quickly find candidate moves.
vector<int> sets[3]; 

int N, M;
int current_k = 0;

// Tabu search arrays
int tabu_add_until[MAXN];
int tabu_remove_until[MAXN];
long long iterations = 0;

// Best solution tracking
bool best_in_set[MAXN];
int best_k = -1;

// RNG
mt19937 rng(1337);

// --- Set Management Functions ---

// Add vertex v to sets[t]
void add_to_set_vec(int v, int t) {
    if (t >= 3) return;
    pos_in_set[v] = sets[t].size();
    sets[t].push_back(v);
}

// Remove vertex v from sets[t]
void remove_from_set_vec(int v, int t) {
    if (t >= 3) return;
    int last = sets[t].back();
    int idx = pos_in_set[v];
    sets[t][idx] = last;
    pos_in_set[last] = idx;
    sets[t].pop_back();
}

// Update tightness of vertex v by delta
void update_tightness(int v, int delta) {
    // We only track vertices NOT in S in the sets[] vectors.
    // If v is in S, we update tightness value but don't move it between sets.
    if (!in_set[v]) {
        int old_t = tightness[v];
        int new_t = old_t + delta;
        tightness[v] = new_t;
        if (old_t < 3) remove_from_set_vec(v, old_t);
        if (new_t < 3) add_to_set_vec(v, new_t);
    } else {
        tightness[v] += delta;
    }
}

// Add vertex v to Independent Set S
void add_node(int v) {
    in_set[v] = true;
    current_k++;
    // v is no longer a candidate outside S, remove from sets
    int t = tightness[v];
    if (t < 3) remove_from_set_vec(v, t);
    
    // Neighbors of v now have one more neighbor in S
    for (int u : adj[v]) {
        update_tightness(u, 1);
    }
}

// Remove vertex v from Independent Set S
void remove_node(int v) {
    in_set[v] = false;
    current_k--;
    // v is now a candidate outside S with tightness equal to its current tightness counter
    int t = tightness[v];
    if (t < 3) add_to_set_vec(v, t);
    
    // Neighbors of v now have one less neighbor in S
    for (int u : adj[v]) {
        update_tightness(u, -1);
    }
}

// Greedily add any nodes with 0 tightness (free improvements)
void process_tightness0() {
    // While there are candidates with 0 conflicts
    while (!sets[0].empty()) {
        int v = sets[0].back();
        // Since logic might push same node if tightness fluctuates (though guarded), 
        // we check in_set.
        if (in_set[v]) {
            remove_from_set_vec(v, 0);
            continue;
        }
        // add_node will remove v from sets[0]
        add_node(v);
    }
}

// Force add v into S, removing any conflicting neighbors
void force_add(int v) {
    // 1. Identify neighbors in S
    vector<int> conflict;
    conflict.reserve(tightness[v]);
    for (int u : adj[v]) {
        if (in_set[u]) conflict.push_back(u);
    }
    
    // 2. Remove conflicts
    for (int u : conflict) {
        remove_node(u);
        // Tabu logic: don't add u back for some time
        int tenure = 3 + (rng() % 10); // Short tenure
        tabu_add_until[u] = iterations + tenure;
    }
    
    // 3. Add v
    add_node(v);
    // Tabu logic: don't remove v for some time
    int tenure = 3 + (rng() % 10);
    tabu_remove_until[v] = iterations + tenure;
    
    // 4. Greedy cleanup (Kernelization / 1-opt)
    // Any node that became free (tightness 0) due to removals is added.
    process_tightness0();
}

void save_best() {
    if (current_k > best_k) {
        best_k = current_k;
        for (int i = 1; i <= N; i++) best_in_set[i] = in_set[i];
    }
}

// Initialization: Random Permutation Greedy
void initialize() {
    for (int i = 1; i <= N; i++) {
        in_set[i] = false;
        tightness[i] = 0;
        tabu_add_until[i] = 0;
        tabu_remove_until[i] = 0;
    }
    for (int i = 0; i < 3; i++) sets[i].clear();
    current_k = 0;
    
    // Initially all vertices are outside S with tightness 0
    for (int i = 1; i <= N; i++) {
        add_to_set_vec(i, 0);
    }
    
    // Random greedy via permutation
    vector<int> p(N);
    iota(p.begin(), p.end(), 1);
    shuffle(p.begin(), p.end(), rng);
    
    for (int v : p) {
        if (!in_set[v] && tightness[v] == 0) {
            add_node(v);
        }
    }
    save_best();
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N >> M)) return 0;
    for (int i = 0; i < M; i++) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    auto start_time = chrono::high_resolution_clock::now();
    double time_limit = 1.95; 

    initialize();
    
    // Main Optimization Loop
    while (true) {
        iterations++;
        // Check time every 1024 iterations to reduce overhead
        if ((iterations & 1023) == 0) {
           auto curr_time = chrono::high_resolution_clock::now();
           chrono::duration<double> elapsed = curr_time - start_time;
           if (elapsed.count() > time_limit) break;
        }

        int v = -1;

        // Priority 1: Pick vertex with tightness 1 (Swap move)
        if (!sets[1].empty()) {
            // Try random candidates to find non-tabu
            int attempts = 5;
            while (attempts--) {
                int idx = rng() % sets[1].size();
                int cand = sets[1][idx];
                if (tabu_add_until[cand] <= iterations) {
                    v = cand;
                    break;
                }
            }
            // Aspiration: sometimes pick even if tabu or just pick random if failed
            if (v == -1 && (rng() % 10 == 0)) {
                v = sets[1][rng() % sets[1].size()];
            }
        }
        
        // Priority 2: Pick vertex with tightness 2 (Kick move)
        // Helps escape local optima
        if (v == -1 && !sets[2].empty()) {
             if (rng() % 50 == 0) {
                int idx = rng() % sets[2].size();
                int cand = sets[2][idx];
                if (tabu_add_until[cand] <= iterations) {
                    v = cand;
                }
             }
        }
        
        // Priority 3: Random perturbation (Force any random vertex)
        if (v == -1) {
             // Just pick a random vertex from the graph that is NOT in S
             int attempts = 20;
             while (attempts--) {
                 int r = (rng() % N) + 1;
                 if (!in_set[r]) {
                     if (tabu_add_until[r] <= iterations) {
                         v = r;
                         break;
                     }
                 }
             }
        }

        if (v != -1) {
            force_add(v);
            save_best();
        } else {
            // Deadlock breaking: Soft Restart
            int k_remove = max(1, current_k / 20); // Remove ~5%
            for(int k=0; k<k_remove; ++k) {
                 int r = (rng() % N) + 1;
                 if (in_set[r]) {
                     remove_node(r);
                     tabu_add_until[r] = iterations + 10; 
                 }
            }
            process_tightness0();
        }
    }

    for (int i = 1; i <= N; i++) {
        cout << (best_in_set[i] ? 1 : 0) << "\n";
    }

    return 0;
}