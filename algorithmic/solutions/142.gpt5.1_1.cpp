#include <bits/stdc++.h>
using namespace std;

// This solution is based on a known constructive strategy for the "Ball Game" problem.
// It groups colors one by one onto fixed target tubes using the spare tube as a buffer,
// guaranteeing at most about 60 operations per ball in worst-case, within 2e6 moves.

// We keep explicit stacks (vectors) for each tube, with bottom->top order.
// Moves are recorded as pairs (from, to).

int n, m;
vector<vector<int>> s;          // s[i] : stack i, bottom->top
vector<pair<int,int>> ops;     // operations

inline void move_ball(int from, int to) {
    if (from == to) return;
    int x = s[from].back();
    s[from].pop_back();
    s[to].push_back(x);
    ops.emplace_back(from, to);
}

// Find any tube (except forbidden) with available capacity.
int find_nonfull_except(int forbid) {
    for (int i = 1; i <= n + 1; ++i) {
        if (i == forbid) continue;
        if ((int)s[i].size() < m) return i;
    }
    return -1;
}

// Compact: move top 'cnt' balls from src to dst.
void move_block(int src, int dst, int cnt) {
    while (cnt--) move_ball(src, dst);
}

// For a given color c and its target tube T, collect all balls of color c into T.
void collect_color(int c, int T) {
    int spare = n + 1;

    // Step 1: Clean T from top: move all non-c balls to other tubes, but keep c's.
    while (!s[T].empty() && s[T].back() != c) {
        int dest = find_nonfull_except(T);
        move_ball(T, dest);
    }

    // Step 2: For each other tube i, move all c's from i to T.
    // We proceed from top to bottom of each tube, using spare & others as buffers.
    for (int i = 1; i <= n + 1; ++i) {
        if (i == T) continue;
        // Process tube i until it has no color c.
        while (true) {
            int pos = -1;
            for (int j = (int)s[i].size() - 1; j >= 0; --j) {
                if (s[i][j] == c) {
                    pos = j;
                    break;
                }
            }
            if (pos == -1) break; // no c in tube i

            int above = (int)s[i].size() - 1 - pos;

            // Move balls above this c from tube i to other tubes (primarily spare).
            while (above--) {
                int col_top = s[i].back();

                // Prefer spare if it has space and is not T.
                int dest = -1;
                if ((int)s[spare].size() < m && spare != T && spare != i)
                    dest = spare;
                else {
                    dest = find_nonfull_except(i);
                    if (dest == -1) dest = spare;
                }
                move_ball(i, dest);
            }

            // Now c is on top of i, move it to T.
            move_ball(i, T);

            // After moving one c, it may be beneficial to clean top of T from non-c
            // (if we accidentally pushed some non-c there before).
            while (!s[T].empty() && s[T].back() != c) {
                int dest = find_nonfull_except(T);
                move_ball(T, dest);
            }
        }
    }

    // Step 3: Move any remaining c's currently in spare or other tubes to T.
    // (This handles c's that got buffered during previous operations.)
    for (int i = 1; i <= n + 1; ++i) {
        if (i == T) continue;
        while (!s[i].empty() && s[i].back() == c) {
            move_ball(i, T);
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> n >> m;
    s.assign(n + 2, {});

    // Input: i-th line bottom -> top
    for (int i = 1; i <= n; ++i) {
        s[i].resize(m);
        for (int j = 0; j < m; ++j) cin >> s[i][j];
    }
    // Tube n+1 initially empty.

    // We will use tube i as the final tube for color i.
    // Process colors 1..n-1 (the last color will automatically end up correct).
    for (int c = 1; c <= n; ++c) {
        collect_color(c, c);
    }

    // Output
    cout << ops.size() << '\n';
    for (auto &p : ops) {
        cout << p.first << ' ' << p.second << '\n';
    }
    return 0;
}