#include <iostream>
#include <vector>
#include <queue>
#include <algorithm>
#include <tuple>

using namespace std;

const int N = 10;

vector<vector<int>> tilt(const vector<vector<int>>& board, char dir) {
    vector<vector<int>> new_board(N, vector<int>(N, 0));
    if (dir == 'L') {
        for (int r = 0; r < N; ++r) {
            int write = 0;
            for (int c = 0; c < N; ++c) {
                if (board[r][c] != 0) {
                    new_board[r][write++] = board[r][c];
                }
            }
        }
    } else if (dir == 'R') {
        for (int r = 0; r < N; ++r) {
            int write = N - 1;
            for (int c = N - 1; c >= 0; --c) {
                if (board[r][c] != 0) {
                    new_board[r][write--] = board[r][c];
                }
            }
        }
    } else if (dir == 'F') {
        for (int c = 0; c < N; ++c) {
            int write = 0;
            for (int r = 0; r < N; ++r) {
                if (board[r][c] != 0) {
                    new_board[write++][c] = board[r][c];
                }
            }
        }
    } else if (dir == 'B') {
        for (int c = 0; c < N; ++c) {
            int write = N - 1;
            for (int r = 0; r < N; ++r) {
                if (board[r][c] != 0) {
                    new_board[write--][c] = board[r][c];
                }
            }
        }
    }
    return new_board;
}

int compute_score(const vector<vector<int>>& board) {
    vector<vector<bool>> visited(N, vector<bool>(N, false));
    int score = 0;
    const int dr[4] = {-1, 1, 0, 0};
    const int dc[4] = {0, 0, -1, 1};
    for (int r = 0; r < N; ++r) {
        for (int c = 0; c < N; ++c) {
            if (board[r][c] != 0 && !visited[r][c]) {
                int flavor = board[r][c];
                int size = 0;
                queue<pair<int, int>> q;
                q.push({r, c});
                visited[r][c] = true;
                while (!q.empty()) {
                    auto [cr, cc] = q.front(); q.pop();
                    ++size;
                    for (int d = 0; d < 4; ++d) {
                        int nr = cr + dr[d];
                        int nc = cc + dc[d];
                        if (nr >= 0 && nr < N && nc >= 0 && nc < N && !visited[nr][nc] && board[nr][nc] == flavor) {
                            visited[nr][nc] = true;
                            q.push({nr, nc});
                        }
                    }
                }
                score += size * size;
            }
        }
    }
    return score;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    vector<int> flavors(100);
    for (int i = 0; i < 100; ++i) {
        cin >> flavors[i];
    }

    vector<vector<int>> board(N, vector<int>(N, 0));
    vector<char> dirs = {'F', 'B', 'L', 'R'};

    for (int t = 0; t < 100; ++t) {
        int p;
        cin >> p;
        --p; // convert to 0-index

        // collect empty cells in front-to-back, left-to-right order
        vector<pair<int, int>> empties;
        for (int r = 0; r < N; ++r) {
            for (int c = 0; c < N; ++c) {
                if (board[r][c] == 0) {
                    empties.push_back({r, c});
                }
            }
        }
        auto [r_new, c_new] = empties[p];
        board[r_new][c_new] = flavors[t];

        // evaluate each tilt direction
        int best_score = -1;
        char best_dir = 'F';
        for (char dir : dirs) {
            vector<vector<int>> new_board = tilt(board, dir);
            int sc = compute_score(new_board);
            if (sc > best_score) {
                best_score = sc;
                best_dir = dir;
            }
        }

        // actually tilt the board
        board = tilt(board, best_dir);
        cout << best_dir << endl;
    }

    return 0;
}