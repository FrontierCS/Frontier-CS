#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

// Constants are fixed for this problem as per the problem statement
const int N = 200;
const int M = 10;
const int STACK_INIT_SIZE = N / M;

// Global state variables for tracking box locations
std::vector<int> stacks[M + 1];
int box_stack[N + 1];
int box_pos[N + 1];

int main() {
    // Use fast I/O
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    // Read problem parameters (n and m are fixed, but we read them anyway)
    int n_in, m_in;
    std::cin >> n_in >> m_in;

    // Read the initial configuration of boxes in stacks
    for (int i = 1; i <= M; ++i) {
        stacks[i].resize(STACK_INIT_SIZE);
        for (int j = 0; j < STACK_INIT_SIZE; ++j) {
            std::cin >> stacks[i][j];
            // Store the initial location of each box
            box_stack[stacks[i][j]] = i;
            box_pos[stacks[i][j]] = j;
        }
    }

    std::vector<std::pair<int, int>> operations;

    // Main loop: carry out boxes in ascending order from 1 to N
    for (int target = 1; target <= N; ++target) {
        int s = box_stack[target];
        int p = box_pos[target];

        // If the target box is not at the top of its stack, we need to move the boxes above it.
        if (p != static_cast<int>(stacks[s].size()) - 1) {
            // The box to select for the move operation is the one directly above the target.
            int v_to_move = stacks[s][p + 1];
            
            // Heuristic to find the best destination stack for the moved boxes.
            int dest = -1;
            
            // Priority 1: An empty stack is the best destination.
            int empty_dest = -1;
            for (int i = 1; i <= M; ++i) {
                if (i == s) continue; // Cannot move to the same stack
                if (stacks[i].empty()) {
                    empty_dest = i;
                    break;
                }
            }

            if (empty_dest != -1) {
                dest = empty_dest;
            } else {
                // Priority 2: If no empty stacks, choose the one with the largest top box number.
                // This delays dealing with the moved boxes.
                // Tie-breaking: choose the stack with the smallest size to keep stacks balanced.
                int max_top_val = -1;
                int min_size_at_max_top = N + 2; // Initialize with a value larger than any possible stack size
                int best_full_dest = -1;

                for (int i = 1; i <= M; ++i) {
                    if (i == s) continue;
                    
                    int current_top = stacks[i].back();
                    int current_size = stacks[i].size();

                    if (current_top > max_top_val) {
                        max_top_val = current_top;
                        min_size_at_max_top = current_size;
                        best_full_dest = i;
                    } else if (current_top == max_top_val) {
                        if (current_size < min_size_at_max_top) {
                            min_size_at_max_top = current_size;
                            best_full_dest = i;
                        }
                    }
                }
                dest = best_full_dest;
            }

            // Fallback in case a destination is not found (e.g., all other stacks are empty).
            if (dest == -1) {
                dest = (s == 1) ? 2 : 1;
            }

            // Record the move operation.
            operations.push_back({v_to_move, dest});

            // Update the state of stacks and box locations after the move.
            size_t dest_old_size = stacks[dest].size();
            size_t boxes_to_move_count = stacks[s].size() - (p + 1);
            
            // Reserve capacity to potentially avoid reallocations.
            stacks[dest].reserve(dest_old_size + boxes_to_move_count);

            for (size_t j = p + 1; j < stacks[s].size(); ++j) {
                int box_v = stacks[s][j];
                stacks[dest].push_back(box_v);
                box_stack[box_v] = dest;
                box_pos[box_v] = dest_old_size + (j - (p + 1));
            }
            stacks[s].resize(p + 1);
        }

        // Now the target box is at the top of its stack, so we can carry it out.
        operations.push_back({target, 0});

        // Update state after carrying out the box.
        s = box_stack[target];
        stacks[s].pop_back();
        box_stack[target] = 0; // Mark as carried out.
        box_pos[target] = -1;
    }

    // Output the sequence of operations.
    for (const auto& op : operations) {
        std::cout << op.first << " " << op.second << "\n";
    }

    return 0;
}