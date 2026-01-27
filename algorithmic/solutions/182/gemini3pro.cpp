#include <iostream>
#include <vector>
#include <algorithm>
#include <ctime>
#include <cstdlib>

using namespace std;

const int MAXN = 10005;

int N, M;
vector<int> adj[MAXN];
bool in_cover[MAXN];
int loss_val[MAXN]; // loss[v]: number of neighbors of v NOT in cover
int deg[MAXN];      // Dynamic degree for greedy
int tabu[MAXN];

void fast_io() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
}

// Simple LCG random
unsigned int rand_state = 12345;
int my_rand() {
    rand_state = rand_state * 1103515245 + 12345;
    return (rand_state / 65536) % 32768;
}

int main() {
    fast_io();
    if (!(cin >> N >> M)) return 0;

    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    // --- Step 1: Greedy Initialization ---
    // Calculate initial degrees
    for (int i = 1; i <= N; ++i) {
        deg[i] = adj[i].size();
        in_cover[i] = false;
    }

    // Buckets for O(M) greedy
    static vector<int> buckets[MAXN];
    int max_deg = 0;
    for (int i = 1; i <= N; ++i) {
        if (deg[i] > max_deg) max_deg = deg[i];
        buckets[deg[i]].push_back(i);
    }

    int current_m = M; 
    int ptr = max_deg;
    while (current_m > 0) {
        while (ptr > 0 && buckets[ptr].empty()) ptr--;
        if (ptr <= 0 && current_m > 0) break; // Should not happen

        int v = buckets[ptr].back();
        buckets[ptr].pop_back();

        if (in_cover[v]) continue;
        if (deg[v] != ptr) continue; // Stale

        in_cover[v] = true;
        current_m -= deg[v];
        deg[v] = 0;

        for (int u : adj[v]) {
            if (!in_cover[u]) {
                deg[u]--;
                if (deg[u] >= 0) buckets[deg[u]].push_back(u);
            }
        }
    }

    // --- Step 2: Calculate Loss ---
    for (int i = 1; i <= N; ++i) {
        int c = 0;
        for (int n : adj[i]) {
            if (!in_cover[n]) c++;
        }
        loss_val[i] = c;
    }

    // --- Step 3: Initial Pruning ---
    // Remove redundant vertices (all neighbors covered by others)
    static int q_rem[MAXN];
    int q_h = 0, q_t = 0;

    for (int i = 1; i <= N; ++i) {
        if (in_cover[i] && loss_val[i] == 0) {
            q_rem[q_t++] = i;
        }
    }

    while(q_h < q_t){
        int v = q_rem[q_h++];
        if (!in_cover[v]) continue;
        // Logic: if loss is 0, we can remove. 
        // Note: loss might have increased if neighbors were removed before processing v.
        if (loss_val[v] != 0) continue; 

        in_cover[v] = false;
        for (int n : adj[v]) {
            loss_val[n]++;
            // If neighbor becomes redundant? Impossible, loss increases.
            // But if neighbor was not in cover, its loss increases, irrelevant.
        }
    }

    // --- Step 4: Local Search ---
    int iter = 0;
    clock_t start_clock = clock();
    double time_limit = 1.95; 

    while ((double)(clock() - start_clock) / CLOCKS_PER_SEC < time_limit) {
        iter++;
        bool improved = false;
        
        int start_idx = my_rand() % N + 1;
        // Iterate to find a vertex u not in S to add
        // We hope adding u allows removing >= 2 vertices (or 1 for swap)
        for (int k = 0; k < N; ++k) {
            int u = (start_idx + k - 1) % N + 1;
            if (in_cover[u]) continue;
            if (tabu[u] > iter) continue;

            // Calculate gain: how many neighbors v \in S would have loss become 0?
            // loss[v]==1 means u is the only outside neighbor. Adding u makes loss[v]=0.
            int gain = 0;
            for (int v : adj[u]) {
                if (in_cover[v] && loss_val[v] == 1) {
                    gain++;
                }
            }

            if (gain >= 2) {
                // Apply move: Add u
                in_cover[u] = true;
                for (int n : adj[u]) loss_val[n]--;

                // Identify candidates for removal (loss == 0)
                q_h = 0; q_t = 0;
                
                // Only u's neighbors could have loss dropped to 0
                for (int n : adj[u]) {
                    if (in_cover[n] && loss_val[n] == 0) {
                        q_rem[q_t++] = n;
                    }
                }

                // Process removal queue
                while(q_h < q_t){
                    int v = q_rem[q_h++];
                    if (!in_cover[v]) continue;
                    if (loss_val[v] != 0) continue; // Safety check for independent set

                    in_cover[v] = false;
                    tabu[v] = iter + 3 + (my_rand() % 5);
                    
                    for (int n : adj[v]) {
                        loss_val[n]++;
                        // Cascading redundancy check
                        if (in_cover[n] && loss_val[n] == 0) {
                             q_rem[q_t++] = n;
                        }
                    }
                }

                improved = true;
                break; // Restart scan
            }
        }

        if (improved) continue;

        // Try Random Swap (Gain == 1)
        // Limit attempts to avoid wasting time
        int attempts = 50; 
        while(attempts--) {
            int u = my_rand() % N + 1;
            if (in_cover[u]) continue;
            if (tabu[u] > iter) continue;

            int gain = 0;
            for (int v : adj[u]) {
                if (in_cover[v] && loss_val[v] == 1) {
                    gain++;
                    if (gain > 1) break;
                }
            }
            
            if (gain == 1) {
                // Execute Swap (add u, remove redundant neighbors)
                in_cover[u] = true;
                for (int n : adj[u]) loss_val[n]--;
                
                q_h = 0; q_t = 0;
                for (int n : adj[u]) {
                    if (in_cover[n] && loss_val[n] == 0) {
                        q_rem[q_t++] = n;
                    }
                }

                while(q_h < q_t){
                    int v = q_rem[q_h++];
                    if (!in_cover[v]) continue;
                    if (loss_val[v] != 0) continue;

                    in_cover[v] = false;
                    tabu[v] = iter + 3 + (my_rand() % 5);
                    
                    for (int n : adj[v]) {
                        loss_val[n]++;
                        if (in_cover[n] && loss_val[n] == 0) {
                             q_rem[q_t++] = n;
                        }
                    }
                }
                break; // Move done
            }
        }
    }

    for (int i = 1; i <= N; ++i) {
        cout << (in_cover[i] ? 1 : 0) << "\n";
    }

    return 0;
}