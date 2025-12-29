#include <iostream>
#include <vector>
#include <utility>

// Global variables for board size and state
int N;
std::vector<std::vector<int>> board;

// Knight move offsets: 8 possible L-shaped moves
const int dx[] = {1, 1, 2, 2, -1, -1, -2, -2};
const int dy[] = {2, -2, 1, -1, 2, -2, 1, -1};

// Checks if a square (r, c) is on the board and has not been visited yet.
// Coordinates are 0-indexed.
inline bool is_valid(int r, int c) {
    return r >= 0 && r < N && c >= 0 && c < N && board[r][c] == 0;
}

// Calculates the "degree" of a square (r, c), which is the number of
// unvisited squares a knight can move to from there.
// Coordinates are 0-indexed.
int get_degree(int r, int c) {
    int count = 0;
    for (int i = 0; i < 8; ++i) {
        int next_r = r + dx[i];
        int next_c = c + dy[i];
        if (is_valid(next_r, next_c)) {
            count++;
        }
    }
    return count;
}

int main() {
    // Fast I/O for performance
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int start_r, start_c;
    std::cin >> N >> start_r >> start_c;

    // Convert 1-indexed input to 0-indexed for internal processing
    start_r--;
    start_c--;

    board.assign(N, std::vector<int>(N, 0));
    std::vector<std::pair<int, int>> path;

    int curr_r = start_r;
    int curr_c = start_c;
    int move_count = 1;

    board[curr_r][curr_c] = move_count;
    path.push_back({curr_r + 1, curr_c + 1});

    // Main loop to find the path
    // It will attempt to visit all N*N squares.
    while (move_count < N * N) {
        int min_degree = 9; // A value higher than the maximum possible degree (8)
        int next_r = -1, next_c = -1;

        // Apply Warnsdorff's rule: find the next move with the minimum degree.
        for (int i = 0; i < 8; ++i) {
            int cand_r = curr_r + dx[i];
            int cand_c = curr_c + dy[i];

            if (is_valid(cand_r, cand_c)) {
                int degree = get_degree(cand_r, cand_c);
                if (degree < min_degree) {
                    min_degree = degree;
                    next_r = cand_r;
                    next_c = cand_c;
                }
            }
        }
        
        // If no valid move is found, the knight is stuck. End the path.
        if (next_r == -1) {
            break;
        }

        // Make the chosen move
        curr_r = next_r;
        curr_c = next_c;
        move_count++;
        board[curr_r][curr_c] = move_count;
        path.push_back({curr_r + 1, curr_c + 1});
    }

    // Output the path length and the path itself
    std::cout << path.size() << "\n";
    for (const auto& p : path) {
        std::cout << p.first << " " << p.second << "\n";
    }

    return 0;
}