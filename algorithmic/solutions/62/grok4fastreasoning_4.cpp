#include <bits/stdc++.h>
using namespace std;

bool is_done(const vector<vector<int>>& stacks, const vector<int>& target, int m, int n) {
    vector<int> pos(n + 1, 0);
    vector<int> num(n + 1, 0);
    for (int p = 1; p <= n + 1; ++p) {
        for (int ball : stacks[p]) {
            int c = ball;
            ++num[c];
            if (pos[c] == 0) {
                pos[c] = p;
            } else if (pos[c] != p) {
                pos[c] = -1;
            }
        }
    }
    for (int c = 1; c <= n; ++c) {
        if (pos[c] <= 0 || num[c] != m) {
            return false;
        }
    }
    return true;
}

int main() {
    int n, m;
    cin >> n >> m;
    vector<vector<int>> stacks(n + 2);
    for (int i = 1; i <= n; ++i) {
        for (int j = 0; j < m; ++j) {
            int col;
            cin >> col;
            stacks[i].push_back(col);
        }
    }
    vector<int> target(n + 1);
    for (int i = 1; i <= n; ++i) {
        target[i] = i;
    }
    vector<pair<int, int>> moves;
    const int MAX_MOVES = 10000000;
    while (moves.size() < MAX_MOVES) {
        // Phase 1: Place as many balls to their targets as possible
        bool placed = true;
        while (placed) {
            placed = false;
            for (int x = 1; x <= n + 1; ++x) {
                if (stacks[x].empty()) continue;
                int c = stacks[x].back();
                int t = target[c];
                if (x != t && (int)stacks[t].size() < m) {
                    int ball = stacks[x].back();
                    stacks[x].pop_back();
                    stacks[t].push_back(ball);
                    moves.emplace_back(x, t);
                    placed = true;
                }
            }
        }
        if (is_done(stacks, target, m, n)) break;
        // Phase 2: Make space by moving an obstructing ball to a suitable y
        int best_y = -1;
        if ((int)stacks[n + 1].size() < m) {
            best_y = n + 1;
        } else {
            int min_s = m;
            for (int y = 1; y <= n + 1; ++y) {
                if (stacks[y].size() < m && (int)stacks[y].size() < min_s) {
                    min_s = stacks[y].size();
                    best_y = y;
                }
            }
        }
        assert(best_y != -1); // Guaranteed by problem
        bool found = false;
        for (int x = 1; x <= n + 1 && !found; ++x) {
            if (stacks[x].empty()) continue;
            int c = stacks[x].back();
            int t = target[c];
            if (stacks[t].size() == (size_t)m && x != best_y) {
                int ball = stacks[x].back();
                stacks[x].pop_back();
                stacks[best_y].push_back(ball);
                moves.emplace_back(x, best_y);
                found = true;
            }
        }
        assert(found); // Should find obstructing
        if (is_done(stacks, target, m, n)) break;
    }
    cout << moves.size() << endl;
    for (auto& p : moves) {
        cout << p.first << " " << p.second << endl;
    }
    return 0;
}