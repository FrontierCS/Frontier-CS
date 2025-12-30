#include <bits/stdc++.h>
using namespace std;

typedef unsigned long long state_t;
int N;
state_t goal;

// encode basket assignments into a 64-bit integer
// basket values: 0 for basket 1, 1 for basket 2, 2 for basket 3
state_t encode(int* arr) {
    state_t s = 0;
    for (int i = 0; i < N; ++i) {
        s |= (state_t)arr[i] << (2 * i);
    }
    return s;
}

// decode the state into an array
void decode(state_t s, int* arr) {
    for (int i = 0; i < N; ++i) {
        arr[i] = (s >> (2 * i)) & 3;
    }
}

// depth‑limited DFS with backtracking
bool dfs(state_t s, int depth, int max_depth,
         vector<pair<int, int>>& path,
         unordered_set<state_t>& visited) {
    if (depth == max_depth) return s == goal;
    if (visited.count(s)) return false;
    visited.insert(s);

    int basket_of[30];
    decode(s, basket_of);

    for (int a = 0; a < 3; ++a) {
        // collect balls in basket a
        vector<int> src;
        for (int i = 0; i < N; ++i)
            if (basket_of[i] == a)
                src.push_back(i + 1);  // ball numbers are 1‑based
        if (src.empty()) continue;
        sort(src.begin(), src.end());
        int sz = src.size();
        int center_pos = (sz + 2) / 2;          // 1‑indexed center position
        int x = src[center_pos - 1];           // ball number of the center
        int x_idx = x - 1;                     // 0‑based index of the ball

        for (int b = 0; b < 3; ++b) {
            if (b == a) continue;

            // collect balls in basket b
            vector<int> tgt;
            for (int i = 0; i < N; ++i)
                if (basket_of[i] == b)
                    tgt.push_back(i + 1);
            sort(tgt.begin(), tgt.end());
            int m = tgt.size();

            // check if moving x from a to b is valid
            bool valid = false;
            if (m == 0) {
                valid = true;
            } else {
                int k_new = (m + 3) / 2;      // center position after insertion
                int idx = k_new - 1;          // number of balls that should be smaller than x
                if (idx == m) {
                    valid = (x > tgt.back());
                } else {
                    if (idx == 0) {
                        valid = (x < tgt[0]);
                    } else {
                        valid = (tgt[idx - 1] < x && x < tgt[idx]);
                    }
                }
            }

            if (valid) {
                // perform the move
                basket_of[x_idx] = b;
                state_t new_s = encode(basket_of);
                path.push_back({a + 1, b + 1});  // output uses 1‑based basket numbers

                if (dfs(new_s, depth + 1, max_depth, path, visited))
                    return true;

                path.pop_back();
                basket_of[x_idx] = a;           // restore
            }
        }
    }
    return false;
}

int main() {
    cin >> N;

    // initial state: all balls in basket 1 (encoded as 0)
    int init_arr[30];
    for (int i = 0; i < N; ++i) init_arr[i] = 0;
    state_t start = encode(init_arr);

    // goal state: all balls in basket 3 (encoded as 2)
    goal = 0;
    for (int i = 0; i < N; ++i)
        goal |= (state_t)2 << (2 * i);

    vector<pair<int, int>> path;
    bool found = false;

    // iterative deepening
    for (int max_depth = 1; max_depth <= 2 * N + 10; ++max_depth) {
        unordered_set<state_t> visited;
        path.clear();
        if (dfs(start, 0, max_depth, path, visited)) {
            found = true;
            break;
        }
    }

    // output the solution
    cout << path.size() << "\n";
    for (auto& move : path)
        cout << move.first << " " << move.second << "\n";

    return 0;
}