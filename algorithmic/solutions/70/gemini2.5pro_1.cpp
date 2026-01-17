#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <set>
#include <map>
#include <tuple>

// Using globals for competitive programming context, reset in solve()
int n, m, start_node, base_move_count;
std::vector<std::vector<int>> adj;
std::vector<int> degrees;
std::vector<bool> visited;
int visited_count;
std::vector<int> unvisited_neighbor_count;
std::vector<int> P;

void solve() {
    // Read graph description
    std::cin >> n >> m >> start_node >> base_move_count;
    adj.assign(n + 1, std::vector<int>());
    degrees.assign(n + 1, 0);
    for (int i = 0; i < m; ++i) {
        int u, v;
        std::cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
        degrees[u]++;
        degrees[v]++;
    }

    // Initialize state for this map
    visited.assign(n + 1, false);
    P.clear();
    P.push_back(start_node);
    visited[start_node] = true;
    visited_count = 1;
    
    unvisited_neighbor_count.assign(n + 1, 0);
    for(int i = 1; i <= n; ++i) {
        unvisited_neighbor_count[i] = degrees[i];
    }
    // Update unvisited neighbor counts based on start_node being visited
    for(int neighbor : adj[start_node]) {
        unvisited_neighbor_count[neighbor]--;
    }

    // Main interaction loop
    while (visited_count < n) {
        int d;
        std::cin >> d;

        std::map<std::pair<int, int>, std::vector<int>> moves_by_prop;
        std::vector<std::pair<int, int>> interactor_view_sorted(d);
        for (int i = 0; i < d; ++i) {
            int deg, flag;
            std::cin >> deg >> flag;
            moves_by_prop[{deg, flag}].push_back(i + 1);
            interactor_view_sorted[i] = {deg, flag};
        }
        std::sort(interactor_view_sorted.begin(), interactor_view_sorted.end());

        // Prune P: Filter possible locations based on current view
        std::vector<int> next_P;
        for (int v : P) {
            if (degrees[v] != d) continue;
            std::vector<std::pair<int, int>> v_view_sorted;
            for (int neighbor : adj[v]) {
                v_view_sorted.push_back({degrees[neighbor], visited[neighbor]});
            }
            std::sort(v_view_sorted.begin(), v_view_sorted.end());
            if (v_view_sorted == interactor_view_sorted) {
                next_P.push_back(v);
            }
        }
        P = next_P;

        // Score and select the best move
        std::vector<std::tuple<int, int, int, std::pair<int, int>>> scored_moves;

        for (auto const& [prop, indices] : moves_by_prop) {
            int deg = prop.first;
            int flag = prop.second;

            std::set<int> p_next_set;
            for (int v : P) {
                for (int u : adj[v]) {
                    if (degrees[u] == deg && visited[u] == flag) {
                        p_next_set.insert(u);
                    }
                }
            }
            
            if (p_next_set.empty()) continue;

            int p_next_size = p_next_set.size();

            if (flag == 0) { // Exploration move
                int newly_visited_count = 0;
                for (int u : p_next_set) {
                    if (!visited[u]) {
                        newly_visited_count++;
                    }
                }
                scored_moves.emplace_back(-1, p_next_size, -newly_visited_count, prop);
            } else { // Backtracking move
                int sum_unvis_neigh = 0;
                for (int u : p_next_set) {
                    sum_unvis_neigh += unvisited_neighbor_count[u];
                }
                scored_moves.emplace_back(0, p_next_size, -sum_unvis_neigh, prop);
            }
        }
        
        std::sort(scored_moves.begin(), scored_moves.end());
        
        std::pair<int, int> best_prop = std::get<3>(scored_moves[0]);
        int move_idx = moves_by_prop[best_prop][0];

        std::cout << move_idx << std::endl;

        // Update state based on the chosen move
        std::set<int> p_next_set;
        for (int v : P) {
            for (int u : adj[v]) {
                if (degrees[u] == best_prop.first && visited[u] == best_prop.second) {
                    p_next_set.insert(u);
                }
            }
        }
        
        P.assign(p_next_set.begin(), p_next_set.end());
        
        for (int u : P) {
            if (!visited[u]) {
                visited[u] = true;
                visited_count++;
                for (int neighbor : adj[u]) {
                    unvisited_neighbor_count[neighbor]--;
                }
            }
        }
    }

    std::string result;
    std::cin >> result; // Read "AC" or "F"
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