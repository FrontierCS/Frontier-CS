#include <iostream>
#include <vector>
#include <algorithm>
#include <cassert>

using namespace std;

const int N = 200;
const int M = 10;
const int T = 0; // target stack index (0-based)

int main() {
    int n, m;
    cin >> n >> m;
    // m is always 10, n=200
    vector<vector<int>> stacks(m);
    for (int i = 0; i < m; i++) {
        for (int j = 0; j < n/m; j++) {
            int box;
            cin >> box;
            stacks[i].push_back(box);
        }
    }

    // position of each box (0-based)
    vector<int> pos_stack(N+1, -1);
    vector<int> pos_idx(N+1, -1);
    for (int i = 0; i < m; i++) {
        for (int j = 0; j < (int)stacks[i].size(); j++) {
            int box = stacks[i][j];
            pos_stack[box] = i;
            pos_idx[box] = j;
        }
    }

    vector<pair<int, int>> ops; // (v, i)

    // Phase 1: rearrange all boxes into stack T in decreasing order (largest at bottom, smallest at top)
    for (int v = n; v >= 1; v--) {
        int s = pos_stack[v];
        int p = pos_idx[v];
        // if v is already at the top of target stack, skip
        if (s == T && p == (int)stacks[s].size() - 1) {
            continue;
        }

        // Step 1: make v the top of its current stack
        if (p != (int)stacks[s].size() - 1) {
            // there are boxes above v
            // box directly above v
            int w = stacks[s][p+1];
            // segment from p+1 to end
            int seg_size = stacks[s].size() - (p+1);
            // compute maximum in the segment
            int max_moved = 0;
            for (int i = p+1; i < (int)stacks[s].size(); i++) {
                max_moved = max(max_moved, stacks[s][i]);
            }

            // choose destination stack d (not s, not T)
            int d = -1;
            int best_top = -1;
            // first try: empty stack or top > max_moved
            for (int i = 0; i < m; i++) {
                if (i == s || i == T) continue;
                if (stacks[i].empty()) {
                    d = i;
                    break;
                } else {
                    int top_i = stacks[i].back();
                    if (top_i > max_moved) {
                        if (d == -1 || top_i > best_top) {
                            d = i;
                            best_top = top_i;
                        }
                    }
                }
            }
            if (d == -1) {
                // fallback: stack with largest top
                best_top = -1;
                for (int i = 0; i < m; i++) {
                    if (i == s || i == T) continue;
                    int top_i = stacks[i].back();
                    if (top_i > best_top) {
                        best_top = top_i;
                        d = i;
                    }
                }
            }
            // perform move (w, d+1) because output is 1-indexed
            ops.push_back({w, d+1});

            // update data structures: move segment from s to d
            vector<int> suffix(stacks[s].begin() + p+1, stacks[s].end());
            stacks[s].resize(p+1);
            int old_size_d = stacks[d].size();
            for (int box : suffix) {
                stacks[d].push_back(box);
            }
            // update positions for moved boxes
            for (int idx = 0; idx < (int)suffix.size(); idx++) {
                int box = suffix[idx];
                pos_stack[box] = d;
                pos_idx[box] = old_size_d + idx;
            }
            // v is now at the top of stack s (position p unchanged, but stack size is p+1)
            // pos_idx[v] remains p, which is now the last index
        }

        // Now v is top of its stack
        s = pos_stack[v];
        // Step 2: move v to target stack if not already there
        if (s != T) {
            ops.push_back({v, T+1}); // T+1 because output is 1-indexed
            // remove v from stack s
            stacks[s].pop_back();
            // add v to stack T
            stacks[T].push_back(v);
            // update position of v
            pos_stack[v] = T;
            pos_idx[v] = stacks[T].size() - 1;
        }
    }

    // Phase 2: carry out boxes in increasing order
    // After phase 1, stack T should have all boxes in decreasing order from bottom to top.
    // So the top is the smallest remaining box.
    for (int v = 1; v <= n; v++) {
        ops.push_back({v, 0});
    }

    // Output operations
    cout << ops.size() << '\n'; // not required, but we output each operation on separate line.
    for (auto& op : ops) {
        cout << op.first << ' ' << op.second << '\n';
    }

    return 0;
}