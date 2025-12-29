#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <numeric>
#include <set>

using namespace std;

// Global variables
int N, M, K;
double EPS;
int GLOBAL_MAX_SIZE;
vector<vector<int>> adj;
vector<int> partition_labels;

// Scratchpads for recursion to avoid reallocation
vector<int> visited_token;
int token_counter = 0;
vector<int> bfs_visited;
int bfs_token = 0;

vector<int> current_part; // 0 or 1
vector<int> gains;
vector<bool> locked;

void solve_recursive(const vector<int>& nodes, int k_sub, int offset) {
    if (nodes.empty()) return;
    
    // Base case: if k_sub is 1, assign all nodes to the current partition offset
    if (k_sub == 1) {
        for (int u : nodes) {
            partition_labels[u] = offset;
        }
        return;
    }

    int k_half = k_sub / 2;
    // Calculate max capacity for one branch of the split
    // The constraint applies to final parts, so a branch leading to k_half parts 
    // can hold at most k_half * GLOBAL_MAX_SIZE
    long long max_cap = (long long)k_half * GLOBAL_MAX_SIZE;
    
    // Mark nodes participating in this subproblem
    token_counter++;
    for (int u : nodes) visited_token[u] = token_counter;

    // --- Initial Split using BFS ---
    // Initialize all to 1 (Right partition)
    for (int u : nodes) current_part[u] = 1;

    int target_left = nodes.size() / 2;
    int cur_left = 0;
    
    bfs_token++;
    // BFS to fill Left partition (0)
    int search_idx = 0;
    vector<int> q;
    q.reserve(nodes.size());

    // Iterate to handle disconnected components within the subgraph
    while (cur_left < target_left && search_idx < nodes.size()) {
        if (bfs_visited[nodes[search_idx]] == bfs_token) {
            search_idx++;
            continue;
        }
        
        q.clear();
        q.push_back(nodes[search_idx]);
        bfs_visited[nodes[search_idx]] = bfs_token;
        int head = 0;
        
        while(head < q.size() && cur_left < target_left) {
            int u = q[head++];
            current_part[u] = 0;
            cur_left++;
            
            for (int v : adj[u]) {
                // Visit only nodes in the current subproblem and not yet visited in this BFS
                if (visited_token[v] == token_counter && bfs_visited[v] != bfs_token) {
                    bfs_visited[v] = bfs_token;
                    q.push_back(v);
                }
            }
        }
        search_idx++;
    }

    // --- Fiduccia-Mattheyses (FM) Refinement ---
    // Only refine if we have enough nodes
    if (nodes.size() > 2) {
        int passes = 2; // Limited passes for efficiency
        
        for (int pass = 0; pass < passes; ++pass) {
            // Compute initial gains for this pass
            // Gain = (external edges) - (internal edges)
            for (int u : nodes) {
                int g = 0;
                int my_p = current_part[u];
                for (int v : adj[u]) {
                    if (visited_token[v] == token_counter) {
                        if (current_part[v] != my_p) g++;
                        else g--;
                    }
                }
                gains[u] = g;
                locked[u] = false;
            }
            
            // Priority queues for max gain
            // Store {-gain, u} to simulate max-heap with std::set
            set<pair<int, int>> moves[2];
            int s0 = 0, s1 = 0;
            for (int u : nodes) {
                if (current_part[u] == 0) {
                    s0++;
                    moves[0].insert({-gains[u], u});
                } else {
                    s1++;
                    moves[1].insert({-gains[u], u});
                }
            }
            
            int best_cut_delta = 0;
            int current_cut_delta = 0;
            int best_move_idx = -1;
            vector<int> move_history;
            move_history.reserve(nodes.size());
            
            // Perform moves
            int limit_moves = nodes.size(); 
            
            for (int step = 0; step < limit_moves; ++step) {
                // Check balance constraints for moves
                bool can01 = (s0 > 0 && (s1 + 1) <= max_cap);
                bool can10 = (s1 > 0 && (s0 + 1) <= max_cap);
                
                int side = -1; // 0: move 0->1, 1: move 1->0
                
                if (can01 && can10) {
                    int g0 = -moves[0].begin()->first;
                    int g1 = -moves[1].begin()->first;
                    if (g0 >= g1) side = 0;
                    else side = 1;
                } else if (can01) {
                    side = 0;
                } else if (can10) {
                    side = 1;
                } else {
                    break; // No valid moves
                }
                
                int u, g;
                if (side == 0) {
                    auto it = moves[0].begin();
                    g = -it->first;
                    u = it->second;
                    moves[0].erase(it);
                    s0--; s1++;
                } else {
                    auto it = moves[1].begin();
                    g = -it->first;
                    u = it->second;
                    moves[1].erase(it);
                    s1--; s0++;
                }
                
                current_part[u] = 1 - current_part[u];
                locked[u] = true;
                current_cut_delta -= g;
                move_history.push_back(u);
                
                if (current_cut_delta < best_cut_delta) {
                    best_cut_delta = current_cut_delta;
                    best_move_idx = step;
                }
                
                // Update gains of neighbors
                for (int v : adj[u]) {
                    if (visited_token[v] == token_counter && !locked[v]) {
                        int p_v = current_part[v];
                        // If neighbor v is in the partition u moved TO, edge becomes internal -> gain decreases
                        // If neighbor v is in the partition u moved FROM, edge becomes external -> gain increases
                        int change = (p_v == current_part[u]) ? -2 : 2;
                        
                        moves[p_v].erase({-gains[v], v});
                        gains[v] += change;
                        moves[p_v].insert({-gains[v], v});
                    }
                }
            }
            
            // Rollback to best state found in this pass
            if (best_move_idx < (int)move_history.size() - 1) {
                for (int i = move_history.size() - 1; i > best_move_idx; --i) {
                    int u = move_history[i];
                    current_part[u] = 1 - current_part[u];
                }
            }
            
            // Stop early if no improvement
            if (best_cut_delta == 0) break;
        }
    }

    // Prepare for recursion
    vector<int> left_nodes, right_nodes;
    left_nodes.reserve(cur_left + nodes.size() / 10); 
    right_nodes.reserve(nodes.size() - cur_left + nodes.size() / 10);
    
    for (int u : nodes) {
        if (current_part[u] == 0) left_nodes.push_back(u);
        else right_nodes.push_back(u);
    }
    
    solve_recursive(left_nodes, k_half, offset);
    solve_recursive(right_nodes, k_half, offset + k_half);
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N >> M >> K >> EPS)) return 0;

    adj.resize(N + 1);
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        if (u != v) { // Self-loops handled implicitly by skipping later, but easy to skip here
            adj[u].push_back(v);
            adj[v].push_back(u);
        }
    }
    
    // Clean graph: remove duplicates and self-loops
    for (int i = 1; i <= N; ++i) {
        vector<int>& nb = adj[i];
        if (nb.empty()) continue;
        sort(nb.begin(), nb.end());
        int k_adj = 0;
        for (int j = 0; j < nb.size(); ++j) {
            if (nb[j] == i) continue; // remove self loop
            if (j > 0 && nb[j] == nb[j-1]) continue; // remove duplicate
            nb[k_adj++] = nb[j];
        }
        nb.resize(k_adj);
    }
    
    // Calculate global max partition size
    // ideal = ceil(N / K)
    long long ideal = (N + K - 1) / K;
    GLOBAL_MAX_SIZE = floor((1.0 + EPS) * ideal);

    partition_labels.resize(N + 1);
    
    // Resize scratchpads
    visited_token.assign(N + 1, 0);
    bfs_visited.assign(N + 1, 0);
    current_part.resize(N + 1);
    gains.resize(N + 1);
    locked.resize(N + 1);
    
    vector<int> all_nodes(N);
    iota(all_nodes.begin(), all_nodes.end(), 1);
    
    // Start recursive bisection
    solve_recursive(all_nodes, K, 1);
    
    // Output
    for (int i = 1; i <= N; ++i) {
        cout << partition_labels[i] << (i == N ? "" : " ");
    }
    cout << "\n";

    return 0;
}