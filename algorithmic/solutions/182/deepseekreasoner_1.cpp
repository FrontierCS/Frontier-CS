#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>
#include <chrono>

using namespace std;

// Global variables
int N, M;
vector<vector<int>> adj;

// Best solution found
vector<int> best_sol;
int best_size = 1e9;

// Current working solution
vector<int> current_sol; // 1 if in cover, 0 otherwise
int current_size = 0;
vector<int> loss; // loss[u] = number of neighbors of u which are NOT in S

// Candidate set for vertices in S with loss == 1 (potential swap candidates)
vector<int> cand_loss1;
vector<int> pos_loss1; // Maps vertex id to index in cand_loss1, -1 if not present

// Queue for pruning redundant vertices (loss == 0)
vector<int> q_zero;

mt19937 rng(1337);

// Helper to add a vertex to the candidate set
void add_cand1(int u) {
    if (pos_loss1[u] == -1) {
        pos_loss1[u] = cand_loss1.size();
        cand_loss1.push_back(u);
    }
}

// Helper to remove a vertex from the candidate set
void remove_cand1(int u) {
    if (pos_loss1[u] != -1) {
        int idx = pos_loss1[u];
        int last = cand_loss1.back();
        cand_loss1[idx] = last;
        pos_loss1[last] = idx;
        cand_loss1.pop_back();
        pos_loss1[u] = -1;
    }
}

// Construct an initial minimal vertex cover based on permutation p
void build_initial(const vector<int>& p) {
    fill(current_sol.begin(), current_sol.end(), 1);
    current_size = N;
    fill(loss.begin(), loss.end(), 0); 
    // Initially S=V, so all neighbors are in S => loss=0 for all
    
    cand_loss1.clear();
    fill(pos_loss1.begin(), pos_loss1.end(), -1);
    
    // Greedily remove redundant vertices (Minimal Vertex Cover construction)
    // Equivalent to greedy Maximal Independent Set on V \ S
    for (int u : p) {
        if (current_sol[u] && loss[u] == 0) {
            current_sol[u] = 0;
            current_size--;
            // Since u leaves S, neighbors' loss increases
            for (int v : adj[u]) {
                loss[v]++;
            }
        }
    }

    // Identify initial swap candidates (loss == 1)
    for (int i = 1; i <= N; i++) {
        if (current_sol[i]) {
            if (loss[i] == 1) add_cand1(i);
        }
    }
}

// Perform a (1,1) swap: remove u (in S), add w (not in S)
// Followed by pruning of any vertices that become redundant
void swap_vertices(int u, int w) {
    // 1. Remove u from S
    current_sol[u] = 0;
    // current_size decreases by 1
    remove_cand1(u);
    
    // Update neighbors of u: u is now outside, so their loss increases
    for (int v : adj[u]) {
        loss[v]++;
        if (current_sol[v]) {
            // Transitions: 
            // 2 -> 1: becomes candidate
            // 1 -> 2: stops being candidate
            if (loss[v] == 1) add_cand1(v);
            else if (loss[v] == 2) remove_cand1(v);
        }
    }

    // 2. Add w to S
    current_sol[w] = 1;
    // current_size increases by 1 (net change 0 so far)

    q_zero.clear();
    
    // Update neighbors of w: w is now inside, so their loss decreases
    for (int z : adj[w]) {
        loss[z]--;
        if (current_sol[z]) {
            // Transitions:
            // 1 -> 0: becomes redundant (prune)
            // 2 -> 1: becomes candidate
            if (loss[z] == 0) {
                q_zero.push_back(z);
                remove_cand1(z);
            } else if (loss[z] == 1) {
                add_cand1(z);
            }
        }
    }
    
    // Check w itself
    if (loss[w] == 0) q_zero.push_back(w);
    else if (loss[w] == 1) add_cand1(w);
    
    // 3. Chain pruning of redundant vertices
    int prune_idx = 0;
    while(prune_idx < q_zero.size()) {
        int z = q_zero[prune_idx++];
        if (!current_sol[z]) continue; // Already removed
        
        current_sol[z] = 0;
        current_size--; // Net reduction in size!
        remove_cand1(z);
        
        // Update neighbors of removed vertex z
        for (int k : adj[z]) {
            loss[k]++;
            if (current_sol[k]) {
                if (loss[k] == 1) add_cand1(k);
                else if (loss[k] == 2) remove_cand1(k);
            }
        }
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N >> M)) return 0;
    
    adj.resize(N + 1);
    for (int i = 0; i < M; i++) {
        int u, v;
        cin >> u >> v;
        if (u != v) {
            adj[u].push_back(v);
            adj[v].push_back(u);
        }
    }

    // Sort and remove duplicates for faster adjacency iteration
    for(int i=1; i<=N; ++i) {
        sort(adj[i].begin(), adj[i].end());
        adj[i].erase(unique(adj[i].begin(), adj[i].end()), adj[i].end());
    }

    // Init globals
    best_sol.assign(N + 1, 1);
    best_size = N;

    current_sol.resize(N + 1);
    loss.resize(N + 1);
    pos_loss1.assign(N + 1, -1);
    
    vector<int> p(N);
    iota(p.begin(), p.end(), 1);

    auto start_time = chrono::steady_clock::now();
    double time_limit = 1.95; 

    // Heuristic: Start with node permutation sorted by degree ascending
    // This tends to produce better Independent Sets (smaller Vertex Covers) in the greedy phase
    sort(p.begin(), p.end(), [&](int a, int b){
        return adj[a].size() < adj[b].size();
    });

    int iter = 0;
    while (true) {
        // Time check
        auto curr_time = chrono::steady_clock::now();
        if (chrono::duration<double>(curr_time - start_time).count() > time_limit) break;

        if (iter > 0) {
            // Random shuffle for diversity in restarts
            shuffle(p.begin(), p.end(), rng);
        }

        build_initial(p);
        
        if (current_size < best_size) {
            best_size = current_size;
            best_sol = current_sol;
        }

        // Local search loop
        // We repeatedly swap a vertex with loss 1 with its uncovered neighbor
        // generating perturbations that might allow further pruning
        int ls_iter = 0;
        int max_ls = 50000;
        if (N < 2000) max_ls = 100000;

        while (ls_iter < max_ls && !cand_loss1.empty()) {
            ls_iter++;
            
            // Pick a random candidate u with loss 1
            int idx = uniform_int_distribution<int>(0, cand_loss1.size() - 1)(rng);
            int u = cand_loss1[idx];

            // Find the unique neighbor w not in S
            int w = -1;
            for (int v : adj[u]) {
                if (!current_sol[v]) {
                    w = v;
                    break;
                }
            }
            
            if (w != -1) {
                swap_vertices(u, w);
            } else {
                // Should not happen if data structures are consistent
                remove_cand1(u);
            }

            if (current_size < best_size) {
                best_size = current_size;
                best_sol = current_sol;
            }
            
            // Periodically check time inside LS loop
            if ((ls_iter & 4095) == 0) {
                 if (chrono::duration<double>(chrono::steady_clock::now() - start_time).count() > time_limit) break;
            }
        }
        iter++;
    }

    for (int i = 1; i <= N; i++) {
        cout << best_sol[i] << "\n";
    }

    return 0;
}