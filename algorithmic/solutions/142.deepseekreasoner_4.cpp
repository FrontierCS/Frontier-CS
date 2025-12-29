#include <bits/stdc++.h>
using namespace std;

int n, m;
vector<vector<int>> poles;  // poles[i] is a stack from bottom to top, i from 1 to n+1
vector<pair<int, int>> moves;

void move_ball(int from, int to) {
    moves.push_back({from, to});
    int ball = poles[from].back();
    poles[from].pop_back();
    poles[to].push_back(ball);
}

bool is_monochromatic(int idx) {
    if (idx > n) return false;  // buffer has no target color
    if (poles[idx].empty()) return false;
    for (int ball : poles[idx])
        if (ball != idx)
            return false;
    return true;
}

// find a pole with space, excluding given poles
int find_temp(int exclude1, int exclude2, const unordered_set<int>& exclude_set = {}) {
    for (int i = 1; i <= n + 1; i++) {
        if (i == exclude1 || i == exclude2) continue;
        if (exclude_set.count(i)) continue;
        if ((int)poles[i].size() < m)
            return i;
    }
    // if none, try excluding only exclude1
    for (int i = 1; i <= n + 1; i++) {
        if (i == exclude1) continue;
        if ((int)poles[i].size() < m)
            return i;
    }
    return -1;  // should not happen
}

// make space on target pole (which is full) by removing one non-target ball
void make_space(int target, int avoid) {
    // find the first non-target ball from the top
    int pos = -1;
    for (int i = (int)poles[target].size() - 1; i >= 0; i--) {
        if (poles[target][i] != target) {
            pos = i;
            break;
        }
    }
    // if all are target color, just move the top ball out
    if (pos == -1) {
        int t = find_temp(target, avoid);
        move_ball(target, t);
        return;
    }
    int k = (int)poles[target].size() - 1 - pos;  // number of target-colored balls above it
    vector<int> temp_poles;
    unordered_set<int> used;
    // move the k target balls to temporary poles
    for (int i = 0; i < k; i++) {
        int t = find_temp(target, avoid, used);
        used.insert(t);
        move_ball(target, t);
        temp_poles.push_back(t);
    }
    // now the non-target ball is on top
    int wrong_color = poles[target].back();
    int wrong_target = wrong_color;
    int t = -1;
    // try to send wrong ball to its own target if possible and not used
    if (wrong_target != target && (int)poles[wrong_target].size() < m && !used.count(wrong_target)) {
        t = wrong_target;
    } else {
        // otherwise find a temporary pole, preferably not used for target balls
        t = find_temp(target, avoid, used);
        if (t == -1) {
            // fallback: any pole with space
            for (int i = 1; i <= n + 1; i++) {
                if (i == target) continue;
                if ((int)poles[i].size() < m) {
                    t = i;
                    break;
                }
            }
        }
    }
    move_ball(target, t);
    // move back the k target balls in reverse order
    for (int i = (int)temp_poles.size() - 1; i >= 0; i--) {
        move_ball(temp_poles[i], target);
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    cin >> n >> m;
    poles.resize(n + 2);  // indices 1..n+1
    for (int i = 1; i <= n; i++) {
        poles[i].resize(m);
        for (int j = 0; j < m; j++) {
            cin >> poles[i][j];
        }
    }

    // main loop
    while (true) {
        bool all_done = true;
        for (int i = 1; i <= n; i++) {
            if (!is_monochromatic(i)) {
                all_done = false;
                break;
            }
        }
        if (all_done) break;

        bool moved = false;
        // try to move a misplaced ball to its target
        for (int i = 1; i <= n + 1; i++) {
            if (poles[i].empty()) continue;
            int color = poles[i].back();
            if (i <= n && is_monochromatic(i)) continue;  // this pole is already good
            int target = color;
            if (target == i) continue;  // already on target? but pole may not be monochromatic
            if ((int)poles[target].size() < m) {
                move_ball(i, target);
                moved = true;
                break;
            } else {
                // target is full, need to make space
                make_space(target, i);
                // now target has space
                move_ball(i, target);
                moved = true;
                break;
            }
        }
        if (moved) continue;
        // no direct move possible, expose a ball from a non-monochromatic pole
        for (int i = 1; i <= n; i++) {
            if (!is_monochromatic(i) && !poles[i].empty()) {
                int t = find_temp(i, -1);
                if (t != -1) {
                    move_ball(i, t);
                    moved = true;
                    break;
                }
            }
        }
        if (!moved) break;  // should not happen
    }

    cout << moves.size() << "\n";
    for (auto [x, y] : moves) {
        cout << x << " " << y << "\n";
    }
    return 0;
}