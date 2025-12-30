#include <bits/stdc++.h>
using namespace std;

const int LEFT = 1;
const int UP = 2;
const int RIGHT = 4;
const int DOWN = 8;

int compute_tree_vertices(const vector<vector<int>>& board) {
    int N = board.size();
    vector<vector<bool>> visited(N, vector<bool>(N, false));
    int total = 0;
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (board[i][j] == 0 || visited[i][j]) continue;
            // BFS to find component
            queue<pair<int,int>> q;
            q.push({i, j});
            visited[i][j] = true;
            vector<pair<int,int>> comp;
            while (!q.empty()) {
                auto [r, c] = q.front(); q.pop();
                comp.push_back({r, c});
                // left
                if (c > 0 && (board[r][c] & LEFT) && board[r][c-1] != 0 && (board[r][c-1] & RIGHT)) {
                    if (!visited[r][c-1]) { visited[r][c-1] = true; q.push({r, c-1}); }
                }
                // up
                if (r > 0 && (board[r][c] & UP) && board[r-1][c] != 0 && (board[r-1][c] & DOWN)) {
                    if (!visited[r-1][c]) { visited[r-1][c] = true; q.push({r-1, c}); }
                }
                // right
                if (c+1 < N && (board[r][c] & RIGHT) && board[r][c+1] != 0 && (board[r][c+1] & LEFT)) {
                    if (!visited[r][c+1]) { visited[r][c+1] = true; q.push({r, c+1}); }
                }
                // down
                if (r+1 < N && (board[r][c] & DOWN) && board[r+1][c] != 0 && (board[r+1][c] & UP)) {
                    if (!visited[r+1][c]) { visited[r+1][c] = true; q.push({r+1, c}); }
                }
            }
            int V = comp.size();
            int E = 0;
            for (auto [r, c] : comp) {
                // count edges only once (right and down)
                if (c+1 < N && (board[r][c] & RIGHT) && board[r][c+1] != 0 && (board[r][c+1] & LEFT)) ++E;
                if (r+1 < N && (board[r][c] & DOWN) && board[r+1][c] != 0 && (board[r+1][c] & UP)) ++E;
            }
            if (E == V - 1) total += V;
        }
    }
    return total;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    int N, T;
    cin >> N >> T;
    vector<vector<int>> board(N, vector<int>(N));
    pair<int,int> empty_pos;
    for (int i = 0; i < N; ++i) {
        string s;
        cin >> s;
        for (int j = 0; j < N; ++j) {
            char c = s[j];
            if (c >= '0' && c <= '9') board[i][j] = c - '0';
            else board[i][j] = 10 + (c - 'a');
            if (board[i][j] == 0) empty_pos = {i, j};
        }
    }

    // random setup
    random_device rd;
    mt19937 rng(rd());
    uniform_real_distribution<double> dist(0.0, 1.0);

    vector<vector<int>> cur_board = board;
    pair<int,int> cur_empty = empty_pos;
    int cur_score = compute_tree_vertices(cur_board);
    int best_score = cur_score;
    vector<char> moves;
    int best_moves_len = 0;
    int moves_accepted = 0;
    char last_move = 0;
    double temp = 1.0;
    const double cooling_rate = 0.9997;
    const int MAX_ITER = T * 10;

    for (int iter = 0; iter < MAX_ITER; ++iter) {
        if (moves_accepted >= T) break;
        if (best_score == N*N - 1) break;

        // collect possible moves (avoid immediate reversal)
        vector<char> candidates;
        int er = cur_empty.first, ec = cur_empty.second;
        if (er > 0 && last_move != 'D') candidates.push_back('U');
        if (er < N-1 && last_move != 'U') candidates.push_back('D');
        if (ec > 0 && last_move != 'R') candidates.push_back('L');
        if (ec < N-1 && last_move != 'L') candidates.push_back('R');
        if (candidates.empty()) {
            // fallback: allow all directions
            if (er > 0) candidates.push_back('U');
            if (er < N-1) candidates.push_back('D');
            if (ec > 0) candidates.push_back('L');
            if (ec < N-1) candidates.push_back('R');
        }

        char move = candidates[uniform_int_distribution<>(0, candidates.size()-1)(rng)];
        int nr = er, nc = ec;
        if (move == 'U') --nr;
        else if (move == 'D') ++nr;
        else if (move == 'L') --nc;
        else if (move == 'R') ++nc;

        // apply move
        swap(cur_board[er][ec], cur_board[nr][nc]);
        int new_score = compute_tree_vertices(cur_board);
        double delta = new_score - cur_score;
        bool accept = false;
        if (delta > 0) accept = true;
        else {
            double prob = exp(delta / temp);
            if (dist(rng) < prob) accept = true;
        }

        if (accept) {
            cur_score = new_score;
            cur_empty = {nr, nc};
            moves.push_back(move);
            ++moves_accepted;
            last_move = move;
            if (cur_score > best_score) {
                best_score = cur_score;
                best_moves_len = moves.size();
            }
        } else {
            // revert
            swap(cur_board[er][ec], cur_board[nr][nc]);
        }

        temp *= cooling_rate;
    }

    string answer(moves.begin(), moves.begin() + best_moves_len);
    cout << answer << endl;

    return 0;
}