#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>

using namespace std;

struct Point {
    int x, y;
};

int n, m, L, R, Sx, Sy, Lq, s;
vector<int> q;
bool used[45][45];
bool row_visited[45];
vector<Point> path;
int q_ptr = 0;

void add_point(int r, int c) {
    path.push_back({r, c});
    used[r][c] = true;
}

bool is_forbidden(int r) {
    // A row is forbidden if it appears in q at or after q_ptr
    // and is not the current target q[q_ptr].
    // q contains distinct integers.
    if (q_ptr >= Lq) return false;
    // If r matches the current target, it is allowed.
    if (q[q_ptr] == r) return false;
    // If r is a future target, it is forbidden.
    for (int i = q_ptr + 1; i < Lq; ++i) {
        if (q[i] == r) return true;
    }
    return false;
}

// Check if we can traverse channel column c from r1 to r2
bool check_channel(int r1, int r2, int col, int current_col, int dest_col) {
    // Check horizontal segment at r1: from current_col to col
    // Exclude start point (already at current_col)
    int step = (col > current_col) ? 1 : -1;
    // If col == current_col (should not happen for channels usually), loop won't run
    for (int c = current_col + step; c != col + step; c += step) {
        if (used[r1][c]) return false;
    }
    
    // Check vertical segment at col: from r1 to r2
    // We are at (r1, col) after horizontal moves
    step = (r2 > r1) ? 1 : -1;
    for (int r = r1 + step; r != r2 + step; r += step) { // Check up to r2
        if (used[r][col]) return false;
    }
    
    // Check horizontal segment at r2: from col to dest_col
    // We are at (r2, col). Move to dest_col.
    step = (dest_col > col) ? 1 : -1;
    for (int c = col + step; c != dest_col + step; c += step) {
        // This includes checking (r2, dest_col).
        // (r2, dest_col) is the entry to the new row required area.
        // It must be free. Since r2 is unvisited, it should be free.
        if (used[r2][c]) return false;
    }
    return true;
}

void execute_jump(int r1, int r2, int col, int current_col, int dest_col) {
    // Horizontal r1
    if (col != current_col) {
        int step = (col > current_col) ? 1 : -1;
        for (int c = current_col + step; c != col + step; c += step) {
            add_point(r1, c);
        }
    }
    // Vertical at col
    if (r2 != r1) {
        int step = (r2 > r1) ? 1 : -1;
        for (int r = r1 + step; r != r2 + step; r += step) {
            add_point(r, col);
        }
    }
    // Horizontal r2
    if (dest_col != col) {
        int step = (dest_col > col) ? 1 : -1;
        for (int c = col + step; c != dest_col + step; c += step) {
            add_point(r2, c);
        }
    } else {
        // If col == dest_col, we arrived at (r2, col) via vertical loop
        // But the vertical loop added (r2, col).
        // Wait, loop: r != r2 + step. So r reaches r2.
        // Yes, (r2, col) is added.
    }
}

void solve_row(int r, int &curr_c) {
    // We are at (r, curr_c). Traverse to the other side of required area.
    if (curr_c == L) {
        for (int c = L + 1; c <= R; ++c) {
            add_point(r, c);
        }
        curr_c = R;
    } else { // curr_c == R
        for (int c = R - 1; c >= L; --c) {
            add_point(r, c);
        }
        curr_c = L;
    }
    row_visited[r] = true;
    if (q_ptr < Lq && q[q_ptr] == r) {
        q_ptr++;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n >> m >> L >> R >> Sx >> Sy >> Lq >> s)) return 0;
    q.resize(Lq);
    for (int i = 0; i < Lq; ++i) cin >> q[i];

    if (Lq > 0 && q[0] != Sx) {
        // Check if Sx appears later in q
        for (int x : q) {
            if (x == Sx) {
                cout << "NO" << endl;
                return 0;
            }
        }
    }

    add_point(Sx, Sy);
    int curr_r = Sx;
    int curr_c = Sy; // L
    solve_row(Sx, curr_c);

    int visited_count = 1;
    
    while (visited_count < n) {
        int target = -1;
        if (q_ptr < Lq) target = q[q_ptr];

        // 1. Try adjacent unvisited allowed
        int next_r = -1;
        int neighbors[2] = {curr_r - 1, curr_r + 1};
        vector<int> candidates;
        for (int nr : neighbors) {
            if (nr >= 1 && nr <= n && !row_visited[nr] && !is_forbidden(nr)) {
                candidates.push_back(nr);
            }
        }

        if (!candidates.empty()) {
            if (candidates.size() == 1) {
                next_r = candidates[0];
            } else {
                if (target != -1) {
                    // Prefer direction towards target
                    if (abs(target - candidates[0]) < abs(target - candidates[1])) next_r = candidates[0];
                    else next_r = candidates[1];
                } else {
                    next_r = candidates[0];
                }
            }
            
            // Execute adjacent move
            add_point(next_r, curr_c);
            curr_r = next_r;
            solve_row(curr_r, curr_c);
            visited_count++;
            continue;
        }

        // 2. Jump
        int jump_target = -1;
        int dirs[2];
        if (target != -1) {
            if (target > curr_r) { dirs[0] = 1; dirs[1] = -1; }
            else { dirs[0] = -1; dirs[1] = 1; }
        } else {
            dirs[0] = 1; dirs[1] = -1;
        }

        for (int k = 0; k < 2; ++k) {
            int d = dirs[k];
            for (int r = curr_r + d; r >= 1 && r <= n; r += d) {
                if (!row_visited[r] && !is_forbidden(r)) {
                    jump_target = r;
                    break;
                }
            }
            if (jump_target != -1) break;
        }

        if (jump_target == -1) {
            cout << "NO" << endl;
            return 0;
        }

        bool success = false;
        int dest_col = curr_c; 
        
        if (curr_c == L) {
            // Left channel
            for (int c = L - 1; c >= 1; --c) {
                if (check_channel(curr_r, jump_target, c, curr_c, dest_col)) {
                    execute_jump(curr_r, jump_target, c, curr_c, dest_col);
                    success = true;
                    break;
                }
            }
        } else {
            // Right channel
            for (int c = R + 1; c <= m; ++c) {
                if (check_channel(curr_r, jump_target, c, curr_c, dest_col)) {
                    execute_jump(curr_r, jump_target, c, curr_c, dest_col);
                    success = true;
                    break;
                }
            }
        }

        if (!success) {
            cout << "NO" << endl;
            return 0;
        }

        curr_r = jump_target;
        solve_row(curr_r, curr_c);
        visited_count++;
    }

    cout << "YES" << endl;
    cout << path.size() << endl;
    for (const auto& p : path) {
        cout << p.x << " " << p.y << "\n";
    }

    return 0;
}