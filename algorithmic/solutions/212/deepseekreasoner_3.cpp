#include <bits/stdc++.h>
using namespace std;

int n, m, L, R, Sx, Sy, Lq, s;
vector<int> q;
int req_count; // required cells per row = R-L+1
vector<int> required_left;
vector<vector<bool>> visited;
vector<pair<int, int>> path;
vector<int> p_seq;
int matched_idx;
bool found;
chrono::steady_clock::time_point start_time;
const double TIME_LIMIT = 29.0; // seconds

// directions: up, down, left, right
const int dx[4] = {-1, 1, 0, 0};
const int dy[4] = {0, 0, -1, 1};

bool is_required(int x, int y) {
    return y >= L && y <= R;
}

// check if sub is a subsequence of seq
bool is_subsequence(const vector<int>& sub, const vector<int>& seq) {
    int i = 0;
    for (int x : seq) {
        if (i < (int)sub.size() && sub[i] == x) i++;
    }
    return i == (int)sub.size();
}

// generate snake path for a given row order π (size n)
vector<pair<int,int>> generate_snake_path(const vector<int>& order) {
    vector<pair<int,int>> res;
    int row = order[0];
    // start at (row, L)
    int x = row, y = L;
    res.emplace_back(x, y);
    // we will traverse each row according to its entry side
    // entry side for order[i]: if i is 0-based even -> left, odd -> right
    for (int i = 0; i < n; i++) {
        row = order[i];
        bool enter_left = (i % 2 == 0);
        int start_col = enter_left ? L : R;
        int end_col = enter_left ? R : L;
        // if i>0, we are already at the entry point (from transition)
        // so we only need to traverse from start_col to end_col (excluding start_col)
        if (i > 0) {
            // we are already at (row, start_col) from transition
            // just add the traversal within the row
            int step = (start_col < end_col) ? 1 : -1;
            for (int col = start_col + step; col != end_col + step; col += step) {
                res.emplace_back(row, col);
            }
        } else {
            // first row: we start at (row, L) which is start_col if enter_left, otherwise we need to move to start_col
            if (start_col != y) {
                int step = (y < start_col) ? 1 : -1;
                for (int col = y + step; col != start_col + step; col += step) {
                    res.emplace_back(row, col);
                }
            }
            // then traverse to end_col
            int step = (start_col < end_col) ? 1 : -1;
            for (int col = start_col + step; col != end_col + step; col += step) {
                res.emplace_back(row, col);
            }
        }
        // transition to next row if not last
        if (i < n-1) {
            int next_row = order[i+1];
            bool next_enter_left = ((i+1) % 2 == 0);
            int next_start_col = next_enter_left ? L : R;
            // current exit point is (row, end_col)
            // move vertically to (next_row, end_col) if same column, else should not happen
            // since exit_col should equal next_start_col by construction (they alternate)
            // So we simply move vertically
            int step_row = (next_row > row) ? 1 : -1;
            for (int r = row + step_row; r != next_row + step_row; r += step_row) {
                res.emplace_back(r, end_col);
            }
        }
    }
    return res;
}

// check if we can still complete the current row (if we are in a row)
bool can_complete_current_row(int row, int cur_y, const vector<bool>& row_visited_cols) {
    // row_visited_cols is for columns L..R only? Actually we need to consider non-required cells in the row as well.
    // We'll do a BFS within the row (only columns 1..m) to see if all unvisited required cells are reachable.
    // But we only care about required cells in this row.
    // We'll compute the set of unvisited required columns in this row.
    vector<bool> unvisited_req(m+1, false);
    for (int col = L; col <= R; col++) {
        if (!visited[row][col]) unvisited_req[col] = true;
    }
    // BFS from cur_y in the same row, only moving left/right, through unvisited cells (both required and non-required)
    vector<bool> col_vis(m+1, false);
    queue<int> qq;
    qq.push(cur_y);
    col_vis[cur_y] = true;
    while (!qq.empty()) {
        int y = qq.front(); qq.pop();
        for (int d = 2; d < 4; d++) { // left and right
            int ny = y + dy[d];
            if (ny < 1 || ny > m) continue;
            if (visited[row][ny]) continue;
            if (col_vis[ny]) continue;
            col_vis[ny] = true;
            qq.push(ny);
        }
    }
    for (int col = L; col <= R; col++) {
        if (unvisited_req[col] && !col_vis[col]) return false;
    }
    return true;
}

// prune based on q and remaining rows
bool prune_q_possible() {
    int remaining_rows = 0;
    for (int i = 1; i <= n; i++) {
        if (required_left[i] > 0) remaining_rows++;
    }
    int remaining_q = Lq - matched_idx;
    if (remaining_rows < remaining_q) return true;
    if (remaining_q == 0) return false;
    // check if the next required q[matched_idx] is among remaining rows
    int need = q[matched_idx];
    if (required_left[need] == 0) return true; // already completed or entered? if required_left[need] == 0, then row need is done, cannot enter again
    // also, if need is not in remaining rows? but we checked required_left[need] > 0
    // additionally, we need to ensure that we can still match the rest in order. This is a simple necessary condition: 
    // the remaining rows must contain the remaining q elements in order. We'll just check that each q element appears in remaining rows in order.
    // but we already check next element. For deeper, we can't easily check without knowing order.
    return false;
}

