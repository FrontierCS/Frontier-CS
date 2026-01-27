#include <iostream>
#include <vector>
#include <algorithm>
#include <numeric>
#include <chrono>

using namespace std;

// Maximum number of vertices as per constraints
const int MAXN = 10005;

// Graph representation
vector<int> adj[MAXN];
// conflict_cnt[u] stores the number of neighbors of u that are currently in the Independent Set S
int conflict_cnt[MAXN]; 
// in_set[u] is true if u is in S
bool in_set[MAXN];
int N, M;

// Best solution found so far
bool best_in_set[MAXN];
int best_k = 0;
int current_k = 0;

// Fast Random Number Generator
struct SplitMix64 {
    unsigned long long s;
    unsigned long long next() {
        unsigned long long z = (s += 0x9e3779b97f4a7c15);
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9;
        z = (z ^ (z >> 27)) * 0x94d049bb133111eb;
        return z ^ (z >> 31);
    }
};
SplitMix64 rng_gen;

// Returns random integer in [0, n-1]
int get_rand(int n) {
    return rng_gen.next() % n;
}

// Add vertex u to Independent Set S
// Precondition: u is not in S and conflict_cnt[u] == 0
void add(int u) {
    in_set[u] = true;
    current_k++;
    for (int v : adj[u]) {
        conflict_cnt[v]++;
    }
}

// Remove vertex u from Independent Set S
// Precondition: u is in S
void remove(int u) {
    in_set[u] = false;
    current_k--;
    for (int v : adj[u]) {
        conflict_cnt[v]--;
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
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    // Seed the RNG
    rng_gen.s = chrono::steady_clock::now().time_since_epoch().count();

    // 1. Initial Greedy Construction
    // Randomize the order of vertices to process
    vector<int> p(N);
    iota(p.begin(), p.end(), 1);
    // Fisher-Yates shuffle
    for(int i = N - 1; i > 0; --i) {
        int j = get_rand(i + 1);
        swap(p[i], p[j]);
    }

    // Simple greedy: add if no neighbors are in set
    for (int u : p) {
        if (conflict_cnt[u] == 0) {
            add(u);
        }
    }

    // Store the initial result
    best_k = current_k;
    for (int i = 1; i <= N; ++i) best_in_set[i] = in_set[i];

    // 2. Local Search with Random Kicks (Iterated Local Search)
    auto start_time = chrono::steady_clock::now();
    double time_limit = 1.90; // Slightly under 2.0s to be safe

    long long iter = 0;
    int stagnation = 0;
    int stagnation_limit = N * 10; 

    while (true) {
        iter++;
        
        // Periodically check time limit (every 4096 iterations)
        if ((iter & 4095) == 0) {
            auto curr = chrono::steady_clock::now();
            chrono::duration<double> diff = curr - start_time;
            if (diff.count() > time_limit) break;
        }

        // Perturbation: If stuck in local optima for too long, kick the solution
        if (stagnation > stagnation_limit) {
            // Remove a small number of vertices randomly
            int k_kick = 2 + (best_k / 50); // Heuristic: ~2% of set size
            if (k_kick > 20) k_kick = 20;
            
            for(int i = 0; i < k_kick; ++i) {
                if (current_k == 0) break;
                // Find a random vertex currently in S
                int v;
                int tries = 0;
                do {
                    v = get_rand(N) + 1;
                    tries++;
                } while (!in_set[v] && tries < 20);
                
                if (in_set[v]) remove(v);
            }
            stagnation = 0; // Reset stagnation after kick
        }

        // Select a random vertex
        int u = get_rand(N) + 1;

        if (in_set[u]) {
            // Already in set, skip
            continue;
        }

        // Try to add u
        if (conflict_cnt[u] == 0) {
            // Case 1: No conflicts. We can add u directly to increase size.
            add(u);
            if (current_k > best_k) {
                best_k = current_k;
                for (int i = 1; i <= N; ++i) best_in_set[i] = in_set[i];
                stagnation = 0; // Reset stagnation on improvement
            }
        } else if (conflict_cnt[u] == 1) {
            // Case 2: Exactly 1 conflict. We can swap u with its neighbor v.
            // This maintains the size but moves to a neighbor solution (plateau search).
            int v = -1;
            // Find the unique neighbor in S
            for (int nb : adj[u]) {
                if (in_set[nb]) {
                    v = nb;
                    break;
                }
            }
            if (v != -1) {
                remove(v);
                add(u);
            }
        } 
        // Case 3: conflict_cnt >= 2. Ignore (requires removing 2+ to add 1, reducing size).
        
        stagnation++;
    }

    // Output the best solution found
    for (int i = 1; i <= N; ++i) {
        cout << (best_in_set[i] ? 1 : 0) << "\n";
    }

    return 0;
}