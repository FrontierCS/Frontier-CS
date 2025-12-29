#include <iostream>
#include <vector>
#include <cassert>

using namespace std;

const int N = 200;
const int M = 10;
const int EMPTY1 = 9;   // first empty stack (1-indexed)
const int EMPTY2 = 10;  // second empty stack

vector<vector<int>> st(M + 1);  // stacks, bottom to top
int stack_id[N + 1];            // which stack a box belongs to
int pos[N + 1];                 // index from bottom in its stack

void move(int v, int dest) {
    int s = stack_id[v];
    int idx = pos[v];
    int k = (int)st[s].size() - idx;
    // output operation
    cout << v << " " << dest << "\n";
    // remove the suffix [idx..end] from stack s
    vector<int> moved;
    for (int i = idx; i < (int)st[s].size(); ++i) {
        moved.push_back(st[s][i]);
    }
    st[s].resize(idx);
    // append to destination stack
    for (int box : moved) {
        st[dest].push_back(box);
        stack_id[box] = dest;
        pos[box] = (int)st[dest].size() - 1;
    }
}

void take_out(int v) {
    // v must be the smallest remaining and at the top of its stack
    cout << v << " 0\n";
    int s = stack_id[v];
    st[s].pop_back();
    stack_id[v] = 0;  // mark as removed
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    cin >> n >> m;  // n=200, m=10

    // read initial stacks
    for (int i = 1; i <= m; ++i) {
        st[i].clear();
        for (int j = 0; j < n / m; ++j) {
            int box;
            cin >> box;
            st[i].push_back(box);
            stack_id[box] = i;
            pos[box] = j;
        }
    }

    // empty two stacks to use as buffers
    if (!st[EMPTY1].empty()) {
        int bottom = st[EMPTY1][0];
        move(bottom, 8);  // move whole stack EMPTY1 to stack 8
    }
    if (!st[EMPTY2].empty()) {
        int bottom = st[EMPTY2][0];
        move(bottom, 7);  // move whole stack EMPTY2 to stack 7
    }

    // carry out boxes in increasing order
    for (int cur = 1; cur <= n; ++cur) {
        if (stack_id[cur] == 0) continue;  // already taken out (should not happen)
        int s = stack_id[cur];
        if (st[s].back() == cur) {
            take_out(cur);
            continue;
        }

        // bring cur to the top using the two empty stacks
        int d = (int)st[s].size() - pos[cur] - 1;  // number of boxes above cur
        // move cur and all above to EMPTY1
        move(cur, EMPTY1);
        // now cur is at the bottom of EMPTY1, boxes above it (if any) are on top
        if (d > 0) {
            // the box directly above cur on EMPTY1
            int above = st[EMPTY1][1];
            move(above, EMPTY2);  // move all boxes above cur to EMPTY2
        }
        // cur is now the top of EMPTY1
        take_out(cur);
        // move the boxes from EMPTY2 back to the original stack s
        if (d > 0) {
            int bottom_e2 = st[EMPTY2][0];
            move(bottom_e2, s);
        }
    }

    return 0;
}