// DFS search
bool dfs(int x, int y, int current_row) {
    if (found) return true;
    // check time
    auto now = chrono::steady_clock::now();
    chrono::duration<double> elapsed = now - start_time;
    if (elapsed.count() > TIME_LIMIT) return false;

    // if all required cells visited, success
    bool all_done = true;
    for (int i = 1; i <= n; i++) {
        if (required_left[i] > 0) {
            all_done = false;
            break;
        }
    }
    if (all_done) {
        found = true;
        return true;
    }

    // prune based on q
    if (prune_q_possible()) return false;

    // if we are in a row, check if we can still complete it
    if (current_row != 0) {
        if (!can_complete_current_row(current_row, y, vector<bool>())) return false;
    }

    // generate moves
    vector<int> dirs = {0,1,2,3};
    // shuffle to avoid getting stuck in bad order
    random_shuffle(dirs.begin(), dirs.end());

    for (int d : dirs) {
        int nx = x + dx[d];
        int ny = y + dy[d];
        if (nx < 1 || nx > n || ny < 1 || ny > m) continue;
        if (visited[nx][ny]) continue;

        // check constraints based on current_row
        if (current_row != 0) {
            // must stay in the same row
            if (nx != current_row) continue;
        } else {
            // if moving to a required cell, it must be of an unentered row
            if (is_required(nx, ny)) {
                int r = nx;
                if (required_left[r] == 0) continue; // row already completed
                // check if this is the first required cell of row r (i.e., required_left[r] == req_count)
                if (required_left[r] != req_count) continue; // already entered, cannot step on its required cells again
            }
        }

        // take the move
        visited[nx][ny] = true;
        path.emplace_back(nx, ny);
        int old_current_row = current_row;
        int old_matched = matched_idx;
        bool entered_new_row = false;
        int row_entered = 0;

        if (is_required(nx, ny)) {
            int r = nx;
            required_left[r]--;
            if (old_current_row == 0) {
                // entering row r for the first time
                current_row = r;
                p_seq.push_back(r);
                if (matched_idx < Lq && q[matched_idx] == r) {
                    matched_idx++;
                }
                entered_new_row = true;
                row_entered = r;
            }
        }

        if (dfs(nx, ny, current_row)) return true;

        // backtrack
        if (entered_new_row) {
            p_seq.pop_back();
            matched_idx = old_matched;
            current_row = 0;
        }
        if (is_required(nx, ny)) {
            int r = nx;
            required_left[r]++;
        }
        path.pop_back();
        visited[nx][ny] = false;
    }
    return false;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(0);
    start_time = chrono::steady_clock::now();

    cin >> n >> m >> L >> R >> Sx >> Sy >> Lq >> s;
    q.resize(Lq);
    for (int i = 0; i < Lq; i++) cin >> q[i];

    // check start condition
    if (Sy != L) {
        // problem guarantees Sy = L, but just in case
        cout << "NO\n";
        return 0;
    }

    req_count = R - L + 1;
    required_left.assign(n+1, req_count);

    // generate snake orders A and B
    vector<int> orderA, orderB;
    // order A: Sx, Sx+1, ..., n, then n-1, ..., 1 (excluding already visited)
    for (int i = Sx; i <= n; i++) orderA.push_back(i);
    for (int i = n-1; i >= 1; i--) {
        if (i >= Sx) continue; // already in orderA
        orderA.push_back(i);
    }
    // order B: Sx, Sx-1, ..., 1, then 2, ..., n (excluding already visited)
    for (int i = Sx; i >= 1; i--) orderB.push_back(i);
    for (int i = 2; i <= n; i++) {
        if (i <= Sx) continue;
        orderB.push_back(i);
    }

    // check if q is subsequence of orderA or orderB
    if (is_subsequence(q, orderA)) {
        vector<pair<int,int>> snake_path = generate_snake_path(orderA);
        cout << "YES\n";
        cout << snake_path.size() << "\n";
        for (auto& p : snake_path) {
            cout << p.first << " " << p.second << "\n";
        }
        return 0;
    }
    if (is_subsequence(q, orderB)) {
        vector<pair<int,int>> snake_path = generate_snake_path(orderB);
        cout << "YES\n";
        cout << snake_path.size() << "\n";
        for (auto& p : snake_path) {
            cout << p.first << " " << p.second << "\n";
        }
        return 0;
    }

    // if no auxiliary columns, then no other orders possible
    if (L == 1 && R == m) {
        cout << "NO\n";
        return 0;
    }

    // otherwise, try DFS
    visited.assign(n+1, vector<bool>(m+1, false));
    // start at (Sx, Sy)
    visited[Sx][Sy] = true;
    path.emplace_back(Sx, Sy);
    required_left[Sx]--;
    p_seq.push_back(Sx);
    matched_idx = 0;
    if (Lq > 0 && q[0] == Sx) matched_idx = 1;
    found = false;

    if (dfs(Sx, Sy, Sx)) {
        cout << "YES\n";
        cout << path.size() << "\n";
        for (auto& p : path) {
            cout << p.first << " " << p.second << "\n";
        }
    } else {
        cout << "NO\n";
    }

    return 0;
}