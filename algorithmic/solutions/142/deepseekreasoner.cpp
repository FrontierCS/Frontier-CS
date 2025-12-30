#include <iostream>
#include <vector>
#include <algorithm>
#include <cassert>
#include <functional>
#include <unordered_set>

using namespace std;

int n, m;
vector<vector<int>> poles; // poles[1..n+1], each is a stack (bottom to top)
vector<pair<int, int>> ops; // list of moves
vector<bool> done; // done[i] = true if pole i is finalized (has m balls of color i)

// move top ball from x to y
void move(int x, int y) {
    assert(!poles[x].empty());
    assert((int)poles[y].size() < m);
    int ball = poles[x].back();
    poles[x].pop_back();
    poles[y].push_back(ball);
    ops.push_back({x, y});
}

int top_color(int p) {
    if (poles[p].empty()) return 0;
    return poles[p].back();
}

// Ensure pole p has at least one free slot (size < m).
// During the process, we forbid moving balls from pole 'forbid'.
void free_space(int p, int forbid = -1) {
    if ((int)poles[p].size() < m) return;
    unordered_set<int> visited;
    function<bool(int)> dfs = [&](int cur) -> bool {
        if (cur == forbid) return false;
        if ((int)poles[cur].size() < m) return true;
        if (visited.count(cur)) return false;
        visited.insert(cur);
        int col = top_color(cur);
        if (col == cur) {
            // try to move to extra pole n+1
            if (dfs(n+1)) {
                move(cur, n+1);
                return true;
            }
            // try to move to any other non-done pole (except cur and forbid)
            for (int j = 1; j <= n; ++j) {
                if (j == cur || j == forbid || done[j]) continue;
                if (dfs(j)) {
                    move(cur, j);
                    return true;
                }
            }
            return false;
        } else {
            // try to move to its target pole 'col'
            if (col != forbid && dfs(col)) {
                move(cur, col);
                return true;
            }
            // if not possible, try extra pole
            if (dfs(n+1)) {
                move(cur, n+1);
                return true;
            }
            return false;
        }
    };
    if (!dfs(p)) {
        // emergency: find any pole with space (except forbid) and move top from p there.
        for (int j = 1; j <= n+1; ++j) {
            if (j == forbid) continue;
            if ((int)poles[j].size() < m) {
                move(p, j);
                return;
            }
        }
        // should never reach here (there must be free space somewhere)
    }
}

// Move the top ball of src to its target pole 'target' (which is the ball's color).
// Uses free_space to ensure target has space, and forbids moving from src.
void move_to_target(int src, int target) {
    if (src == target) return;
    if ((int)poles[target].size() < m) {
        move(src, target);
    } else {
        free_space(target, src);
        move(src, target);
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> n >> m;
    poles.resize(n+2);
    for (int i = 1; i <= n; ++i) {
        poles[i].resize(m);
        for (int j = 0; j < m; ++j) {
            cin >> poles[i][j]; // bottom to top
        }
    }
    // extra pole n+1 is empty
    done.assign(n+1, false);
    ops.clear();

    // Process colors from n down to 1
    for (int c = n; c >= 1; --c) {
        // Phase 1: Clear pole c of balls that are not color c.
        while (true) {
            bool changed = false;
            // Move non-c balls from the top of pole c to their targets.
            while (!poles[c].empty() && top_color(c) != c) {
                int col = top_color(c);
                move_to_target(c, col);
                changed = true;
            }
            // Check if all balls in pole c are color c.
            bool all_c = true;
            for (int ball : poles[c]) {
                if (ball != c) {
                    all_c = false;
                    break;
                }
            }
            if (all_c) {
                break; // pole c now contains only color c (maybe less than m)
            } else {
                // There is at least one non-c ball below some c balls.
                // Move the top c ball to a temporary pole.
                int temp = -1;
                if ((int)poles[n+1].size() < m) {
                    temp = n+1;
                } else {
                    for (int j = 1; j < c; ++j) {
                        if (!done[j] && (int)poles[j].size() < m) {
                            temp = j;
                            break;
                        }
                    }
                }
                if (temp == -1) {
                    // Need to free space in a temporary pole.
                    free_space(n+1, c);
                    temp = n+1;
                }
                move(c, temp);
                changed = true;
            }
            if (!changed) break;
        }

        // Phase 2: Collect all remaining balls of color c into pole c.
        // Search in poles 1..c-1 and the extra pole.
        for (int j = 1; j <= c-1; ++j) {
            while (true) {
                bool found = false;
                for (int ball : poles[j]) {
                    if (ball == c) {
                        found = true;
                        break;
                    }
                }
                if (!found) break;
                // Bring a color c ball to the top of pole j.
                while (!poles[j].empty() && top_color(j) != c) {
                    int col = top_color(j);
                    move_to_target(j, col);
                }
                // Now top is color c, move it to pole c.
                move_to_target(j, c);
            }
        }
        // Collect from extra pole.
        int j = n+1;
        while (true) {
            bool found = false;
            for (int ball : poles[j]) {
                if (ball == c) {
                    found = true;
                    break;
                }
            }
            if (!found) break;
            while (!poles[j].empty() && top_color(j) != c) {
                int col = top_color(j);
                move_to_target(j, col);
            }
            move_to_target(j, c);
        }

        done[c] = true;
    }

    // Output
    cout << ops.size() << "\n";
    for (auto& p : ops) {
        cout << p.first << " " << p.second << "\n";
    }
    return 0;
}