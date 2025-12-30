#include <iostream>
#include <vector>
#include <utility>
#include <algorithm>

// Global variables for board size and state
int N;
// Using 1-based indexing for convenience to match problem statement.
// Global arrays are zero-initialized, which works perfectly for 'unvisited'.
int board[667][667]; 

// Knight's move offsets (8 directions, ordered clockwise)
const int dr[] = {-2, -1, 1, 2, 2, 1, -1, -2};
const int dc[] = {1, 2, 2, 1, -1, -2, -2, -1};

// Check if a square (r, c) is on the board and unvisited.
// Inlining can give a minor performance boost.
inline bool isValid(int r, int c) {
    return r >= 1 && r <= N && c >= 1 && c <= N && board[r][c] == 0;
}

// Calculate the number of available moves from a square (Warnsdorff's rule).
// This is the 'degree' of the vertex in the graph of unvisited squares.
int getDegree(int r, int c) {
    int count = 0;
    for (int i = 0; i < 8; ++i) {
        if (isValid(r + dr[i], c + dc[i])) {
            count++;
        }
    }
    return count;
}

int main() {
    // Use fast I/O
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int start_r, start_c;
    std::cin >> N >> start_r >> start_c;

    // `path` will store the sequence of visited squares.
    std::vector<std::pair<int, int>> path;
    
    // Set the starting position.
    int r = start_r;
    int c = start_c;

    // Mark the starting square as visited (step 1).
    board[r][c] = 1;
    path.push_back({r, c});

    // Generate the rest of the path, up to N*N-1 more moves.
    for (int move_count = 2; move_count <= N * N; ++move_count) {
        int next_r = -1;
        int next_c = -1;
        // Max possible degree is 8, so 9 is a safe initial value for min_degree.
        int min_degree = 9;

        // Apply Warnsdorff's rule: find the next move that has the minimum number of onward moves.
        for (int i = 0; i < 8; ++i) {
            int nr = r + dr[i];
            int nc = c + dc[i];

            if (isValid(nr, nc)) {
                int degree = getDegree(nr, nc);
                if (degree < min_degree) {
                    min_degree = degree;
                    next_r = nr;
                    next_c = nc;
                }
            }
        }

        // If next_r is -1, it means we are stuck and cannot make any more moves.
        if (next_r == -1) {
            break; 
        }

        // Make the chosen move.
        r = next_r;
        c = next_c;
        board[r][c] = move_count;
        path.push_back({r, c});
    }

    // Output the length of the path found.
    std::cout << path.size() << "\n";
    // Output the coordinates of each square in the path.
    for (const auto& p : path) {
        std::cout << p.first << " " << p.second << "\n";
    }

    return 0;
}