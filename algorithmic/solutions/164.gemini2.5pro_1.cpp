#include <iostream>
#include <vector>
#include <algorithm>
#include <utility>

// State of the system
int N, M;
std::vector<std::vector<int>> stacks;
std::vector<std::pair<int, int>> pos; // pos[v] = {stack_idx, height_idx}
std::vector<std::pair<int, int>> operations;

// Simulates a move operation, updating the state and recording the operation
void apply_move(int v_move, int dest_stack_idx) {
    operations.push_back({v_move, dest_stack_idx + 1});

    auto [src_stack_idx, src_height_idx] = pos[v_move];

    std::vector<int> block;
    // The block to be moved starts from v_move
    for (size_t i = src_height_idx; i < stacks[src_stack_idx].size(); ++i) {
        block.push_back(stacks[src_stack_idx][i]);
    }

    // Remove the block from the source stack
    stacks[src_stack_idx].resize(src_height_idx);

    // Add the block to the destination stack and update positions of moved boxes
    size_t old_dest_size = stacks[dest_stack_idx].size();
    for (size_t i = 0; i < block.size(); ++i) {
        int box_val = block[i];
        stacks[dest_stack_idx].push_back(box_val);
        pos[box_val] = {dest_stack_idx, (int)(old_dest_size + i)};
    }
}

// Simulates a carry-out operation, updating the state and recording the operation
void apply_carry_out(int v_target) {
    operations.push_back({v_target, 0});
    auto [stack_idx, height_idx] = pos[v_target];
    stacks[stack_idx].pop_back();
    // No need to update pos for v_target, it's gone from the system.
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::cin >> N >> M;
    stacks.resize(M);
    pos.resize(N + 1);

    for (int i = 0; i < M; ++i) {
        int k = N / M;
        stacks[i].resize(k);
        for (int j = 0; j < k; ++j) {
            std::cin >> stacks[i][j];
            pos[stacks[i][j]] = {i, j};
        }
    }

    for (int v_target = 1; v_target <= N; ++v_target) {
        auto [src_stack_idx, src_height_idx] = pos[v_target];

        // Check if the target box is at the top of its stack
        if (src_height_idx != (int)stacks[src_stack_idx].size() - 1) {
            // It's not at the top, so we must move the boxes above it
            int v_move = stacks[src_stack_idx][src_height_idx + 1];
            
            int dest_stack_idx = -1;

            // Strategy to find destination:
            // 1. Prefer an empty stack.
            // 2. Otherwise, pick the shortest stack.
            // 3. Tie-break shortest stacks by picking one with the largest-numbered top box.

            // First, look for an empty stack.
            for (int i = 0; i < M; ++i) {
                if (i == src_stack_idx) continue;
                if (stacks[i].empty()) {
                    dest_stack_idx = i;
                    break;
                }
            }
            
            if (dest_stack_idx == -1) {
                // No empty stacks found. Find the best non-empty one.
                // We want to minimize (size, -top_value) to find the best stack.
                std::pair<size_t, int> best_criteria = { (size_t)N + 1, -1 };

                for (int i = 0; i < M; ++i) {
                    if (i == src_stack_idx) continue;
                    
                    std::pair<size_t, int> current_criteria = {stacks[i].size(), -stacks[i].back()};
                    if (current_criteria < best_criteria) {
                        best_criteria = current_criteria;
                        dest_stack_idx = i;
                    }
                }
            }

            apply_move(v_move, dest_stack_idx);
        }

        // Now the target box is at the top, carry it out.
        apply_carry_out(v_target);
    }

    for (const auto& op : operations) {
        std::cout << op.first << " " << op.second << "\n";
    }

    return 0;
}