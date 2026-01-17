#include <iostream>
#include <vector>
#include <numeric>
#include <cmath>
#include <set>
#include <algorithm>

// Fast I/O
void fast_io() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
}

void solve() {
    // Read input
    int N, M;
    std::cin >> N;
    std::vector<int> S(N);
    std::vector<int> pos(N);
    for (int i = 0; i < N; ++i) {
        std::cin >> S[i];
        pos[S[i]] = i;
    }
    std::cin >> M;
    std::vector<std::pair<int, int>> jerry_swaps(M);
    for (int i = 0; i < M; ++i) {
        std::cin >> jerry_swaps[i].first >> jerry_swaps[i].second;
    }

    // Initialize simulation data structures
    std::vector<std::pair<int, int>> my_swaps(M);
    std::vector<long long> costs(M);
    std::vector<bool> is_sorted_at_k(M + 1);
    std::set<std::pair<int, int>> displacements;

    for (int v = 0; v < N; ++v) {
        if(pos[v] != v) {
            displacements.insert({std::abs(pos[v] - v), v});
        }
    }

    // Simulation loop
    for (int k = 0; k < M; ++k) {
        is_sorted_at_k[k] = displacements.empty();

        // Jerry's move
        int x = jerry_swaps[k].first;
        int y = jerry_swaps[k].second;

        if (x != y) {
            int val_x = S[x];
            int val_y = S[y];

            if (pos[val_x] != val_x) displacements.erase({std::abs(pos[val_x] - val_x), val_x});
            if (pos[val_y] != val_y) displacements.erase({std::abs(pos[val_y] - val_y), val_y});

            std::swap(S[x], S[y]);
            pos[val_x] = y;
            pos[val_y] = x;
            
            if (pos[val_x] != val_x) displacements.insert({std::abs(pos[val_x] - val_x), val_x});
            if (pos[val_y] != val_y) displacements.insert({std::abs(pos[val_y] - val_y), val_y});
        }

        // My move (greedy strategy)
        if (displacements.empty()) {
            my_swaps[k] = {0, 0};
            costs[k] = 0;
        } else {
            int v_to_fix = displacements.begin()->second;
            int u = pos[v_to_fix];
            int v_idx = v_to_fix;
            
            my_swaps[k] = {u, v_idx};
            costs[k] = std::abs(u - v_idx);

            int w = S[v_idx]; // value at target position for v_to_fix

            displacements.erase(displacements.begin());
            if (pos[w] != w) displacements.erase({std::abs(pos[w] - w), w});
            
            std::swap(S[u], S[v_idx]);
            pos[v_to_fix] = v_idx;
            pos[w] = u;

            // v_to_fix is now sorted, so it's not re-inserted.
            if (pos[w] != w) displacements.insert({std::abs(pos[w] - w), w});
        }
    }
    is_sorted_at_k[M] = displacements.empty();

    // Calculate prefix sums of costs
    std::vector<long long> prefix_costs(M + 1, 0);
    for (int i = 0; i < M; ++i) {
        prefix_costs[i + 1] = prefix_costs[i] + costs[i];
    }

    // Find the best R
    long long best_V = -1;
    int best_R = -1;

    for (int R = 0; R <= M; ++R) {
        if (is_sorted_at_k[R]) {
            long long current_V = (long long)R * prefix_costs[R];
            if (best_R == -1 || current_V < best_V) {
                best_V = current_V;
                best_R = R;
            }
        }
    }
    
    // Output the solution
    std::cout << best_R << "\n";
    for (int i = 0; i < best_R; ++i) {
        std::cout << my_swaps[i].first << " " << my_swaps[i].second << "\n";
    }
    std::cout << best_V << "\n";
}

int main() {
    fast_io();
    solve();
    return 0;
}