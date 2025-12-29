#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    if (!(cin >> N >> M)) return 0;
    vector<string> s(M);
    for (int i = 0; i < M; ++i) cin >> s[i];

    // Indices of strings, sorted by descending length
    vector<int> order(M);
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [&](int a, int b) {
        if ((int)s[a].size() != (int)s[b].size())
            return s[a].size() > s[b].size();
        return a < b;
    });

    // Board initialization with '.'
    vector<string> board(N, string(N, '.'));

    // Greedy placement
    for (int idx : order) {
        const string &str = s[idx];
        int k = (int)str.size();

        int bestNew = -1;
        int bestI = -1, bestJ = -1, bestDir = -1; // 0: horizontal, 1: vertical

        for (int i = 0; i < N; ++i) {
            for (int j = 0; j < N; ++j) {
                // Horizontal
                {
                    int newCells = 0;
                    bool conflict = false;
                    for (int p = 0; p < k; ++p) {
                        int ii = i;
                        int jj = (j + p) % N;
                        char c = board[ii][jj];
                        if (c == '.') {
                            ++newCells;
                        } else if (c != str[p]) {
                            conflict = true;
                            break;
                        }
                    }
                    if (!conflict) {
                        if (bestNew == -1 || newCells < bestNew) {
                            bestNew = newCells;
                            bestI = i;
                            bestJ = j;
                            bestDir = 0;
                        }
                    }
                }
                // Vertical
                {
                    int newCells = 0;
                    bool conflict = false;
                    for (int p = 0; p < k; ++p) {
                        int ii = (i + p) % N;
                        int jj = j;
                        char c = board[ii][jj];
                        if (c == '.') {
                            ++newCells;
                        } else if (c != str[p]) {
                            conflict = true;
                            break;
                        }
                    }
                    if (!conflict) {
                        if (bestNew == -1 || newCells < bestNew) {
                            bestNew = newCells;
                            bestI = i;
                            bestJ = j;
                            bestDir = 1;
                        }
                    }
                }
            }
        }

        if (bestNew != -1) {
            if (bestDir == 0) {
                // Horizontal placement
                for (int p = 0; p < k; ++p) {
                    int ii = bestI;
                    int jj = (bestJ + p) % N;
                    board[ii][jj] = str[p];
                }
            } else {
                // Vertical placement
                for (int p = 0; p < k; ++p) {
                    int ii = (bestI + p) % N;
                    int jj = bestJ;
                    board[ii][jj] = str[p];
                }
            }
        }
    }

    // Fill remaining '.' with random letters A-H
    mt19937 rng(71236721);
    uniform_int_distribution<int> dist(0, 7);
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (board[i][j] == '.') {
                board[i][j] = char('A' + dist(rng));
            }
        }
    }

    // Output
    for (int i = 0; i < N; ++i) {
        cout << board[i] << '\n';
    }

    return 0;
}