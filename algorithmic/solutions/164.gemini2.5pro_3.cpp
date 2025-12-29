#include <iostream>
#include <vector>
#include <utility>
#include <numeric>
#include <algorithm>

void solve() {
    int n, m;
    std::cin >> n >> m;

    std::vector<std::vector<int>> stacks(m);
    std::vector<std::pair<int, int>> box_pos(n + 1);

    for (int i = 0; i < m; ++i) {
        int stack_size = n / m;
        stacks[i].reserve(n); // Reserve space for future growth
        for (int j = 0; j < stack_size; ++j) {
            int b;
            std::cin >> b;
            stacks[i].push_back(b);
            box_pos[b] = {i, j};
        }
    }

    std::vector<std::pair<int, int>> history;

    for (int target_box = 1; target_box <= n; ++target_box) {
        int s = box_pos[target_box].first;
        size_t pos = box_pos[target_box].second;

        // If the target box is not at the top of its stack, move boxes above it.
        if (pos != stacks[s].size() - 1) {
            int box_to_move_from = stacks[s][pos + 1];

            // Find the best destination stack for the boxes on top.
            // The heuristic is to choose a stack that we will likely not need to access soon.
            // This is determined by the minimum box number in the stack (higher is better).
            // As a tie-breaker, choose the stack with a smaller size.
            int best_d = -1;
            int max_min_box = -1;
            size_t min_size_for_max_min_box = n + 1;

            for (int j = 0; j < m; ++j) {
                if (j == s) {
                    continue;
                }

                int current_min_box = n + 1; // Sentinel for an empty stack
                if (!stacks[j].empty()) {
                    current_min_box = *std::min_element(stacks[j].begin(), stacks[j].end());
                }
                
                size_t current_size = stacks[j].size();

                if (current_min_box > max_min_box) {
                    max_min_box = current_min_box;
                    min_size_for_max_min_box = current_size;
                    best_d = j;
                } else if (current_min_box == max_min_box) {
                    if (current_size < min_size_for_max_min_box) {
                        min_size_for_max_min_box = current_size;
                        best_d = j;
                    }
                }
            }
            
            int d = best_d;
            history.push_back({box_to_move_from, d + 1});

            // Perform the move operation
            size_t old_d_size = stacks[d].size();
            size_t num_to_move = stacks[s].size() - (pos + 1);
            
            for (size_t i = 0; i < num_to_move; ++i) {
                int box_v = stacks[s][pos + 1 + i];
                stacks[d].push_back(box_v);
                box_pos[box_v] = {d, (int)(old_d_size + i)};
            }
            
            stacks[s].resize(pos + 1);
        }

        // Carry out the target box, which is now at the top
        history.push_back({target_box, 0});
        stacks[s].pop_back();
    }

    for (const auto& op : history) {
        std::cout << op.first << " " << op.second << "\n";
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    solve();
    return 0;
}