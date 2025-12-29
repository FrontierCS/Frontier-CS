#include <bits/stdc++.h>
using namespace std;

int compute_S(const vector<vector<int>>& board, int N) {
    vector<vector<int>> comp_id(N, vector<int>(N, -1));
    int cur_id = 0;
    int largest_tree = 0;
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (board[i][j] == 0 || comp_id[i][j] != -1) continue;
            queue<pair<int, int>> q;
            q.push({i, j});
            comp_id[i][j] = cur_id;
            vector<pair<int, int>> comp;
            comp.push_back({i, j});
            while (!q.empty()) {
                auto [x, y] = q.front(); q.pop();
                // left
                if (y > 0 && (board[x][y] & 1) && (board[x][y-1] & 4) && comp_id[x][y-1] == -1 && board[x][y-1] != 0) {
                    comp_id[x][y-1] = cur_id;
                    q.push({x, y-1});
                    comp.push_back({x, y-1});
                }
                // up
                if (x > 0 && (board[x][y] & 2) && (board[x-1][y] & 8) && comp_id[x-1][y] == -1 && board[x-1][y] != 0) {
                    comp_id[x-1][y] = cur_id;
                    q.push({x-1, y});
                    comp.push_back({x-1, y});
                }
                // right
                if (y < N-1 && (board[x][y] & 4) && (board[x][y+1] & 1) && comp_id[x][y+1] == -1 && board[x][y+1] != 0) {
                    comp_id[x][y+1] = cur_id;
                    q.push({x, y+1});
                    comp.push_back({x, y+1});
                }
                // down
                if (x < N-1 && (board[x][y] & 8) && (board[x+1][y] & 2) && comp_id[x+1][y] == -1 && board[x+1][y] != 0) {
                    comp_id[x+1][y] = cur_id;
                    q.push({x+1, y});
                    comp.push_back({x+1, y});
                }
            }
            int V = comp.size();
            int E = 0;
            for (auto [x, y] : comp) {
                // right edge
                if (y < N-1 && (board[x][y] & 4) && (board[x][y+1] & 1) && comp_id[x][y+1] == cur_id) ++E;
                // down edge
                if (x < N-1 && (board[x][y] & 8) && (board[x+1][y] & 2) && comp_id[x+1][y] == cur_id) ++E;
            }
            if (E == V - 1) largest_tree = max(largest_tree, V);
            ++cur_id;
        }
    }
    return largest_tree;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    
    int N, T;
    cin >> N >> T;
    vector<vector<int>> board(N, vector<int>(N));
    int empty_r, empty_c;
    for (int i = 0; i < N; ++i) {
        string s;
        cin >> s;
        for (int j = 0; j < N; ++j) {
            char c = s[j];
            int val;
            if ('0' <= c && c <= '9') val = c - '0';
            else val = c - 'a' + 10;
            board[i][j] = val;
            if (val == 0) {
                empty_r = i;
                empty_c = j;
            }
        }
    }

    int best_S = compute_S(board, N);
    string best_seq = "";
    string cur_seq = "";
    int moves_done = 0;
    char last_move = 0;

    random_device rd;
    mt19937 gen(rd());
    uniform_real_distribution<> dis(0.0, 1.0);

    const vector<pair<int, int>> dir_delta = {{-1, 0}, {1, 0}, {0, -1}, {0, 1}};
    const string dir_char = "UDLR";

    while (moves_done < T) {
        int current_S = compute_S(board, N);
        if (current_S == N * N - 1) {
            if (current_S > best_S) {
                best_S = current_S;
                best_seq = cur_seq;
            }
            break;
        }

        vector<pair<char, int>> moves; // (direction, new_S)
        for (int d = 0; d < 4; ++d) {
            int nr = empty_r + dir_delta[d].first;
            int nc = empty_c + dir_delta[d].second;
            if (nr < 0 || nr >= N || nc < 0 || nc >= N) continue;
            vector<vector<int>> new_board = board;
            swap(new_board[empty_r][empty_c], new_board[nr][nc]);
            int new_S = compute_S(new_board, N);
            moves.push_back({dir_char[d], new_S});
        }

        if (moves.empty()) break;

        // Filter out the move that undoes the last move, if possible
        char opposite = 0;
        if (last_move == 'U') opposite = 'D';
        else if (last_move == 'D') opposite = 'U';
        else if (last_move == 'L') opposite = 'R';
        else if (last_move == 'R') opposite = 'L';

        vector<pair<char, int>> filtered;
        for (auto& m : moves) {
            if (opposite && m.first == opposite && moves.size() > 1) continue;
            filtered.push_back(m);
        }
        if (filtered.empty()) filtered = moves;

        // Check if any move improves S
        bool has_improvement = false;
        for (auto& m : filtered) {
            if (m.second > current_S) {
                has_improvement = true;
                break;
            }
        }

        char chosen;
        if (has_improvement) {
            int best_val = -1;
            for (auto& m : filtered) {
                if (m.second > best_val) {
                    best_val = m.second;
                    chosen = m.first;
                } else if (m.second == best_val && dis(gen) < 0.5) {
                    chosen = m.first;
                }
            }
        } else {
            double progress = (double)(T - moves_done) / T;
            double p_random = 0.01 + (0.3 - 0.01) * progress;
            if (dis(gen) < p_random) {
                uniform_int_distribution<> idx_dis(0, filtered.size() - 1);
                chosen = filtered[idx_dis(gen)].first;
            } else {
                int best_val = -1;
                for (auto& m : filtered) {
                    if (m.second > best_val) {
                        best_val = m.second;
                        chosen = m.first;
                    }
                }
            }
        }

        // Apply the chosen move
        int dr = 0, dc = 0;
        if (chosen == 'U') dr = -1;
        else if (chosen == 'D') dr = 1;
        else if (chosen == 'L') dc = -1;
        else if (chosen == 'R') dc = 1;
        int nr = empty_r + dr;
        int nc = empty_c + dc;
        swap(board[empty_r][empty_c], board[nr][nc]);
        empty_r = nr;
        empty_c = nc;
        cur_seq += chosen;
        last_move = chosen;
        ++moves_done;

        int new_S = compute_S(board, N);
        if (new_S > best_S) {
            best_S = new_S;
            best_seq = cur_seq;
        }
    }

    cout << best_seq << endl;
    return 0;
}