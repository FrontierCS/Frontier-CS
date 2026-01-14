#include <iostream>
#include <vector>
#include <numeric>

// Helper function to print a state vector
void print_state(const std::vector<int>& state, int n) {
    for (int i = 0; i < n; ++i) {
        std::cout << state[i] << (i == n - 1 ? "" : " ");
    }
    std::cout << "\n";
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n, m;
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

    std::vector<std::vector<int>> states;
    states.push_back(initial_state);
    
    std::vector<int> current_state = initial_state;

    if (current_state == target_state) {
        std::cout << 0 << "\n";
        print_state(states[0], n);
        return 0;
    }

    // The number of steps is likely small, but we use a safe upper bound.
    for (int k = 0; k < 2 * n; ++k) {
        std::vector<int> next_state = current_state;
        
        // For each node, decide its next color based on the greedy strategy.
        for (int i = 0; i < n; ++i) {
            // If unsatisfied, try to become satisfied.
            if (current_state[i] != target_state[i]) {
                for (int neighbor : adj[i]) {
                    if (current_state[neighbor] == target_state[i]) {
                        next_state[i] = target_state[i];
                        break;
                    }
                }
            }
        }
        
        current_state = next_state;
        states.push_back(current_state);

        if (current_state == target_state) {
            break;
        }
    }

    std::cout << states.size() - 1 << "\n";
    for (const auto& state : states) {
        print_state(state, n);
    }

    return 0;
}