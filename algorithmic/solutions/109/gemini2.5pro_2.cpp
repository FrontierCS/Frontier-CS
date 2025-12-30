#include <iostream>
#include <vector>
#include <utility>
#include <algorithm>

// Global variables for board size and state
int N;
std::vector<std::vector<int>> board;

// Knight's move offsets. A fixed order provides a deterministic tie-breaker.
const int dr[] = {-2, -2, -1, -1, 1, 1, 2, 2};
const int dc[] = {-1, 1, -2, 2, -2, 2, -1, 1};

// Helper function to calculate the degree of a square.
// The degree is the number of unvisited squares it can move to from there.
int get_degree(int r, int c) {
    int degree = 0;
    for (int i = 0; i < 8; ++i) {
        int nr = r + dr[i];
        int nc = c + dc[i];
        if (nr >= 1 && nr <= N && nc >= 1 && nc <= N && board[nr][nc] == 0) {
            degree++;
        }
    }
    return degree;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int start_r, start_c;
    std::cin >> N >> start_r >> start_c;

    board.assign(N + 1, std::vector<int>(N + 1, 0));
    std::vector<std::pair<int, int>> path;

    int curr_r = start_r;
    int curr_c = start_c;

    // The main loop implements Warnsdorff's rule.
    // The loop runs up to N*N times, once for each square on the board.
    for (int k = 0; k < N * N; ++k) {
        board[curr_r][curr_c] = k + 1; // Mark as visited with the step number
        path.push_back({curr_r, curr_c});

        int min_degree = 9; // Maximum possible degree is 8, so 9 is a safe initial value.
        int next_r = -1, next_c = -1;

        // Find the next valid move that leads to a square with the minimum degree.
        for (int i = 0; i < 8; ++i) {
            int cand_r = curr_r + dr[i];
            int cand_c = curr_c + dc[i];

            // Check if the candidate square is on the board and unvisited.
            if (cand_r >= 1 && cand_r <= N && cand_c >= 1 && cand_c <= N && board[cand_r][cand_c] == 0) {
                int degree = get_degree(cand_r, cand_c);
                if (degree < min_degree) {
                    min_degree = degree;
                    next_r = cand_r;
                    next_c = cand_c;
                }
            }
        }

        if (next_r == -1) {
            // No more valid moves, the tour is stuck.
            // For N >= 5, a full tour is always possible, but a simple heuristic might fail.
            // The problem asks for the longest path found, so we just stop here.
            break;
        }

        // Move to the chosen square for the next iteration.
        curr_r = next_r;
        curr_c = next_c;
    }

    // Output the length of the path and the path itself.
    std::cout << path.size() << "\n";
    for (const auto& p : path) {
        std::cout << p.first << " " << p.second << "\n";
    }

    return 0;
}