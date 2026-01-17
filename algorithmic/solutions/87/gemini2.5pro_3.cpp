#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

void print_state(const std::vector<int>& state) {
    for (size_t i = 0; i < state.size(); ++i) {
        std::cout << state[i] << (i == state.size() - 1 ? "" : " ");
    }
    std::cout << "\n";
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    int m;
    std::cin >> n >> m;

    std::vector<int> initial_state(n);
    for (int i = 0; i < n; ++i) {
        std::cin >> initial_state[i];
    }
    
    std::vector<int> target_state(n);
    for (int i = 0; i < n; ++i) {
        std::cin >> target_state[i];
    }

    std::vector<std::vector<int>> adj(n);
    for (int i = 0; i < m; ++i) {
        int u, v;
        std::cin >> u >> v;
        --u; --v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    std::vector<std::vector<int>> history;
    history.push_back(initial_state);

    if (initial_state == target_state) {
        std::cout << 0 << "\n";
        print_state(initial_state);
        return 0;
    }

    std::vector<int> current_state = initial_state;
    
    int max_steps = 2 * n + 5; 
    if (max_steps > 20000) max_steps = 20000;

    for (int k = 0; k < max_steps; ++k) {
        std::vector<int> next_state = current_state;
        
        for (int i = 0; i < n; ++i) {
            if (current_state[i] != target_state[i]) {
                // This node is incorrect and wants to change.
                // It can take a color from any neighbor. If a neighbor has the
                // target color, it's a valid move to take it.
                bool can_change = false;
                for (int neighbor : adj[i]) {
                    if (current_state[neighbor] == target_state[i]) {
                        can_change = true;
                        break;
                    }
                }
                
                if (can_change) {
                    next_state[i] = target_state[i];
                }
            }
        }
        
        current_state = next_state;
        history.push_back(current_state);

        if (current_state == target_state) {
            break;
        }
    }

    std::cout << history.size() - 1 << "\n";
    for (const auto& state : history) {
        print_state(state);
    }

    return 0;
}