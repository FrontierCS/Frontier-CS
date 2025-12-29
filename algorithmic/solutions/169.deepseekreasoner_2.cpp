#include <iostream>
#include <vector>
#include <string>
#include <utility>
using namespace std;

struct Oni {
    int r, c;
    int dir; // 0: up, 1: down, 2: left, 3: right
    bool removed;
};

int main() {
    int N = 20;
    vector<string> board(N);
    for (int i = 0; i < N; ++i) {
        cin >> board[i];
    }

    vector<Oni> onis;
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (board[i][j] == 'x') {
                onis.push_back({i, j, -1, false});
            }
        }
    }

    // Determine a safe direction for each Oni
    for (auto& oni : onis) {
        bool up_safe = true;
        for (int r = 0; r < oni.r; ++r) {
            if (board[r][oni.c] == 'o') {
                up_safe = false;
                break;
            }
        }
        bool down_safe = true;
        for (int r = oni.r + 1; r < N; ++r) {
            if (board[r][oni.c] == 'o') {
                down_safe = false;
                break;
            }
        }
        bool left_safe = true;
        for (int c = 0; c < oni.c; ++c) {
            if (board[oni.r][c] == 'o') {
                left_safe = false;
                break;
            }
        }
        bool right_safe = true;
        for (int c = oni.c + 1; c < N; ++c) {
            if (board[oni.r][c] == 'o') {
                right_safe = false;
                break;
            }
        }

        if (up_safe) oni.dir = 0;
        else if (down_safe) oni.dir = 1;
        else if (left_safe) oni.dir = 2;
        else if (right_safe) oni.dir = 3;
        // According to the guarantee, at least one direction is safe.
    }

    vector<pair<char, int>> operations;

    // Process columns: first up, then down
    for (int j = 0; j < N; ++j) {
        // Up sequences
        vector<int> up_indices;
        for (int idx = 0; idx < (int)onis.size(); ++idx) {
            if (!onis[idx].removed && onis[idx].c == j && onis[idx].dir == 0) {
                up_indices.push_back(idx);
            }
        }
        if (!up_indices.empty()) {
            int max_up = 0;
            for (int idx : up_indices) {
                if (onis[idx].r > max_up) max_up = onis[idx].r;
            }
            int shifts = max_up + 1;
            for (int s = 0; s < shifts; ++s) operations.push_back({'U', j});
            for (int s = 0; s < shifts; ++s) operations.push_back({'D', j});
            // Mark all Oni in this column with row <= max_up as removed
            for (int idx = 0; idx < (int)onis.size(); ++idx) {
                if (!onis[idx].removed && onis[idx].c == j && onis[idx].r <= max_up) {
                    onis[idx].removed = true;
                }
            }
        }

        // Down sequences
        vector<int> down_indices;
        for (int idx = 0; idx < (int)onis.size(); ++idx) {
            if (!onis[idx].removed && onis[idx].c == j && onis[idx].dir == 1) {
                down_indices.push_back(idx);
            }
        }
        if (!down_indices.empty()) {
            int min_down = N - 1;
            for (int idx : down_indices) {
                if (onis[idx].r < min_down) min_down = onis[idx].r;
            }
            int shifts = N - min_down;
            for (int s = 0; s < shifts; ++s) operations.push_back({'D', j});
            for (int s = 0; s < shifts; ++s) operations.push_back({'U', j});
            // Mark all Oni in this column with row >= min_down as removed
            for (int idx = 0; idx < (int)onis.size(); ++idx) {
                if (!onis[idx].removed && onis[idx].c == j && onis[idx].r >= min_down) {
                    onis[idx].removed = true;
                }
            }
        }
    }

    // Process rows: first left, then right
    for (int i = 0; i < N; ++i) {
        // Left sequences
        vector<int> left_indices;
        for (int idx = 0; idx < (int)onis.size(); ++idx) {
            if (!onis[idx].removed && onis[idx].r == i && onis[idx].dir == 2) {
                left_indices.push_back(idx);
            }
        }
        if (!left_indices.empty()) {
            int max_left = 0;
            for (int idx : left_indices) {
                if (onis[idx].c > max_left) max_left = onis[idx].c;
            }
            int shifts = max_left + 1;
            for (int s = 0; s < shifts; ++s) operations.push_back({'L', i});
            for (int s = 0; s < shifts; ++s) operations.push_back({'R', i});
            // Mark all Oni in this row with column <= max_left as removed
            for (int idx = 0; idx < (int)onis.size(); ++idx) {
                if (!onis[idx].removed && onis[idx].r == i && onis[idx].c <= max_left) {
                    onis[idx].removed = true;
                }
            }
        }

        // Right sequences
        vector<int> right_indices;
        for (int idx = 0; idx < (int)onis.size(); ++idx) {
            if (!onis[idx].removed && onis[idx].r == i && onis[idx].dir == 3) {
                right_indices.push_back(idx);
            }
        }
        if (!right_indices.empty()) {
            int min_right = N - 1;
            for (int idx : right_indices) {
                if (onis[idx].c < min_right) min_right = onis[idx].c;
            }
            int shifts = N - min_right;
            for (int s = 0; s < shifts; ++s) operations.push_back({'R', i});
            for (int s = 0; s < shifts; ++s) operations.push_back({'L', i});
            // Mark all Oni in this row with column >= min_right as removed
            for (int idx = 0; idx < (int)onis.size(); ++idx) {
                if (!onis[idx].removed && onis[idx].r == i && onis[idx].c >= min_right) {
                    onis[idx].removed = true;
                }
            }
        }
    }

    // Output the sequence of operations
    for (auto& op : operations) {
        cout << op.first << " " << op.second << "\n";
    }

    return 0;
}