#include <bits/stdc++.h>
using namespace std;

struct Vehicle {
    bool horiz;
    int len;
    int fixed; // row if horiz, col if vertical
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int initialBoard[6][6];
    int maxId = 0;
    for (int i = 0; i < 6; ++i) {
        for (int j = 0; j < 6; ++j) {
            if (!(cin >> initialBoard[i][j])) return 0;
            maxId = max(maxId, initialBoard[i][j]);
        }
    }

    int n = maxId;
    if (n == 0) {
        // Degenerate, but problem guarantees at least red car
        cout << 0 << " " << 0 << "\n";
        return 0;
    }

    vector<int> min_r(n + 1, 6), max_r(n + 1, -1);
    vector<int> min_c(n + 1, 6), max_c(n + 1, -1);

    for (int r = 0; r < 6; ++r) {
        for (int c = 0; c < 6; ++c) {
            int id = initialBoard[r][c];
            if (id > 0) {
                min_r[id] = min(min_r[id], r);
                max_r[id] = max(max_r[id], r);
                min_c[id] = min(min_c[id], c);
                max_c[id] = max(max_c[id], c);
            }
        }
    }

    vector<Vehicle> veh(n + 1);
    vector<int> pos_init(n + 1, 0);

    for (int id = 1; id <= n; ++id) {
        if (min_r[id] == 6) continue; // should not happen in valid input
        bool horiz = (min_r[id] == max_r[id]);
        if (horiz) {
            int len = max_c[id] - min_c[id] + 1;
            int row = min_r[id];
            veh[id] = {true, len, row};
            pos_init[id] = min_c[id];
        } else {
            int len = max_r[id] - min_r[id] + 1;
            int col = min_c[id];
            veh[id] = {false, len, col};
            pos_init[id] = min_r[id];
        }
    }

    using ull = unsigned long long;

    auto decode = [&](ull key, int pos[]) {
        for (int id = 1; id <= n; ++id) {
            pos[id] = (int)((key >> (3 * (id - 1))) & 7ULL);
        }
    };

    auto encode_from_array = [&](int pos[]) -> ull {
        ull key = 0;
        for (int id = 1; id <= n; ++id) {
            key |= (ull(pos[id]) << (3 * (id - 1)));
        }
        return key;
    };

    // Initial state
    int tmp_pos[11];
    for (int id = 1; id <= n; ++id) tmp_pos[id] = pos_init[id];
    ull startKey = encode_from_array(tmp_pos);

    unordered_map<ull, int> dist;
    dist.reserve(4000000);
    dist.max_load_factor(0.7f);

    queue<ull> q;
    q.push(startKey);
    dist[startKey] = 0;

    int board[6][6];
    int pos[11];

    int answerSteps = -1;

    while (!q.empty()) {
        ull key = q.front();
        q.pop();
        int d = dist[key];

        decode(key, pos);
        if (pos[1] == 6) { // red car fully out
            answerSteps = d;
            break;
        }

        memset(board, 0, sizeof(board));
        for (int id = 1; id <= n; ++id) {
            if (id == 1 && pos[1] >= 6) continue; // red fully out, but we'd have broken earlier
            Vehicle &vh = veh[id];
            if (vh.horiz) {
                int r = vh.fixed;
                for (int k = 0; k < vh.len; ++k) {
                    int c = pos[id] + k;
                    if (0 <= c && c < 6) board[r][c] = id;
                }
            } else {
                int c = vh.fixed;
                for (int k = 0; k < vh.len; ++k) {
                    int r = pos[id] + k;
                    if (0 <= r && r < 6) board[r][c] = id;
                }
            }
        }

        for (int id = 1; id <= n; ++id) {
            Vehicle &vh = veh[id];
            if (id == 1 && pos[1] >= 6) continue;

            int shift = 3 * (id - 1);
            ull mask = 7ULL << shift;

            if (vh.horiz) {
                int r = vh.fixed;
                int left = pos[id];
                int right = pos[id] + vh.len - 1;

                // Move left
                if (left > 0) {
                    int cell = left - 1;
                    if (cell >= 0 && board[r][cell] == 0) {
                        int newVal = left - 1;
                        ull newKey = (key & ~mask) | (ull(newVal) << shift);
                        if (!dist.count(newKey)) {
                            dist[newKey] = d + 1;
                            q.push(newKey);
                        }
                    }
                }

                // Move right
                if (id == 1) { // red car can exit to the right
                    if (pos[id] <= 6 - vh.len - 1) {
                        int frontCell = pos[id] + vh.len;
                        if (frontCell >= 0 && frontCell < 6 && board[r][frontCell] == 0) {
                            int newVal = pos[id] + 1;
                            ull newKey = (key & ~mask) | (ull(newVal) << shift);
                            if (!dist.count(newKey)) {
                                dist[newKey] = d + 1;
                                q.push(newKey);
                            }
                        }
                    } else if (pos[id] < 6) {
                        int newVal = pos[id] + 1; // move into / further out of exit
                        ull newKey = (key & ~mask) | (ull(newVal) << shift);
                        if (!dist.count(newKey)) {
                            dist[newKey] = d + 1;
                            q.push(newKey);
                        }
                    }
                } else {
                    if (right < 5) {
                        int cell = right + 1;
                        if (board[r][cell] == 0) {
                            int newVal = pos[id] + 1;
                            ull newKey = (key & ~mask) | (ull(newVal) << shift);
                            if (!dist.count(newKey)) {
                                dist[newKey] = d + 1;
                                q.push(newKey);
                            }
                        }
                    }
                }
            } else { // vertical
                int c = vh.fixed;
                int top = pos[id];
                int bottom = pos[id] + vh.len - 1;

                // Move up
                if (top > 0) {
                    int cellR = top - 1;
                    if (board[cellR][c] == 0) {
                        int newVal = top - 1;
                        ull newKey = (key & ~mask) | (ull(newVal) << shift);
                        if (!dist.count(newKey)) {
                            dist[newKey] = d + 1;
                            q.push(newKey);
                        }
                    }
                }
                // Move down
                if (bottom < 5) {
                    int cellR = bottom + 1;
                    if (board[cellR][c] == 0) {
                        int newVal = top + 1;
                        ull newKey = (key & ~mask) | (ull(newVal) << shift);
                        if (!dist.count(newKey)) {
                            dist[newKey] = d + 1;
                            q.push(newKey);
                        }
                    }
                }
            }
        }
    }

    if (answerSteps < 0) answerSteps = 0; // should not happen in valid puzzles

    // We choose not to modify the puzzle (0 preparation moves)
    cout << answerSteps << " " << 0 << "\n";

    return 0;
}