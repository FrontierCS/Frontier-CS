#include <bits/stdc++.h>
using namespace std;

int n, m;
vector<vector<int>> pillars; // 1-indexed, top at back
vector<pair<int, int>> moves;

void move_ball(int from, int to) {
    int ball = pillars[from].back();
    pillars[from].pop_back();
    pillars[to].push_back(ball);
    moves.emplace_back(from, to);
}

int top_color(int p) {
    return pillars[p].back();
}

void ensure_space_nplus1();

void ensure_space(int p, vector<bool>& visited) {
    if (pillars[p].size() <= m - 1) return;
    if (visited[p]) {
        // cycle detected -> move top ball to n+1
        ensure_space_nplus1();
        move_ball(p, n + 1);
        return;
    }
    visited[p] = true;
    int d = top_color(p);
    if (d == p) {
        // top ball belongs here, move it to n+1 to free a slot
        ensure_space_nplus1();
        move_ball(p, n + 1);
    } else {
        ensure_space(d, visited);
        move_ball(p, d);
    }
    visited[p] = false;
}

void ensure_space_nplus1() {
    while (pillars[n + 1].size() == m) {
        int c = top_color(n + 1);
        vector<bool> visited(n + 2, false);
        ensure_space(c, visited);
        move_ball(n + 1, c);
    }
}

void move_top_to_correct(int i) {
    if (pillars[i].empty()) return;
    int c = top_color(i);
    if (c == i) {
        // move to n+1 temporarily
        ensure_space_nplus1();
        move_ball(i, n + 1);
    } else {
        // move to n+1 first, then to correct pillar
        ensure_space_nplus1();
        move_ball(i, n + 1);
        vector<bool> visited(n + 2, false);
        ensure_space(c, visited);
        move_ball(n + 1, c);
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> n >> m;
    pillars.resize(n + 2);
    for (int i = 1; i <= n; i++) {
        pillars[i].resize(m);
        for (int j = 0; j < m; j++) {
            cin >> pillars[i][j];
        }
        // we store bottom to top, so top is at index m-1.
        // but for convenience of popping from back, reverse to have top at back
        reverse(pillars[i].begin(), pillars[i].end());
    }
    // pillar n+1 is initially empty

    // Process each pillar until empty
    for (int i = 1; i <= n; i++) {
        while (!pillars[i].empty()) {
            move_top_to_correct(i);
        }
    }

    // Process remaining balls on pillar n+1
    while (!pillars[n + 1].empty()) {
        int c = top_color(n + 1);
        vector<bool> visited(n + 2, false);
        ensure_space(c, visited);
        move_ball(n + 1, c);
    }

    // Output
    cout << moves.size() << "\n";
    for (auto [x, y] : moves) {
        cout << x << " " << y << "\n";
    }

    return 0;
}