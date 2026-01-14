#include <iostream>
#include <vector>
#include <string>
#include <sstream>
#include <algorithm>
#include <map>

// Globals for a single test case
int n;
std::vector<std::vector<int>> adj;
std::vector<int> degree;
std::vector<bool> visited;
std::vector<int> parent;

// Function to compute fingerprint of a vertex.
// The fingerprint is its degree and the sorted list of (degree, visited_flag) of its neighbors.
// This is based on the current global `visited` state.
std::pair<int, std::vector<std::pair<int, int>>> get_fingerprint(int u) {
    std::vector<std::pair<int, int>> neighbor_info;
    for (int v : adj[u]) {
        neighbor_info.push_back({degree[v], visited[v]});
    }
    std::sort(neighbor_info.begin(), neighbor_info.end());
    return {degree[u], neighbor_info};
}

void solve() {
    int m, start_node, base_move_count;
    std::cin >> n >> m >> start_node >> base_move_count;
    adj.assign(n + 1, std::vector<int>());
    degree.assign(n + 1, 0);
    for (int i = 0; i < m; ++i) {
        int u, v;
        std::cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
        degree[u]++;
        degree[v]++;
    }
    
    for(int i = 1; i <= n; ++i) {
        std::sort(adj[i].begin(), adj[i].end());
    }

    visited.assign(n + 1, false);
    parent.assign(n + 1, 0);

    int current_vertex = start_node;
    visited[start_node] = true;
    int num_visited = 1;

    std::string line;
    // Consume the rest of the line after reading n, m, start, base_move_count
    std::getline(std::cin, line); 

    while (num_visited < n) {
        // 1. Get info from interactor for the current vertex
        std::getline(std::cin, line);
        std::stringstream ss(line);
        int d;
        ss >> d;
        std::vector<std::pair<int, int>> interactor_neighbors(d);
        for (int i = 0; i < d; ++i) {
            ss >> interactor_neighbors[i].first >> interactor_neighbors[i].second;
        }

        // 2. Decide on a target vertex to move to (DFS strategy)
        int target_v = -1;
        bool is_exploring = false;
        
        std::vector<int> unvisited_neighbors;
        for (int neighbor : adj[current_vertex]) {
            if (!visited[neighbor]) {
                unvisited_neighbors.push_back(neighbor);
            }
        }
        
        if (!unvisited_neighbors.empty()) {
            // Prefer to explore unvisited nodes
            target_v = unvisited_neighbors[0]; // adj lists are sorted, so this is deterministic
            is_exploring = true;
        } else {
            // All neighbors visited, backtrack to parent
            if (parent[current_vertex] != 0) {
                 target_v = parent[current_vertex];
            } else {
                 // At start node in a fully explored component. This should only happen if n_visited = n.
                 // If not, graph may be disconnected. Move to any neighbor to avoid getting stuck.
                 target_v = adj[current_vertex][0];
            }
            is_exploring = false;
        }

        // 3. Find the 1-based index for the move
        std::pair<int, int> target_char = {degree[target_v], is_exploring ? 0 : 1};
        int move_idx = -1;
        for (int i = 0; i < d; ++i) {
            if (interactor_neighbors[i] == target_char) {
                move_idx = i + 1;
                break;
            }
        }

        // 4. Make the move
        std::cout << move_idx << std::endl;

        // 5. Get response and identify new location
        std::getline(std::cin, line);
        if (line == "AC" || line == "F") {
            if (line == "AC") num_visited = n;
            break;
        }
        
        std::stringstream ss_resp(line);
        ss_resp >> d;
        std::vector<std::pair<int, int>> received_neighbor_info(d);
        for (int i = 0; i < d; ++i) {
            ss_resp >> received_neighbor_info[i].first >> received_neighbor_info[i].second;
        }
        std::sort(received_neighbor_info.begin(), received_neighbor_info.end());
        std::pair<int, std::vector<std::pair<int, int>>> received_fingerprint = {d, received_neighbor_info};
        
        // Find all potential candidates for our destination
        std::vector<int> candidates;
        for (int neighbor : adj[current_vertex]) {
            if (degree[neighbor] == target_char.first && visited[neighbor] == !is_exploring) {
                 candidates.push_back(neighbor);
            }
        }
        
        int new_vertex = -1;
        if (candidates.size() == 1) {
            new_vertex = candidates[0];
        } else {
            // Disambiguate using fingerprints
            std::vector<int> matching_candidates;
            for (int cand_v : candidates) {
                auto theoretical_fingerprint = get_fingerprint(cand_v);
                if (theoretical_fingerprint == received_fingerprint) {
                    matching_candidates.push_back(cand_v);
                }
            }

            if (!matching_candidates.empty()) {
                // On ambiguity, pick smallest index deterministically
                new_vertex = matching_candidates[0]; 
            } else {
                // Fallback, should not happen in a well-formed problem
                new_vertex = candidates[0];
            }
        }

        // 6. Update state
        if (is_exploring) {
            if (!visited[new_vertex]) {
                visited[new_vertex] = true;
                num_visited++;
                parent[new_vertex] = current_vertex;
            }
        }
        current_vertex = new_vertex;
    }

    if (num_visited < n && line != "AC" && line != "F") {
        std::getline(std::cin, line); // Consume final "AC" or "F"
    }
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