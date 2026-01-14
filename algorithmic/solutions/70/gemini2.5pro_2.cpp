#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <map>
#include <string>

// Globals for a single test case
int N, M, START_NODE, BASE_MOVE_COUNT;
std::vector<std::vector<int>> adj;
std::vector<int> degrees;
std::vector<bool> visited;
int visited_count;
int current_node;
std::vector<int> path_stack;

// Helper to read the current node's neighbor information from the interactor
std::vector<std::pair<int, int>> read_interactor_response() {
    int d;
    std::cin >> d;
    std::vector<std::pair<int, int>> neighbors(d);
    for (int i = 0; i < d; ++i) {
        std::cin >> neighbors[i].first >> neighbors[i].second;
    }
    return neighbors;
}

void solve() {
    // Read graph structure
    std::cin >> N >> M >> START_NODE >> BASE_MOVE_COUNT;
    adj.assign(N + 1, std::vector<int>());
    degrees.assign(N + 1, 0);
    for (int i = 0; i < M; ++i) {
        int u, v;
        std::cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    // Pre-calculate degrees and sort adjacency lists for determinism
    for (int i = 1; i <= N; ++i) {
        degrees[i] = adj[i].size();
        std::sort(adj[i].begin(), adj[i].end());
    }

    // Initialize traversal state
    current_node = START_NODE;
    visited.assign(N + 1, false);
    visited_count = 0;
    path_stack.clear();

    while (true) {
        if (!visited[current_node]) {
            visited[current_node] = true;
            visited_count++;
        }
        if (visited_count == N) {
            break;
        }

        auto interactor_neighbors = read_interactor_response();
        int d = interactor_neighbors.size();

        // --- Plan a move (DFS logic) ---
        std::vector<int> unvisited_neighbors;
        for (int neighbor : adj[current_node]) {
            if (!visited[neighbor]) {
                unvisited_neighbors.push_back(neighbor);
            }
        }
        
        int target_node = -1;
        bool backtracking = false;

        if (!unvisited_neighbors.empty()) {
            // Strategy: Prioritize unambiguous moves
            std::map<std::pair<int, int>, int> prop_counts;
            for (int neighbor : adj[current_node]) {
                prop_counts[{degrees[neighbor], visited[neighbor]}]++;
            }

            int best_target = -1;
            // Find an unvisited neighbor whose properties are unique among all neighbors
            for (int neighbor : unvisited_neighbors) {
                if (prop_counts[{degrees[neighbor], false}] == 1) {
                    best_target = neighbor;
                    break;
                }
            }
            
            if (best_target != -1) {
                target_node = best_target;
            } else {
                // All unvisited neighbors are ambiguous, pick the one with smallest ID
                target_node = unvisited_neighbors[0];
            }
            backtracking = false;
        } else {
            // All neighbors visited, so backtrack
            target_node = path_stack.back();
            path_stack.pop_back();
            backtracking = true;
        }

        // --- Execute the move ---
        std::pair<int, int> target_props = {degrees[target_node], backtracking};
        
        int move_choice = -1;
        for (int i = 0; i < d; ++i) {
            if (interactor_neighbors[i] == target_props) {
                move_choice = i + 1;
                break;
            }
        }
        std::cout << move_choice << std::endl;

        // --- Update state ---
        int prev_node = current_node;
        if (!backtracking) {
            path_stack.push_back(prev_node);
        }
        
        // Find all possible destinations for the move
        std::vector<int> potential_lands;
        for (int neighbor : adj[prev_node]) {
            if (degrees[neighbor] == target_props.first && visited[neighbor] == (bool)target_props.second) {
                potential_lands.push_back(neighbor);
            }
        }
        
        // Heuristic: If ambiguous, assume we landed on the node with the smallest ID
        current_node = *std::min_element(potential_lands.begin(), potential_lands.end());
    }
    
    // Read final "AC" or "F"
    std::string result;
    std::cin >> result;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    int t;
    std::cin >> t;
    while (t--) {
        solve();
    }
    return 0;
}