#include <iostream>
#include <vector>
#include <queue>
#include <algorithm>
using namespace std;

const int N = 10;

void simulate_tilt(const vector<vector<int>>& board, vector<vector<int>>& newboard, char dir) {
    // initialize newboard to zeros
    for (int i = 0; i < N; i++)
        for (int j = 0; j < N; j++)
            newboard[i][j] = 0;

    if (dir == 'L') {
        for (int i = 0; i < N; i++) {
            vector<int> candies;
            for (int j = 0; j < N; j++)
                if (board[i][j] != 0)
                    candies.push_back(board[i][j]);
            int k = 0;
            for (int val : candies)
                newboard[i][k++] = val;
        }
    } else if (dir == 'R') {
        for (int i = 0; i < N; i++) {
            vector<int> candies;
            for (int j = 0; j < N; j++)
                if (board[i][j] != 0)
                    candies.push_back(board[i][j]);
            int k = candies.size();
            int start = N - k;
            for (int idx = 0; idx < k; idx++)
                newboard[i][start + idx] = candies[idx];
        }
    } else if (dir == 'F') {
        for (int j = 0; j < N; j++) {
            vector<int> candies;
            for (int i = 0; i < N; i++)
                if (board[i][j] != 0)
                    candies.push_back(board[i][j]);
            int k = 0;
            for (int val : candies)
                newboard[k++][j] = val;
        }
    } else if (dir == 'B') {
        for (int j = 0; j < N; j++) {
            vector<int> candies;
            for (int i = 0; i < N; i++)
                if (board[i][j] != 0)
                    candies.push_back(board[i][j]);
            int k = candies.size();
            int start = N - k;
            for (int idx = 0; idx < k; idx++)
                newboard[start + idx][j] = candies[idx];
        }
    }
}

int compute_pairs(const vector<vector<int>>& board) {
    int pairs = 0;
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            if (board[i][j] == 0) continue;
            if (i + 1 < N && board[i+1][j] == board[i][j]) pairs++;
            if (j + 1 < N && board[i][j+1] == board[i][j]) pairs++;
        }
    }
    return pairs;
}

int compute_score(const vector<vector<int>>& board) {
    vector<vector<bool>> visited(N, vector<bool>(N, false));
    int total = 0;
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            if (board[i][j] == 0 || visited[i][j]) continue;
            int flavor = board[i][j];
            queue<pair<int,int>> q;
            q.push({i, j});
            visited[i][j] = true;
            int sz = 0;
            while (!q.empty()) {
                auto [r, c] = q.front(); q.pop();
                sz++;
                int dr[] = {1, -1, 0, 0};
                int dc[] = {0, 0, 1, -1};
                for (int d = 0; d < 4; d++) {
                    int nr = r + dr[d];
                    int nc = c + dc[d];
                    if (nr >= 0 && nr < N && nc >= 0 && nc < N && !visited[nr][nc] && board[nr][nc] == flavor) {
                        visited[nr][nc] = true;
                        q.push({nr, nc});
                    }
                }
            }
            total += sz * sz;
        }
    }
    return total;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    vector<int> flavors(100);
    for (int i = 0; i < 100; i++)
        cin >> flavors[i];

    vector<vector<int>> board(N, vector<int>(N, 0));

    for (int t = 0; t < 100; t++) {
        int p;
        cin >> p;
        // place the t-th candy at the p-th empty cell (1-indexed)
        int cnt = 0;
        int row = -1, col = -1;
        for (int i = 0; i < N && row == -1; i++) {
            for (int j = 0; j < N; j++) {
                if (board[i][j] == 0) {
                    cnt++;
                    if (cnt == p) {
                        row = i;
                        col = j;
                        break;
                    }
                }
            }
        }
        board[row][col] = flavors[t];

        char best_dir = 'F';
        int best_comp = -1;
        int best_pairs = -1;
        vector<char> dirs = {'F', 'B', 'L', 'R'};
        for (char dir : dirs) {
            vector<vector<int>> newboard(N, vector<int>(N, 0));
            simulate_tilt(board, newboard, dir);
            int comp = compute_score(newboard);
            int pairs = compute_pairs(newboard);
            if (comp > best_comp || (comp == best_comp && pairs > best_pairs)) {
                best_comp = comp;
                best_pairs = pairs;
                best_dir = dir;
            }
        }

        cout << best_dir << endl;

        // actually tilt the board
        vector<vector<int>> newboard(N, vector<int>(N, 0));
        simulate_tilt(board, newboard, best_dir);
        board = newboard;
    }

    return 0;
}