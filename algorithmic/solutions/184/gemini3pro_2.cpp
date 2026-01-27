#pragma GCC optimize("O3,unroll-loops")
#pragma GCC target("avx2,bmi,bmi2,lzcnt,popcnt")

#include <iostream>
#include <vector>
#include <algorithm>
#include <random>
#include <chrono>
#include <bitset>
#include <numeric>

using namespace std;

// Maximum constraints
const int MAXN = 1005;

// Global graph and state variables
int N, M;
bitset<MAXN> adj_mat[MAXN];
vector<int> adj_list[MAXN];
bitset<MAXN> current_set_bits;
int blocked[MAXN]; // blocked[v] count of neighbors of v in the current set

bitset<MAXN> best_set_bits;
int best_k = -1;

// Function to add a node to the current independent set
void add_node(int v) {
    current_set_bits.set(v);
    for (int u : adj_list[v]) {
        blocked[u]++;
    }
}

// Function to remove a node from the current independent set
void remove_node(int v) {
    current_set_bits.reset(v);
    for (int u : adj_list[v]) {
        blocked[u]--;
    }
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N >> M)) return 0;

    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        // 1-based indexing for input, consistent with bitset and arrays
        adj_mat[u].set(v);
        adj_mat[v].set(u);
        adj_list[u].push_back(v);
        adj_list[v].push_back(u);
    }

    auto start_time = chrono::high_resolution_clock::now();
    mt19937 rng(1337); 
    
    vector<int> p(N);
    iota(p.begin(), p.end(), 1);

    // Initial deterministic greedy solution (Min-Degree heuristic)
    {
        vector<int> sorted_p = p;
        sort(sorted_p.begin(), sorted_p.end(), [&](int a, int b){
            return adj_list[a].size() < adj_list[b].size();
        });
        
        current_set_bits.reset();
        fill(blocked, blocked + N + 1, 0);
        
        for (int v : sorted_p) {
            if (blocked[v] == 0) {
                add_node(v);
            }
        }
        
        if ((int)current_set_bits.count() > best_k) {
            best_k = current_set_bits.count();
            best_set_bits = current_set_bits;
        }
    }

    // Reuse vector for efficiency
    static vector<int> u_to_w[MAXN];

    // Main optimization loop (Restart + Randomized Greedy + Local Search)
    while (true) {
        auto curr_time = chrono::high_resolution_clock::now();
        chrono::duration<double> elapsed = curr_time - start_time;
        if (elapsed.count() > 1.95) break;

        // Reset state
        current_set_bits.reset();
        fill(blocked, blocked + N + 1, 0);
        
        // Randomize permutation for greedy initialization
        shuffle(p.begin(), p.end(), rng);
        
        // Build initial maximal independent set
        for (int v : p) {
            if (blocked[v] == 0) {
                add_node(v);
            }
        }
        
        int plateau_moves = 0;
        const int MAX_PLATEAU = 200;
        
        // Local Search phase
        while (true) {
            if (plateau_moves > MAX_PLATEAU) break;
            // Check time periodically inside the inner loop
            if ((plateau_moves & 31) == 0) {
                 auto t = chrono::high_resolution_clock::now();
                 if (chrono::duration<double>(t - start_time).count() > 1.98) break;
            }

            // Identify candidates
            // cand0: Vertices with 0 neighbors in S (can be added freely)
            // cand1: Vertices with 1 neighbor in S (potential for 1-for-2 swap)
            vector<int> cand0, cand1;
            cand0.reserve(N); cand1.reserve(N);
            
            for (int i = 1; i <= N; ++i) {
                if (!current_set_bits[i]) {
                    if (blocked[i] == 0) cand0.push_back(i);
                    else if (blocked[i] == 1) cand1.push_back(i);
                }
            }

            // Always add free vertices if any
            if (!cand0.empty()) {
                for (int v : cand0) {
                    if (blocked[v] == 0) add_node(v);
                }
                plateau_moves = 0;
                continue;
            }
            
            // Try (1,2)-swap: Remove 1 vertex u from S, add 2 vertices v, w
            // v, w must be neighbors of u, and not connected to each other, and have no other neighbors in S
            
            vector<int> used_u;
            used_u.reserve(N);
            
            // Map u -> list of valid w candidates
            for (int w : cand1) {
                int u = -1;
                for (int neighbor : adj_list[w]) {
                    if (current_set_bits[neighbor]) {
                        u = neighbor;
                        break;
                    }
                }
                if (u != -1) {
                    if (u_to_w[u].empty()) used_u.push_back(u);
                    u_to_w[u].push_back(w);
                }
            }
            
            bool improved = false;
            shuffle(cand1.begin(), cand1.end(), rng);
            
            // Try to find v and w for a swap
            for (int v : cand1) {
                int u = -1;
                for (int neighbor : adj_list[v]) {
                    if (current_set_bits[neighbor]) {
                        u = neighbor;
                        break;
                    }
                }
                
                if (u != -1) {
                    // Check other candidates w connected to the same u
                    for (int w : u_to_w[u]) {
                        if (w != v && !adj_mat[v][w]) {
                            // Perform (1,2)-swap
                            remove_node(u);
                            add_node(v);
                            add_node(w);
                            improved = true;
                            break;
                        }
                    }
                }
                if (improved) break;
            }
            
            // Clear mapping
            for (int u : used_u) u_to_w[u].clear();
            
            if (improved) {
                plateau_moves = 0;
                continue;
            }
            
            // Plateau move: (1,1)-swap
            // Pick a random vertex v with blocked=1, swap with its neighbor u
            // This helps escape local optima by changing the configuration without changing size
            if (!cand1.empty()) {
                int v = cand1[rng() % cand1.size()];
                int u = -1;
                for (int neighbor : adj_list[v]) {
                    if (current_set_bits[neighbor]) {
                        u = neighbor;
                        break;
                    }
                }
                if (u != -1) {
                    remove_node(u);
                    add_node(v);
                    plateau_moves++;
                } else {
                    plateau_moves++;
                }
            } else {
                // No moves possible
                break; 
            }
        }
        
        // Update global best
        int current_k = current_set_bits.count();
        if (current_k > best_k) {
            best_k = current_k;
            best_set_bits = current_set_bits;
        }
    }

    // Output results
    for (int i = 1; i <= N; ++i) {
        cout << (best_set_bits[i] ? 1 : 0) << "\n";
    }

    return 0;
}