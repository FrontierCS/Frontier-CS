#include <iostream>
#include <vector>
#include <algorithm>
#include <cassert>

using namespace std;

const int N = 200;
const int M = 10;
int n, m;
vector<vector<int>> stacks(M+1);  // 1-indexed, each stack bottom to top
int pos_stack[N+1];   // which stack the box is in (1..m)
int pos_idx[N+1];     // index from bottom (0-based) in its stack

// Choose destination stack for moving a block whose bottom is 'w', source stack is 's'
int chooseDestination(int s, int w) {
    const int EMPTY_SCORE = 1000000;
    int best_score = -1e9;
    int best_d = -1;
    for (int i = 1; i <= m; ++i) {
        if (i == s) continue;
        if (stacks[i].empty()) {
            int score = EMPTY_SCORE;
            if (score > best_score) {
                best_score = score;
                best_d = i;
            }
        } else {
            int top_i = stacks[i].back();
            int diff = top_i - w;
            int score;
            if (diff > 0) {
                score = diff * 10 - (int)stacks[i].size();
            } else {
                score = diff * 100 - (int)stacks[i].size();
            }
            if (score > best_score) {
                best_score = score;
                best_d = i;
            }
        }
    }
    assert(best_d != -1);
    return best_d;
}

// Move the segment of stack s starting at index start_idx (inclusive) to the top of stack d
void moveSegment(int s, int start_idx, int d) {
    vector<int> segment(stacks[s].begin() + start_idx, stacks[s].end());
    int old_size_d = stacks[d].size();
    for (size_t j = 0; j < segment.size(); ++j) {
        int box = segment[j];
        pos_stack[box] = d;
        pos_idx[box] = old_size_d + j;
    }
    stacks[d].insert(stacks[d].end(), segment.begin(), segment.end());
    stacks[s].erase(stacks[s].begin() + start_idx, stacks[s].end());
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> n >> m;
    int k = n / m;  // 20
    for (int i = 1; i <= m; ++i) {
        stacks[i].resize(k);
        for (int j = 0; j < k; ++j) {
            cin >> stacks[i][j];
        }
    }

    // Initialize position arrays
    for (int i = 1; i <= m; ++i) {
        for (size_t j = 0; j < stacks[i].size(); ++j) {
            int box = stacks[i][j];
            pos_stack[box] = i;
            pos_idx[box] = j;
        }
    }

    int next_box = 1;
    int op_count = 0;
    const int MAX_OPS = 5000;

    while (next_box <= n && op_count < MAX_OPS) {
        int v = next_box;
        int s = pos_stack[v];
        int idx = pos_idx[v];
        bool is_top = (idx == (int)stacks[s].size() - 1);

        if (is_top) {
            // Carry out v
            cout << v << " " << 0 << "\n";
            stacks[s].pop_back();
            ++next_box;
            ++op_count;
        } else {
            // Move the box directly above v and all boxes above it
            int w = stacks[s][idx + 1];
            int d = chooseDestination(s, w);
            cout << w << " " << d << "\n";
            moveSegment(s, idx + 1, d);
            ++op_count;

            // Now v is at the top of stack s, carry it out
            cout << v << " " << 0 << "\n";
            stacks[s].pop_back();
            ++next_box;
            ++op_count;
        }
    }

    // If somehow we exceed 5000 operations, we stop.
    // In practice this should not happen.

    return 0;
}