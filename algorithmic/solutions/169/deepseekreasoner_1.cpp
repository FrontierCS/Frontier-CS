#include <bits/stdc++.h>
using namespace std;

const int N = 20;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    vector<string> board(N);
    for (int i = 0; i < N; ++i) {
        cin >> board[i];
    }
    
    vector<pair<int, int>> oni;
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (board[i][j] == 'x') {
                oni.emplace_back(i, j);
            }
        }
    }
    
    vector<char> dir(oni.size());
    for (size_t idx = 0; idx < oni.size(); ++idx) {
        int i = oni[idx].first, j = oni[idx].second;
        
        bool up_safe = true, down_safe = true, left_safe = true, right_safe = true;
        for (int r = 0; r < i; ++r) if (board[r][j] == 'o') { up_safe = false; break; }
        for (int r = i + 1; r < N; ++r) if (board[r][j] == 'o') { down_safe = false; break; }
        for (int c = 0; c < j; ++c) if (board[i][c] == 'o') { left_safe = false; break; }
        for (int c = j + 1; c < N; ++c) if (board[i][c] == 'o') { right_safe = false; break; }
        
        int up_cost = 2 * (i + 1);
        int down_cost = 2 * (N - i);
        int left_cost = 2 * (j + 1);
        int right_cost = 2 * (N - j);
        
        vector<pair<int, char>> options;
        if (up_safe) options.emplace_back(up_cost, 'U');
        if (down_safe) options.emplace_back(down_cost, 'D');
        if (left_safe) options.emplace_back(left_cost, 'L');
        if (right_safe) options.emplace_back(right_cost, 'R');
        
        sort(options.begin(), options.end());
        dir[idx] = options[0].second;
    }
    
    vector<vector<int>> up_col(N), down_col(N);
    vector<vector<int>> left_row(N), right_row(N);
    for (size_t idx = 0; idx < oni.size(); ++idx) {
        int i = oni[idx].first, j = oni[idx].second;
        char d = dir[idx];
        if (d == 'U') up_col[j].push_back(i);
        else if (d == 'D') down_col[j].push_back(i);
        else if (d == 'L') left_row[i].push_back(j);
        else if (d == 'R') right_row[i].push_back(j);
    }
    
    struct Op { char type; int idx; int bound; };
    vector<Op> ops;
    
    for (int j = 0; j < N; ++j) {
        if (!up_col[j].empty()) {
            int i_up = *max_element(up_col[j].begin(), up_col[j].end());
            ops.push_back({'U', j, i_up});
        }
        if (!down_col[j].empty()) {
            int i_down = *min_element(down_col[j].begin(), down_col[j].end());
            ops.push_back({'D', j, i_down});
        }
    }
    for (int i = 0; i < N; ++i) {
        if (!left_row[i].empty()) {
            int j_left = *max_element(left_row[i].begin(), left_row[i].end());
            ops.push_back({'L', i, j_left});
        }
        if (!right_row[i].empty()) {
            int j_right = *min_element(right_row[i].begin(), right_row[i].end());
            ops.push_back({'R', i, j_right});
        }
    }
    
    vector<vector<bool>> removed(N, vector<bool>(N, false));
    vector<pair<char, int>> moves;
    
    auto add_moves = [&](char d, int p, int k) {
        for (int t = 0; t < k; ++t) moves.emplace_back(d, p);
    };
    
    for (const Op& op : ops) {
        bool has_new = false;
        if (op.type == 'U') {
            for (int r = 0; r <= op.bound; ++r) {
                if (board[r][op.idx] == 'x' && !removed[r][op.idx]) {
                    has_new = true;
                    break;
                }
            }
            if (!has_new) continue;
            int k = op.bound + 1;
            add_moves('U', op.idx, k);
            add_moves('D', op.idx, k);
            for (int r = 0; r <= op.bound; ++r) {
                if (board[r][op.idx] == 'x') removed[r][op.idx] = true;
            }
        }
        else if (op.type == 'D') {
            for (int r = op.bound; r < N; ++r) {
                if (board[r][op.idx] == 'x' && !removed[r][op.idx]) {
                    has_new = true;
                    break;
                }
            }
            if (!has_new) continue;
            int k = N - op.bound;
            add_moves('D', op.idx, k);
            add_moves('U', op.idx, k);
            for (int r = op.bound; r < N; ++r) {
                if (board[r][op.idx] == 'x') removed[r][op.idx] = true;
            }
        }
        else if (op.type == 'L') {
            for (int c = 0; c <= op.bound; ++c) {
                if (board[op.idx][c] == 'x' && !removed[op.idx][c]) {
                    has_new = true;
                    break;
                }
            }
            if (!has_new) continue;
            int k = op.bound + 1;
            add_moves('L', op.idx, k);
            add_moves('R', op.idx, k);
            for (int c = 0; c <= op.bound; ++c) {
                if (board[op.idx][c] == 'x') removed[op.idx][c] = true;
            }
        }
        else if (op.type == 'R') {
            for (int c = op.bound; c < N; ++c) {
                if (board[op.idx][c] == 'x' && !removed[op.idx][c]) {
                    has_new = true;
                    break;
                }
            }
            if (!has_new) continue;
            int k = N - op.bound;
            add_moves('R', op.idx, k);
            add_moves('L', op.idx, k);
            for (int c = op.bound; c < N; ++c) {
                if (board[op.idx][c] == 'x') removed[op.idx][c] = true;
            }
        }
    }
    
    for (const auto& m : moves) {
        cout << m.first << " " << m.second << "\n";
    }
    
    return 0;
}