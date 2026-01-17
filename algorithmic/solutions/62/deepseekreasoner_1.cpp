#include <bits/stdc++.h>
using namespace std;

int n, m;
vector<vector<int>> pillars; // bottom to top
vector<int> sz;
vector<int> correct_cnt;
vector<pair<int, int>> moves;
vector<bool> in_process;

void move(int x, int y) {
    int ball = pillars[x].back();
    pillars[x].pop_back();
    pillars[y].push_back(ball);
    sz[x]--; sz[y]++;
    if (x == ball) correct_cnt[ball]--;
    if (y == ball) correct_cnt[ball]++;
    moves.push_back({x, y});
}

void solve(int src) {
    if (sz[src] == 0) return;
    int color = pillars[src].back();
    int target = color;
    if (src == target) return;

    if (in_process[src]) {
        if (src == n + 1) {
            for (int j = 1; j <= n; j++) {
                if (sz[j] < m) {
                    move(src, j);
                    return;
                }
            }
        } else {
            if (sz[n + 1] < m) {
                move(src, n + 1);
            } else {
                solve(n + 1);
                move(src, n + 1);
            }
        }
        return;
    }

    in_process[src] = true;

    if (sz[target] < m) {
        move(src, target);
    } else {
        // target is full
        while (sz[target] == m && !pillars[target].empty() && pillars[target].back() == target) {
            if (sz[n + 1] < m) {
                move(target, n + 1);
            } else {
                bool moved = false;
                for (int j = 1; j <= n; j++) {
                    if (sz[j] < m) {
                        move(n + 1, j);
                        moved = true;
                        break;
                    }
                }
                if (!moved) {
                    // emergency: move any ball from buffer to any pillar (may cause overflow but rare)
                    move(n + 1, (target % n) + 1);
                }
                move(target, n + 1);
            }
        }
        if (sz[target] < m) {
            move(src, target);
        } else {
            solve(target);
            move(src, target);
        }
    }

    in_process[src] = false;
}

bool check_done() {
    for (int i = 1; i <= n; i++) {
        if (sz[i] != m || correct_cnt[i] != m) return false;
    }
    return sz[n + 1] == 0;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    cin >> n >> m;
    pillars.resize(n + 2);
    sz.assign(n + 2, 0);
    correct_cnt.assign(n + 1, 0);
    in_process.assign(n + 2, false);

    for (int i = 1; i <= n; i++) {
        pillars[i].resize(m);
        for (int j = 0; j < m; j++) {
            cin >> pillars[i][j];
            if (pillars[i][j] == i) correct_cnt[i]++;
        }
        sz[i] = m;
    }

    while (!check_done() && moves.size() < 10000000) {
        bool changed = false;
        for (int i = 1; i <= n; i++) {
            while (!pillars[i].empty() && pillars[i].back() != i && moves.size() < 10000000) {
                solve(i);
                changed = true;
            }
        }
        while (!pillars[n + 1].empty() && moves.size() < 10000000) {
            solve(n + 1);
            changed = true;
        }
        if (!changed) break;
    }

    cout << moves.size() << "\n";
    for (auto& p : moves) {
        cout << p.first << " " << p.second << "\n";
    }
    return 0;
}