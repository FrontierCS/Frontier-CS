#include <iostream>
#include <vector>
#include <cassert>

using namespace std;

int n, m;
vector<vector<int>> stacks;
vector<pair<int, int>> pos; // pos[box] = (stack_index, index_from_bottom)

void rebuild_pos() {
    pos.assign(n + 1, {-1, -1});
    for (int i = 0; i < m; ++i) {
        for (int j = 0; j < (int)stacks[i].size(); ++j) {
            int box = stacks[i][j];
            pos[box] = {i, j};
        }
    }
}

int choose_destination(int s, int u) {
    // Choose a stack t != s to move the block whose bottom is u.
    // Heuristic: prefer empty stacks, then stacks with top > u (choose smallest such top),
    // otherwise stacks with largest top.
    int best = -1;
    int best_type = -1; // 0: empty, 1: top > u, 2: top <= u
    int best_top = -1;

    for (int i = 0; i < m; ++i) {
        if (i == s) continue;
        if (stacks[i].empty()) {
            // Empty stack is best.
            return i; // Return first empty stack found.
        }
        int top_i = stacks[i].back();
        if (top_i > u) {
            if (best_type == 2) {
                // We have a candidate with top <= u, but this is better.
                best = i;
                best_type = 1;
                best_top = top_i;
            } else if (best_type == 1) {
                // Choose the smallest top.
                if (top_i < best_top) {
                    best = i;
                    best_top = top_i;
                }
            } else { // best_type == -1
                best = i;
                best_type = 1;
                best_top = top_i;
            }
        } else { // top_i <= u
            if (best_type == 2) {
                // Choose the largest top.
                if (top_i > best_top) {
                    best = i;
                    best_top = top_i;
                }
            } else if (best_type == -1) {
                best = i;
                best_type = 2;
                best_top = top_i;
            }
            // If best_type == 1, ignore this stack.
        }
    }
    assert(best != -1);
    return best;
}

int main() {
    cin >> n >> m;
    int k = n / m;
    stacks.resize(m);
    for (int i = 0; i < m; ++i) {
        for (int j = 0; j < k; ++j) {
            int box;
            cin >> box;
            stacks[i].push_back(box);
        }
    }
    rebuild_pos();

    vector<pair<int, int>> ops;

    for (int v = 1; v <= n; ++v) {
        auto [s, p] = pos[v];
        if (p == (int)stacks[s].size() - 1) {
            // v is at the top.
            ops.emplace_back(v, 0);
            stacks[s].pop_back();
        } else {
            // v is not at the top.
            int u = stacks[s][p + 1]; // box directly above v
            int t = choose_destination(s, u);
            // Move operation: (u, t+1) because stacks are 1-indexed in output.
            ops.emplace_back(u, t + 1);

            // Perform the move: take the block from stack s starting at p+1.
            vector<int> block(stacks[s].begin() + p + 1, stacks[s].end());
            stacks[s].resize(p + 1);
            // Append the block to stack t.
            stacks[t].insert(stacks[t].end(), block.begin(), block.end());

            // Now v is at the top of stack s.
            ops.emplace_back(v, 0);
            stacks[s].pop_back();
        }
        rebuild_pos();
    }

    // Output the sequence.
    for (auto [v, i] : ops) {
        cout << v << " " << i << "\n";
    }

    return 0;
}