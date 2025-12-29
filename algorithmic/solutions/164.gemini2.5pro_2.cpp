#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

// Problem constraints
const int N = 200;
const int M = 10;
const int INITIAL_STACK_SIZE = N / M;

// State of the stacks
std::vector<int> stacks[M + 1];
// For quick lookup of box positions
int box_stack[N + 1];
int box_pos[N + 1];
// History of operations
std::vector<std::pair<int, int>> history;

// Function to perform a move operation and update state
void perform_move(int v_target, int dest_t) {
    int s = box_stack[v_target];
    int p = box_pos[v_target];

    // The box to specify in the move operation is the one directly on top of v_target
    int box_to_move = stacks[s][p + 1];
    history.push_back({box_to_move, dest_t});

    // Move boxes from stack s to dest_t
    size_t orig_dest_size = stacks[dest_t].size();
    stacks[dest_t].insert(stacks[dest_t].end(), stacks[s].begin() + p + 1, stacks[s].end());
    
    // Update positions for moved boxes
    for (size_t i = orig_dest_size; i < stacks[dest_t].size(); ++i) {
        int b = stacks[dest_t][i];
        box_stack[b] = dest_t;
        box_pos[b] = i;
    }

    // Resize the source stack
    stacks[s].resize(p + 1);
}

// Function to perform a carry out operation and update state
void carry_out(int v) {
    history.push_back({v, 0});
    int s = box_stack[v];
    stacks[s].pop_back();
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n_dummy, m_dummy;
    std::cin >> n_dummy >> m_dummy;

    for (int i = 1; i <= M; ++i) {
        stacks[i].reserve(N);
        for (int j = 0; j < INITIAL_STACK_SIZE; ++j) {
            int b;
            std::cin >> b;
            stacks[i].push_back(b);
            box_stack[b] = i;
            box_pos[b] = j;
        }
    }

    int trash_stack_idx = M;

    for (int v = 1; v <= N; ++v) {
        int s = box_stack[v];
        int p = box_pos[v];

        // If box v is already at the top, carry it out
        if (p == static_cast<int>(stacks[s].size()) - 1) {
            carry_out(v);
            continue;
        }

        int dest_t = -1;
        
        // "Lucky case": if box v+1 is at the top of the block we need to move.
        // This makes v+1 available for free after carrying out v.
        bool lucky = false;
        if (v < N && stacks[s].back() == v + 1) {
            lucky = true;
        }

        if (lucky) {
            // To preserve the v+1 on top, move the block to a "quiet" stack:
            // an empty one, or the shortest one to minimize future disturbances.
            int best_t = -1;
            int min_size = N + 1;
            int empty_t = -1;
            for (int t = 1; t <= M; ++t) {
                if (t == s) continue;
                if (stacks[t].empty()) {
                    empty_t = t;
                    break;
                }
                if (static_cast<int>(stacks[t].size()) < min_size) {
                    min_size = stacks[t].size();
                    best_t = t;
                }
            }
            dest_t = (empty_t != -1) ? empty_t : best_t;
        } else {
            // Standard strategy: use a designated trash stack.
            if (s != trash_stack_idx) {
                // If v is in a working stack, move covering boxes to the trash stack.
                dest_t = trash_stack_idx;
            } else {
                // If v is in the trash stack, move covering boxes to the best working stack.
                // Best is an empty stack, otherwise one with the highest-numbered top box.
                int best_t = -1;
                int max_top = -1;
                int empty_t = -1;
                for (int t = 1; t < trash_stack_idx; ++t) {
                    if (stacks[t].empty()) {
                        empty_t = t;
                        break;
                    }
                    if (stacks[t].back() > max_top) {
                        max_top = stacks[t].back();
                        best_t = t;
                    }
                }
                dest_t = (empty_t != -1) ? empty_t : best_t;
            }
        }
        
        perform_move(v, dest_t);
        carry_out(v);
    }

    for (const auto& op : history) {
        std::cout << op.first << " " << op.second << "\n";
    }

    return 0;
}