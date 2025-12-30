#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <climits>

const int N = 200;
const int M = 10;

std::vector<int> stacks[M + 1];
int box_stack[N + 1];
int box_pos[N + 1];

void read_input() {
    int n_dummy, m_dummy;
    std::cin >> n_dummy >> m_dummy;
    for (int i = 1; i <= M; ++i) {
        stacks[i].resize(N / M);
        for (int j = 0; j < N / M; ++j) {
            std::cin >> stacks[i][j];
            box_stack[stacks[i][j]] = i;
            box_pos[stacks[i][j]] = j;
        }
    }
}

void perform_move(int v_to_move, int dest_stack) {
    std::cout << v_to_move << " " << dest_stack << std::endl;

    int src_stack = box_stack[v_to_move];
    int pos_to_move = box_pos[v_to_move];

    size_t dest_old_size = stacks[dest_stack].size();
    for (size_t i = pos_to_move; i < stacks[src_stack].size(); ++i) {
        int box_v = stacks[src_stack][i];
        stacks[dest_stack].push_back(box_v);
        box_stack[box_v] = dest_stack;
        box_pos[box_v] = dest_old_size + (i - pos_to_move);
    }
    stacks[src_stack].resize(pos_to_move);
}

void perform_carry(int v) {
    std::cout << v << " " << 0 << std::endl;
    int s = box_stack[v];
    stacks[s].pop_back();
}

void solve() {
    for (int v = 1; v <= N; ++v) {
        int s = box_stack[v];
        int p = box_pos[v];

        if (p != static_cast<int>(stacks[s].size()) - 1) {
            int v_above = stacks[s][p + 1];
            
            int best_t = -1;

            // Priority 1: Use an empty stack if available
            for (int i = 1; i <= M; ++i) {
                if (i != s && stacks[i].empty()) {
                    best_t = i;
                    break;
                }
            }

            // Priority 2: If no empty stack, find one with the best heuristic score
            if (best_t == -1) {
                long long best_score = LLONG_MIN;
                for (int i = 1; i <= M; ++i) {
                    if (i == s) continue;
                    
                    // Heuristic: prefer stacks with a large-numbered top box,
                    // and penalize taller stacks.
                    const int C = 2;
                    long long current_score = (long long)stacks[i].back() - (long long)C * stacks[i].size();
                    
                    if (current_score > best_score) {
                        best_score = current_score;
                        best_t = i;
                    }
                }
            }
            perform_move(v_above, best_t);
        }
        
        perform_carry(v);
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    read_input();
    solve();
    return 0;
}