#include <bits/stdc++.h>
using namespace std;

int main() {
    int N = 20;
    vector<string> board(N);
    for (int i = 0; i < N; i++) {
        cin >> board[i];
    }
    vector<pair<char, int>> ops;
    while (true) {
        int best_cost = INT_MAX;
        int br = -1, bc = -1;
        char bdir = ' ';
        int bshifts = 0;
        int bline = -1;
        bool bcol = false;
        for (int ii = 0; ii < N; ii++) {
            for (int jj = 0; jj < N; jj++) {
                if (board[ii][jj] != 'x') continue;
                bool uok = true;
                for (int k = 0; k < ii; k++) {
                    if (board[k][jj] == 'o') {
                        uok = false;
                        break;
                    }
                }
                int cu = uok ? 2 * (ii + 1) : INT_MAX / 2;
                bool dok = true;
                for (int k = ii + 1; k < N; k++) {
                    if (board[k][jj] == 'o') {
                        dok = false;
                        break;
                    }
                }
                int cd = dok ? 2 * (N - ii) : INT_MAX / 2;
                bool lok = true;
                for (int k = 0; k < jj; k++) {
                    if (board[ii][k] == 'o') {
                        lok = false;
                        break;
                    }
                }
                int cl = lok ? 2 * (jj + 1) : INT_MAX / 2;
                bool rok = true;
                for (int k = jj + 1; k < N; k++) {
                    if (board[ii][k] == 'o') {
                        rok = false;
                        break;
                    }
                }
                int cr = rok ? 2 * (N - jj) : INT_MAX / 2;
                int minc = min({cu, cd, cl, cr});
                if (minc < best_cost) {
                    best_cost = minc;
                    br = ii;
                    bc = jj;
                    if (cu == minc) {
                        bdir = 'U';
                        bshifts = ii + 1;
                        bline = jj;
                        bcol = true;
                    } else if (cd == minc) {
                        bdir = 'D';
                        bshifts = N - ii;
                        bline = jj;
                        bcol = true;
                    } else if (cl == minc) {
                        bdir = 'L';
                        bshifts = jj + 1;
                        bline = ii;
                        bcol = false;
                    } else {
                        bdir = 'R';
                        bshifts = N - jj;
                        bline = ii;
                        bcol = false;
                    }
                }
            }
        }
        if (br == -1) break;
        char push_d = bdir;
        char restore_d;
        if (bdir == 'U') restore_d = 'D';
        else if (bdir == 'D') restore_d = 'U';
        else if (bdir == 'L') restore_d = 'R';
        else restore_d = 'L';
        bool is_col = bcol;
        int line = bline;
        // push
        for (int s = 0; s < bshifts; s++) {
            ops.push_back({push_d, line});
            if (is_col) {
                if (push_d == 'U') {
                    // up shift
                    for (int row = 0; row < N - 1; row++) {
                        board[row][line] = board[row + 1][line];
                    }
                    board[N - 1][line] = '.';
                } else {
                    // down shift
                    for (int row = N - 1; row >= 1; row--) {
                        board[row][line] = board[row - 1][line];
                    }
                    board[0][line] = '.';
                }
            } else {
                if (push_d == 'L') {
                    // left shift
                    for (int col = 0; col < N - 1; col++) {
                        board[line][col] = board[line][col + 1];
                    }
                    board[line][N - 1] = '.';
                } else {
                    // right shift
                    for (int col = N - 1; col >= 1; col--) {
                        board[line][col] = board[line][col - 1];
                    }
                    board[line][0] = '.';
                }
            }
        }
        // restore
        for (int s = 0; s < bshifts; s++) {
            ops.push_back({restore_d, line});
            if (is_col) {
                if (restore_d == 'U') {
                    for (int row = 0; row < N - 1; row++) {
                        board[row][line] = board[row + 1][line];
                    }
                    board[N - 1][line] = '.';
                } else {
                    for (int row = N - 1; row >= 1; row--) {
                        board[row][line] = board[row - 1][line];
                    }
                    board[0][line] = '.';
                }
            } else {
                if (restore_d == 'L') {
                    for (int col = 0; col < N - 1; col++) {
                        board[line][col] = board[line][col + 1];
                    }
                    board[line][N - 1] = '.';
                } else {
                    for (int col = N - 1; col >= 1; col--) {
                        board[line][col] = board[line][col - 1];
                    }
                    board[line][0] = '.';
                }
            }
        }
    }
    for (auto [d, p] : ops) {
        cout << d << " " << p << "\n";
    }
    return 0;
}