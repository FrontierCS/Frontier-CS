#include <iostream>
#include <vector>
#include <algorithm>
#include <random>
#include <numeric>
#include <chrono>

using namespace std;

// Global variables for graph
int N, M;
vector<vector<int>> adj;
vector<int> degree;

// Random number generator
mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

// Structure to manage the Independent Set solution
struct Solution {
    vector<bool> in_set;
    int size;
    vector<int> conflicts; // conflicts[u] stores the number of neighbors of u currently in the set S

    Solution(int n) : in_set(n + 1, false), size(0), conflicts(n + 1, 0) {}

    // Add vertex u to the set S. Updates conflicts for neighbors.
    void add(int u) {
        if (in_set[u]) return;
        in_set[u] = true;
        size++;
        for (int v : adj[u]) {
            conflicts[v]++;
        }
    }

    // Remove vertex u from the set S. Updates conflicts for neighbors.
    void remove(int u) {
        if (!in_set[u]) return;
        in_set[u] = false;
        size--;
        for (int v : adj[u]) {
            conflicts[v]--;
        }
    }
    
    // Check if u can be added to S without violating independence property
    bool is_independent(int u) const {
        return conflicts[u] == 0;
    }
};

// Heuristic Construction: Randomized Min-Degree Greedy
// Repeatedly picks the vertex with the minimum degree in the remaining graph,
// adds it to the set, and removes it and its neighbors.
Solution construct_greedy() {
    Solution sol(N);
    vector<int> d = degree;
    vector<bool> active(N + 1, true);
    int active_cnt = N;
    
    while(active_cnt > 0) {
        int min_deg = 1e9;
        vector<int> min_candidates;
        
        // Scan for active nodes with minimum current degree
        for (int i = 1; i <= N; ++i) {
            if (!active[i]) continue;
            if (d[i] < min_deg) {
                min_deg = d[i];
                min_candidates.clear();
                min_candidates.push_back(i);
            } else if (d[i] == min_deg) {
                min_candidates.push_back(i);
            }
        }
        
        if (min_candidates.empty()) break;
        
        // Randomly pick one among the ties
        int u = min_candidates[rng() % min_candidates.size()];
        
        sol.add(u);
        
        // Identify nodes to remove (u and its neighbors)
        vector<int> to_remove;
        to_remove.reserve(adj[u].size() + 1);
        to_remove.push_back(u);
        for(int v : adj[u]) {
            if (active[v]) to_remove.push_back(v);
        }
        
        // Remove nodes and update degrees of their neighbors
        for(int x : to_remove) {
            if (!active[x]) continue;
            active[x] = false;
            active_cnt--;
            for (int w : adj[x]) {
                if (active[w]) {
                    d[w]--;
                }
            }
        }
    }
    
    // Greedy Expansion: Try to fill any remaining valid spots
    vector<int> p(N);
    iota(p.begin(), p.end(), 1);
    shuffle(p.begin(), p.end(), rng);
    for(int i : p) {
        if (!sol.in_set[i] && sol.is_independent(i)) {
            sol.add(i);
        }
    }
    
    return sol;
}

int main() {
    // Fast I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N >> M)) return 0;

    adj.resize(N + 1);
    degree.resize(N + 1, 0);
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
        degree[u]++;
        degree[v]++;
    }

    auto start_time = chrono::steady_clock::now();
    double time_limit = 1.95; // Seconds

    // Generate initial solution
    Solution best_sol = construct_greedy();
    Solution curr_sol = best_sol;

    // Iterated Local Search
    // Strategy: Perturb (force add a node, remove conflicts) -> Greedy Expand -> Accept/Reject
    vector<int> candidates;
    candidates.reserve(N);
    vector<int> conflicts_to_remove;
    conflicts_to_remove.reserve(N);

    long long iter = 0;
    
    while (true) {
        // Time check every 128 iterations
        if ((iter & 127) == 0) {
            auto now = chrono::steady_clock::now();
            if (chrono::duration<double>(now - start_time).count() > time_limit) break;
        }
        iter++;

        // 1. Perturbation: Force add a random vertex v NOT in current set
        int v = -1;
        // Try random sampling first for speed
        for(int k=0; k<20; ++k) {
            int r = (rng() % N) + 1;
            if (!curr_sol.in_set[r]) {
                v = r;
                break;
            }
        }
        // Fallback: collect all valid options if sampling fails
        if (v == -1) {
            vector<int> not_in;
            not_in.reserve(N - curr_sol.size);
            for(int i=1; i<=N; ++i) if(!curr_sol.in_set[i]) not_in.push_back(i);
            if (not_in.empty()) break; // Should not happen unless K=N
            v = not_in[rng() % not_in.size()];
        }

        // Identify neighbors of v that are in S
        conflicts_to_remove.clear();
        for (int u : adj[v]) {
            if (curr_sol.in_set[u]) {
                conflicts_to_remove.push_back(u);
            }
        }

        // Remove conflicting nodes and add v
        for (int u : conflicts_to_remove) curr_sol.remove(u);
        curr_sol.add(v);

        // 2. Greedy Expansion: Try to add any other nodes that fit
        candidates.clear();
        for (int i = 1; i <= N; ++i) {
            if (!curr_sol.in_set[i] && curr_sol.conflicts[i] == 0) {
                candidates.push_back(i);
            }
        }

        if (!candidates.empty()) {
            // Shuffle to add diversity
            if (candidates.size() > 1) {
                for (size_t i = 0; i < candidates.size(); ++i) {
                    size_t j = i + rng() % (candidates.size() - i);
                    swap(candidates[i], candidates[j]);
                }
            }
            // Add valid candidates
            for (int u : candidates) {
                if (curr_sol.conflicts[u] == 0) {
                    curr_sol.add(u);
                }
            }
        }

        // 3. Update Global Best
        if (curr_sol.size > best_sol.size) {
            best_sol = curr_sol;
        }

        // 4. Acceptance Criteria
        // If current solution degrades too much, revert to best.
        // Allowing small degradation (size - 1) helps escape local optima (Plateau search).
        bool reset = false;
        
        // Revert if strictly worse than best - 1
        if (curr_sol.size < best_sol.size - 1) reset = true;
        
        // Periodically reset to best to intensify search in good region
        if (iter % 2000 == 0) reset = true; 

        if (reset) {
            curr_sol = best_sol;
        }
    }

    // Output result
    for (int i = 1; i <= N; ++i) {
        cout << (best_sol.in_set[i] ? 1 : 0) << "\n";
    }

    return 0;
}