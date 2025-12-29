#include <iostream>
#include <vector>
#include <utility>

// Global variables for convenience in a competitive programming setting.
// They are accessible by all functions without being passed as arguments.
int N;
std::vector<std::vector<bool>> visited;

// The 8 possible moves of a knight, arranged in a clockwise order.
int dx[] = {1, 2, 2, 1, -1, -2, -2, -1};
int dy[] = {2, 1, -1, -2, -2, -1, 1, 2};

// Checks if a square (r, c) is within the board boundaries and has not been visited.
// Marked 'inline' as a hint to the compiler for potential optimization.
inline bool is_valid(int r, int c) {
    return r >= 0 && r < N && c >= 0 && c < N && !visited[r][c];
}

// Counts the number of valid subsequent moves from a given square (r, c).
// This is the "degree" used in Warnsdorff's Rule.
int count_successors(int r, int c) {
    int count = 0;
    for (int i = 0; i < 8; ++i) {
        if (is_valid(r + dx[i], c + dy[i])) {
            count++;
        }
    }
    return count;
}

int main() {
    // Fast I/O for performance.
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int start_r, start_c;
    std::cin >> N >> start_r >> start_c;

    // Convert 1-indexed input coordinates to 0-indexed for array access.
    int curr_r = start_r - 1;
    int curr_c = start_c - 1;

    // Initialize the visited grid and the path vector.
    visited.assign(N, std::vector<bool>(N, false));
    std::vector<std::pair<int, int>> path;
    path.reserve(N * N); // Pre-allocate memory to avoid reallocations.

    // Start the tour.
    visited[curr_r][curr_c] = true;
    path.push_back({curr_r, curr_c});

    // The tour consists of N*N squares, so we need to make N*N - 1 moves.
    for (int i = 1; i < N * N; ++i) {
        int best_next_r = -1, best_next_c = -1;
        int min_degree = 9; // A square can have at most 8 moves.

        // Find the best next move according to Warnsdorff's Rule.
        for (int k = 0; k < 8; ++k) {
            int cand_r = curr_r + dx[k];
            int cand_c = curr_c + dy[k];

            if (is_valid(cand_r, cand_c)) {
                int degree = count_successors(cand_r, cand_c);
                
                // If this move has a smaller degree, it becomes our new best choice.
                // In case of a tie, the first one encountered is chosen.
                if (degree < min_degree) {
                    min_degree = degree;
                    best_next_r = cand_r;
                    best_next_c = cand_c;
                }
            }
        }

        // If no valid moves are found, the knight is trapped.
        if (best_next_r == -1) {
            break;
        }

        // Make the chosen move.
        curr_r = best_next_r;
        curr_c = best_next_c;
        visited[curr_r][curr_c] = true;
        path.push_back({curr_r, curr_c});
    }

    // Output the results.
    std::cout << path.size() << "\n";
    for (const auto& p : path) {
        // Convert 0-indexed coordinates back to 1-indexed for the output.
        std::cout << p.first + 1 << " " << p.second + 1 << "\n";
    }

    return 0;
}