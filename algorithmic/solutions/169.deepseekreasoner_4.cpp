#include <iostream>
#include <vector>
#include <algorithm>
#include <utility>
#include <string>

using namespace std;

const int N = 20;

bool is_safe(int i, int j, char dir, const vector<vector<int>>& board) {
    if (dir == 'U') {
        for (int k = 0; k < i; ++k)
            if (board[k][j] == 2) return false;
        return true;
    } else if (dir == 'D') {
        for (int k = i + 1; k < N; ++k)
            if (board[k][j] == 2) return false;
        return true;
    } else if (dir == 'L') {
        for (int k = 0; k < j; ++k)
            if (board[i][k] == 2) return false;
        return true;
    } else if (dir == 'R') {
        for (int k = j + 1; k < N; ++k)
            if (board[i][k] == 2) return false;
        return true;
    }
    return false;
}

int cost(int i, int j, char dir) {
    if (dir == 'U') return 2 * (i + 1);
    if (dir == 'D') return 2 * (N - i);
    if (dir == 'L') return 2 * (j + 1);
    if (dir == 'R') return 2 * (N - j);
    return 1000000;
}

void apply_shift(char dir, int p, vector<vector<int>>& board, vector<pair<char, int>>& output) {
    output.push_back({dir, p});
    if (dir == 'L') {
        for (int j = 0; j < N - 1; ++j)
            board[p][j] = board[p][j + 1];
        board[p][N - 1] = 0;
    } else if (dir == 'R') {
        for (int j = N - 1; j > 0; --j)
            board[p][j] = board[p][j - 1];
        board[p][0] = 0;
    } else if (dir == 'U') {
        for (int i = 0; i < N - 1; ++i)
            board[i][p] = board[i + 1][p];
        board[N - 1][p] = 0;
    } else if (dir == 'D') {
        for (int i = N - 1; i > 0; --i)
            board[i][p] = board[i - 1][p];
        board[0][p] = 0;
    }
}

void perform_removal(int i, int j, char dir, vector<vector<int>>& board, vector<pair<char, int>>& output) {
    int k;
    if (dir == 'U') {
        k = i + 1;
        for (int t = 0; t < k; ++t) apply_shift('U', j, board, output);
        for (int t = 0; t < k; ++t) apply_shift('D', j, board, output);
    } else if (dir == 'D') {
        k = N - i;
        for (int t = 0; t < k; ++t) apply_shift('D', j, board, output);
        for (int t = 0; t < k; ++t) apply_shift('U', j, board, output);
    } else if (dir == 'L') {
        k = j + 1;
        for (int t = 0; t < k; ++t) apply_shift('L', i, board, output);
        for (int t = 0; t < k; ++t) apply_shift('R', i, board, output);
    } else if (dir == 'R') {
        k = N - j;
        for (int t = 0; t < k; ++t) apply_shift('R', i, board, output);
        for (int t = 0; t < k; ++t) apply_shift('L', i, board, output);
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    vector<vector<int>> board(N, vector<int>(N, 0));
    vector<pair<int, int>> init_oni;

    for (int i = 0; i < N; ++i) {
        string s;
        cin >> s;
        for (int j = 0; j < N; ++j) {
            if (s[j] == 'x') {
                board[i][j] = 1;
                init_oni.push_back({i, j});
            } else if (s[j] == 'o') {
                board[i][j] = 2;
            }
        }
    }

    vector<pair<char, int>> output;

    while (true) {
        vector<pair<int, int>> current_oni;
        for (int i = 0; i < N; ++i)
            for (int j = 0; j < N; ++j)
                if (board[i][j] == 1)
                    current_oni.push_back({i, j});

        if (current_oni.empty()) break;

        // sort by distance to nearest edge (prefer edges first)
        sort(current_oni.begin(), current_oni.end(),
             [](const pair<int, int>& a, const pair<int, int>& b) {
                 int da = min({a.first, N - 1 - a.first, a.second, N - 1 - a.second});
                 int db = min({b.first, N - 1 - b.first, b.second, N - 1 - b.second});
                 return da < db;
             });

        bool removed = false;
        for (const auto& p : current_oni) {
            int i = p.first, j = p.second;
            if (board[i][j] != 1) continue; // already removed

            vector<char> safe_dirs;
            for (char dir : {'U', 'D', 'L', 'R'}) {
                if (is_safe(i, j, dir, board))
                    safe_dirs.push_back(dir);
            }
            if (safe_dirs.empty()) continue;

            char best_dir = safe_dirs[0];
            int best_cost = cost(i, j, best_dir);
            for (char dir : safe_dirs) {
                int c = cost(i, j, dir);
                if (c < best_cost) {
                    best_cost = c;
                    best_dir = dir;
                }
            }

            perform_removal(i, j, best_dir, board, output);
            removed = true;
            break; // board changed, rescan
        }

        if (!removed) {
            // should not happen under guarantees
            break;
        }
    }

    for (const auto& move : output) {
        cout << move.first << " " << move.second << "\n";
    }

    return 0;
}