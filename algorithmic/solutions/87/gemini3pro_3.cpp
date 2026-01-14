#include <iostream>
#include <vector>
#include <queue>
#include <algorithm>

using namespace std;

// Global variables to store graph and states
int n, m;
vector<int> initial_state;
vector<int> target_state;
vector<vector<int>> adj;
vector<int> dist_to_target_0;

// BFS to compute shortest distance from each node to the set of nodes that are 0 in the target state.
// This helps in determining if a node can contribute to forming a target 0 within the remaining steps.
void bfs_dist() {
    dist_to_target_0.assign(n + 1, 1e9);
    queue<int> q;
    bool has_target_0 = false;
    for (int i = 1; i <= n; ++i) {
        if (target_state[i-1] == 0) {
            dist_to_target_0[i] = 0;
            q.push(i);
            has_target_0 = true;
        }
    }
    
    // If there are no 0s in target, distances remain infinite
    if (!has_target_0) return;

    while (!q.empty()) {
        int u = q.front();
        q.pop();

        for (int v : adj[u]) {
            if (dist_to_target_0[v] > dist_to_target_0[u] + 1) {
                dist_to_target_0[v] = dist_to_target_0[u] + 1;
                q.push(v);
            }
        }
    }
}

// Function to check if it's possible to transform initial_state to target_state in exactly k steps.
// If successful, it populates result_path with the sequence of states.
// The strategy is greedy: at each step, we decide the color of each node.
// A node becomes 0 if:
// 1. It MUST be 0 (all its neighbors are 0).
// 2. It CAN be 0 (has at least one 0 neighbor) AND it is useful for reaching a target 0.
//    "Useful" means the distance to the nearest target 0 is within the remaining steps.
// Otherwise, it becomes 1.
bool check(int k, vector<vector<int>>& result_path) {
    result_path.clear();
    result_path.push_back(initial_state);

    vector<int> current = initial_state;
    
    for (int t = 0; t < k; ++t) {
        vector<int> next_state(n);
        int remaining_steps = k - (t + 1);
        
        for (int u = 1; u <= n; ++u) {
            bool has_zero_neighbor = false;
            bool all_zero_neighbors = true;
            
            for (int v : adj[u]) {
                if (current[v-1] == 0) has_zero_neighbor = true;
                else all_zero_neighbors = false;
            }
            
            // Constraints based on neighbors
            bool in_upper = has_zero_neighbor; // Can be 0
            bool in_lower = all_zero_neighbors; // Must be 0
            
            // Heuristic: is this node on a valid path to a target 0?
            bool is_useful = false;
            if (dist_to_target_0[u] <= remaining_steps) {
                is_useful = true;
            }
            
            // Logic: Set to 0 if forced, or if allowed and useful.
            // This implicitly maximizes 1s while preserving necessary 0s.
            if ((in_upper && is_useful) || in_lower) {
                next_state[u-1] = 0;
            } else {
                next_state[u-1] = 1;
            }
        }
        current = next_state;
        result_path.push_back(current);
    }
    
    return current == target_state;
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n >> m)) return 0;

    initial_state.resize(n);
    for (int i = 0; i < n; ++i) cin >> initial_state[i];

    target_state.resize(n);
    for (int i = 0; i < n; ++i) cin >> target_state[i];

    adj.resize(n + 1);
    // Since a node can keep its color, we effectively have self-loops.
    for (int i = 1; i <= n; ++i) {
        adj[i].push_back(i);
    }

    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    // Precompute distances to target 0s
    bfs_dist();

    // Iterate through possible number of steps k to find the minimum.
    // Since n is small (<= 100), the optimal k should be comparable to n.
    // We check up to 2*n + 2 to be safe and cover cases requiring some maneuvering.
    for (int k = 0; k <= 2 * n + 5; ++k) {
        vector<vector<int>> path;
        if (check(k, path)) {
            cout << k << "\n";
            for (const auto& state : path) {
                for (int i = 0; i < n; ++i) {
                    cout << state[i] << (i == n - 1 ? "" : " ");
                }
                cout << "\n";
            }
            return 0;
        }
    }
    
    return 0;
}