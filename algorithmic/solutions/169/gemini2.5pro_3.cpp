#include <iostream>
#include <vector>
#include <string>
#include <algorithm>

int N;
std::vector<std::string> board;
std::vector<std::pair<char, int>> moves;

void shift_row_left(int r, int times) {
    if (times <= 0) return;
    for (int k = 0; k < times; ++k) {
        moves.push_back({'L', r});
    }
    std::string temp_row = board[r];
    for (int j = 0; j < N - times; ++j) {
        board[r][j] = temp_row[j + times];
    }
    for (int j = N - times; j < N; ++j) {
        board[r][j] = '.';
    }
}

void shift_row_right(int r, int times) {
    if (times <= 0) return;
    for (int k = 0; k < times; ++k) {
        moves.push_back({'R', r});
    }
    std::string temp_row = board[r];
    for (int j = times; j < N; ++j) {
        board[r][j] = temp_row[j - times];
    }
    for (int j = 0; j < times; ++j) {
        board[r][j] = '.';
    }
}

void shift_col_up(int c, int times) {
    if (times <= 0) return;
    for (int k = 0; k < times; ++k) {
        moves.push_back({'U', c});
    }
    std::vector<char> temp_col(N);
    for(int i = 0; i < N; ++i) temp_col[i] = board[i][c];
    
    for (int i = 0; i < N - times; ++i) {
        board[i][c] = temp_col[i + times];
    }
    for (int i = N - times; i < N; ++i) {
        board[i][c] = '.';
    }
}

void shift_col_down(int c, int times) {
    if (times <= 0) return;
    for (int k = 0; k < times; ++k) {
        moves.push_back({'D', c});
    }
    std::vector<char> temp_col(N);
    for(int i = 0; i < N; ++i) temp_col[i] = board[i][c];
    
    for (int i = times; i < N; ++i) {
        board[i][c] = temp_col[i - times];
    }
    for (int i = 0; i < times; ++i) {
        board[i][c] = '.';
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    
    std::cin >> N;
    board.resize(N);
    for (int i = 0; i < N; ++i) {
        std::cin >> board[i];
    }
    
    // Phase L
    for (int i = 0; i < N; ++i) {
        int min_o_c = N;
        for (int j = 0; j < N; ++j) {
            if (board[i][j] == 'o') {
                min_o_c = j;
                break;
            }
        }
        shift_row_left(i, min_o_c);
    }
    
    // Phase R
    for (int i = 0; i < N; ++i) {
        int max_o_c = -1;
        for (int j = N - 1; j >= 0; --j) {
            if (board[i][j] == 'o') {
                max_o_c = j;
                break;
            }
        }
        if (max_o_c != -1) {
            shift_row_right(i, (N - 1) - max_o_c);
        }
    }

    // Phase U
    for (int j = 0; j < N; ++j) {
        int min_o_r = N;
        for (int i = 0; i < N; ++i) {
            if (board[i][j] == 'o') {
                min_o_r = i;
                break;
            }
        }
        shift_col_up(j, min_o_r);
    }

    // Phase D
    for (int j = 0; j < N; ++j) {
        int max_o_r = -1;
        for (int i = N - 1; i >= 0; --i) {
            if (board[i][j] == 'o') {
                max_o_r = i;
                break;
            }
        }
        if (max_o_r != -1) {
            shift_col_down(j, (N - 1) - max_o_r);
        }
    }
    
    for(const auto& move : moves) {
        std::cout << move.first << " " << move.second << "\n";
    }

    return 0;
}