#include <iostream>
#include <vector>
#include <bitset>
#include <algorithm>
#include <chrono>
#include <random>

using namespace std;

// Define constraints
const int MAXN = 1005;

// Global variables to store graph and best solution
int N, M;
bitset<MAXN> adj[MAXN];
vector<int> best_clique;

// Timer setup
auto start_time = chrono::high_resolution_clock::now();

double get_time() {
    auto now = chrono::high_resolution_clock::now();
    return chrono::duration<double>(now - start_time).count();
}

int main() {
    // Fast I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N >> M)) return 0;

    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u][v] = 1;
        adj[v][u] = 1;
    }

    // Random number generator
    mt19937 rng(1337);

    // 1. Initial Deterministic Greedy (Degree Heuristic)
    {
        vector<int> p(N);
        for(int i=0; i<N; ++i) p[i] = i + 1;
        
        // Sort vertices by degree descending
        sort(p.begin(), p.end(), [](int a, int b){
            return adj[a].count() > adj[b].count();
        });

        vector<int> current_clique;
        bitset<MAXN> candidates;
        
        // Initialize candidates to all vertices 1..N
        candidates.set(); 
        for(int i=N+1; i<MAXN; ++i) candidates[i] = 0; 
        candidates[0] = 0;

        for (int u : p) {
            if (candidates[u]) {
                current_clique.push_back(u);
                candidates &= adj[u];
            }
        }
        if (current_clique.size() > best_clique.size()) {
            best_clique = current_clique;
        }
    }

    // 2. Randomized Iterative Search
    // Run until close to time limit (leave 0.05s buffer)
    while (get_time() < 1.95) {
        vector<int> current_clique;
        bitset<MAXN> candidates;
        
        // Strategy Selection: Perturbation vs Restart
        bool perturb = false;
        if (!best_clique.empty()) {
            // 50% chance to perturb the best solution found so far
            if (rng() % 100 < 50) perturb = true;
        }

        if (perturb) {
            current_clique = best_clique;
            // Remove a small random number of vertices (1 to 3)
            int remove_cnt = 1 + (rng() % 3);
            if (remove_cnt >= (int)current_clique.size()) remove_cnt = (int)current_clique.size() - 1;
            
            if (remove_cnt > 0) {
                for (int k = 0; k < remove_cnt; ++k) {
                    int idx = rng() % current_clique.size();
                    swap(current_clique[idx], current_clique.back());
                    current_clique.pop_back();
                }
            }
            
            // Rebuild candidates based on the remaining clique
            // Start with all 1s, intersect with neighbors of all clique members
            candidates.set();
            for(int i=N+1; i<MAXN; ++i) candidates[i] = 0;
            candidates[0] = 0;
            
            for (int u : current_clique) {
                candidates &= adj[u];
            }
        } else {
            // Random Restart
            // Pick a random starting vertex
            int start_node = 1 + (rng() % N);
            current_clique.push_back(start_node);
            
            // Candidates are just neighbors of start_node
            candidates = adj[start_node];
        }

        // Greedily extend the clique
        while (true) {
            // Gather all current candidate vertices
            vector<int> potential_nodes;
            // Iterating 1 to N is fast enough
            for (int i = 1; i <= N; ++i) {
                if (candidates[i]) {
                    potential_nodes.push_back(i);
                }
            }

            if (potential_nodes.empty()) break;

            // Select the best candidate
            // Heuristic: Candidate with the highest degree within the current candidate set
            // To save time, we sample a subset if potential_nodes is large
            int sample_size = min((int)potential_nodes.size(), 40);
            
            int best_v = -1;
            int max_deg = -1;

            for (int k = 0; k < sample_size; ++k) {
                // Pick a random index from the remaining unsampled part
                int ridx = k + (rng() % (potential_nodes.size() - k));
                swap(potential_nodes[k], potential_nodes[ridx]);
                
                int v = potential_nodes[k];
                // Calculate degree in the induced subgraph of candidates
                int deg = (int)(candidates & adj[v]).count();
                
                if (deg > max_deg) {
                    max_deg = deg;
                    best_v = v;
                }
            }

            // Add best candidate to clique
            if (best_v != -1) {
                current_clique.push_back(best_v);
                candidates &= adj[best_v];
            } else {
                break;
            }
        }

        // Update global best
        if (current_clique.size() > best_clique.size()) {
            best_clique = current_clique;
        }
    }

    // Output solution
    vector<int> result(N + 1, 0);
    for (int u : best_clique) {
        result[u] = 1;
    }

    for (int i = 1; i <= N; ++i) {
        cout << result[i] << "\n";
    }

    return 0;
}