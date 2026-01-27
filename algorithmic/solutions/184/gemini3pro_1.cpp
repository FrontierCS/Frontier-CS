#include <iostream>
#include <vector>
#include <algorithm>
#include <random>
#include <bitset>
#include <chrono>
#include <numeric>

using namespace std;

const int MAXN = 1005;
int N, M;
bitset<MAXN> adj[MAXN];
bitset<MAXN> current_s;
bitset<MAXN> best_s;
int current_s_size = 0;
int best_s_size = 0;

// Count of neighbors in S for each vertex
int neighbor_in_s_cnt[MAXN];

// Random number generator
mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

void add_node(int u) {
    if (current_s[u]) return;
    current_s[u] = 1;
    current_s_size++;
    // Update neighbors' counts
    for (int v = 1; v <= N; ++v) {
        if (adj[u][v]) {
            neighbor_in_s_cnt[v]++;
        }
    }
}

void remove_node(int u) {
    if (!current_s[u]) return;
    current_s[u] = 0;
    current_s_size--;
    // Update neighbors' counts
    for (int v = 1; v <= N; ++v) {
        if (adj[u][v]) {
            neighbor_in_s_cnt[v]--;
        }
    }
}

// Function to build a random maximal independent set
void build_random_greedy() {
    // Clear current solution
    current_s.reset();
    current_s_size = 0;
    fill(neighbor_in_s_cnt, neighbor_in_s_cnt + N + 1, 0);

    vector<int> p(N);
    iota(p.begin(), p.end(), 1);
    shuffle(p.begin(), p.end(), rng);

    for (int u : p) {
        if (neighbor_in_s_cnt[u] == 0) {
            add_node(u);
        }
    }
}

// Global buffer for candidates to avoid reallocation
vector<int> candidates_for[MAXN];

// Try to find a (1, 2) swap: remove 1 node u, add 2 nodes v1, v2
bool try_one_two_swap() {
    vector<int> nodes_in_s;
    nodes_in_s.reserve(current_s_size);
    
    for (int u = 1; u <= N; ++u) {
        candidates_for[u].clear();
        if (current_s[u]) {
            nodes_in_s.push_back(u);
        }
    }
    
    // Categorize potential replacements
    // Iterate all vertices, if neighbor count is 1, add to the list of its unique neighbor
    for (int v = 1; v <= N; ++v) {
        if (!current_s[v] && neighbor_in_s_cnt[v] == 1) {
            // Find the unique neighbor u
            for (int u : nodes_in_s) {
                if (adj[v][u]) {
                    candidates_for[u].push_back(v);
                    break; 
                }
            }
        }
    }
    
    // Randomize order of checking to diversify search
    shuffle(nodes_in_s.begin(), nodes_in_s.end(), rng);
    
    for (int u : nodes_in_s) {
        const vector<int>& cands = candidates_for[u];
        if (cands.size() < 2) continue;
        
        // Check if there are two nodes in cands that are not connected
        for (size_t i = 0; i < cands.size(); ++i) {
            for (size_t j = i + 1; j < cands.size(); ++j) {
                int v1 = cands[i];
                int v2 = cands[j];
                if (!adj[v1][v2]) {
                    // Found improvement!
                    remove_node(u);
                    add_node(v1);
                    add_node(v2);
                    return true;
                }
            }
        }
    }
    
    return false;
}

// 1-1 Swap (Plateau move)
// Returns true if a swap was performed.
bool random_one_one_swap() {
    vector<int> candidates;
    for (int v = 1; v <= N; ++v) {
        if (!current_s[v] && neighbor_in_s_cnt[v] == 1) {
            candidates.push_back(v);
        }
    }
    
    if (candidates.empty()) return false;
    
    // Pick random candidate
    int v = candidates[rng() % candidates.size()];
    
    // Find u (the unique neighbor in S)
    int u = -1;
    // We iterate 1..N or just check bits. Intersection is faster if we had bitset for S.
    // adj[v] & current_s
    bitset<MAXN> intersection = adj[v] & current_s;
    
    // Find the set bit
    // Using simple loop for compatibility
    for (int i = 1; i <= N; ++i) {
        if (intersection[i]) {
            u = i;
            break;
        }
    }
    
    if (u != -1) {
        remove_node(u);
        add_node(v);
        return true;
    }
    return false;
}

// Just add any node with 0 neighbors in S
bool fill_up() {
    bool added = false;
    vector<int> p(N);
    iota(p.begin(), p.end(), 1);
    shuffle(p.begin(), p.end(), rng);
    
    for (int v : p) {
        if (!current_s[v] && neighbor_in_s_cnt[v] == 0) {
            add_node(v);
            added = true;
        }
    }
    return added;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N >> M)) return 0;

    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u][v] = 1;
        adj[v][u] = 1;
    }

    auto start_time = chrono::steady_clock::now();
    
    best_s_size = -1;

    // Main optimization loop
    while (true) {
        auto curr_time = chrono::steady_clock::now();
        chrono::duration<double> elapsed = curr_time - start_time;
        if (elapsed.count() > 1.95) break;

        // Restart with greedy construction
        build_random_greedy();
        if (current_s_size > best_s_size) {
            best_s_size = current_s_size;
            best_s = current_s;
        }
        
        // Local Search Phase
        int stale_iter = 0;
        int max_stale = 50 + N/10; 

        while (true) {
            // Check time periodically
            if ((stale_iter & 31) == 0) {
                 if ((chrono::steady_clock::now() - start_time).count() * 1e-9 > 1.95) break;
            }

            bool improved = false;
            
            // 1. Try to fill up (Add nodes if possible)
            if (fill_up()) {
                improved = true;
                stale_iter = 0;
            }
            
            // 2. Try (1, 2) swap (Remove 1, Add 2)
            if (!improved && try_one_two_swap()) {
                improved = true;
                stale_iter = 0;
            }
            
            if (improved) {
                if (current_s_size > best_s_size) {
                    best_s_size = current_s_size;
                    best_s = current_s;
                }
                continue;
            }
            
            // 3. Plateau moves (1-1 swap) to escape local optima
            if (stale_iter < max_stale) {
                if (random_one_one_swap()) {
                    stale_iter++;
                } else {
                    // No possible moves
                    break;
                }
            } else {
                break;
            }
        }
        
        if (current_s_size > best_s_size) {
            best_s_size = current_s_size;
            best_s = current_s;
        }
    }

    for (int i = 1; i <= N; ++i) {
        cout << (best_s[i] ? 1 : 0) << "\n";
    }

    return 0;
}