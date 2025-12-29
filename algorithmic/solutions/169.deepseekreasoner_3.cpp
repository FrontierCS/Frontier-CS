#include <bits/stdc++.h>
using namespace std;

const int N = 20;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n; // n is always 20
    vector<string> grid(n);
    for (int i = 0; i < n; ++i) {
        cin >> grid[i];
    }

    // positions of Oni and Fukunokami
    vector<pair<int, int>> oni_pos;
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            if (grid[i][j] == 'x') {
                oni_pos.emplace_back(i, j);
            }
        }
    }

    // for each column, compute min and max row of Fukunokami
    vector<int> min_f_row(n, n), max_f_row(n, -1);
    // for each row, compute min and max column of Fukunokami
    vector<int> min_f_col(n, n), max_f_col(n, -1);

    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            if (grid[i][j] == 'o') {
                min_f_row[j] = min(min_f_row[j], i);
                max_f_row[j] = max(max_f_row[j], i);
                min_f_col[i] = min(min_f_col[i], j);
                max_f_col[i] = max(max_f_col[i], j);
            }
        }
    }

    // store assigned direction for each Oni
    vector<char> dir(oni_pos.size());
    vector<int> oni_i(oni_pos.size()), oni_j(oni_pos.size());

    // per column lists for up/down, per row lists for left/right (initial assignment)
    vector<vector<int>> up_rows(n), down_rows(n);
    vector<vector<int>> left_cols(n), right_cols(n);

    // assign each Oni to a direction greedily
    for (size_t idx = 0; idx < oni_pos.size(); ++idx) {
        int i = oni_pos[idx].first;
        int j = oni_pos[idx].second;
        oni_i[idx] = i;
        oni_j[idx] = j;

        bool up_safe   = (i < min_f_row[j]);
        bool down_safe = (i > max_f_row[j]);
        bool left_safe = (j < min_f_col[i]);
        bool right_safe= (j > max_f_col[i]);

        int up_cost    = 2 * (i + 1);
        int down_cost  = 2 * (n - i);
        int left_cost  = 2 * (j + 1);
        int right_cost = 2 * (n - j);

        int best_cost = INT_MAX;
        char best_dir = 0;
        if (up_safe && up_cost < best_cost) {
            best_cost = up_cost;
            best_dir = 'U';
        }
        if (down_safe && down_cost < best_cost) {
            best_cost = down_cost;
            best_dir = 'D';
        }
        if (left_safe && left_cost < best_cost) {
            best_cost = left_cost;
            best_dir = 'L';
        }
        if (right_safe && right_cost < best_cost) {
            best_cost = right_cost;
            best_dir = 'R';
        }

        dir[idx] = best_dir;
        if (best_dir == 'U') {
            up_rows[j].push_back(i);
        } else if (best_dir == 'D') {
            down_rows[j].push_back(i);
        } else if (best_dir == 'L') {
            left_cols[i].push_back(j);
        } else { // 'R'
            right_cols[i].push_back(j);
        }
    }

    // compute up_max and down_min for each column
    vector<int> up_max(n, -1), down_min(n, n);
    for (int j = 0; j < n; ++j) {
        if (!up_rows[j].empty()) {
            up_max[j] = *max_element(up_rows[j].begin(), up_rows[j].end());
        }
        if (!down_rows[j].empty()) {
            down_min[j] = *min_element(down_rows[j].begin(), down_rows[j].end());
        }
    }

    // filter row assignments: only keep Oni that survive column operations
    vector<vector<int>> left_cols_filt(n), right_cols_filt(n);
    for (size_t idx = 0; idx < oni_pos.size(); ++idx) {
        char d = dir[idx];
        if (d == 'L' || d == 'R') {
            int i = oni_i[idx];
            int j = oni_j[idx];
            // check if this Oni is removed by column operations
            if (i <= up_max[j] || i >= down_min[j]) {
                // will be removed as collateral, skip row operation
                continue;
            }
            if (d == 'L') {
                left_cols_filt[i].push_back(j);
            } else {
                right_cols_filt[i].push_back(j);
            }
        }
    }

    // generate moves
    vector<pair<char, int>> moves;

    // column operations
    for (int j = 0; j < n; ++j) {
        if (!up_rows[j].empty()) {
            int t = up_max[j] + 1;
            for (int k = 0; k < t; ++k) moves.emplace_back('U', j);
            for (int k = 0; k < t; ++k) moves.emplace_back('D', j);
        }
        if (!down_rows[j].empty()) {
            int t = n - down_min[j];
            for (int k = 0; k < t; ++k) moves.emplace_back('D', j);
            for (int k = 0; k < t; ++k) moves.emplace_back('U', j);
        }
    }

    // row operations (only for surviving Oni)
    for (int i = 0; i < n; ++i) {
        if (!left_cols_filt[i].empty()) {
            int max_col = *max_element(left_cols_filt[i].begin(), left_cols_filt[i].end());
            int t = max_col + 1;
            for (int k = 0; k < t; ++k) moves.emplace_back('L', i);
            for (int k = 0; k < t; ++k) moves.emplace_back('R', i);
        }
        if (!right_cols_filt[i].empty()) {
            int min_col = *min_element(right_cols_filt[i].begin(), right_cols_filt[i].end());
            int t = n - min_col;
            for (int k = 0; k < t; ++k) moves.emplace_back('R', i);
            for (int k = 0; k < t; ++k) moves.emplace_back('L', i);
        }
    }

    // output
    cout << moves.size() << "\n"; // not required, but we output moves directly
    for (auto& [d, p] : moves) {
        cout << d << " " << p << "\n";
    }

    return 0;
}