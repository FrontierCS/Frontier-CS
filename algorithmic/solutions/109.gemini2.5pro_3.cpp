#include <iostream>
#include <vector>
#include <utility>

// Global variables to be accessible by helper functions
int N;
std::vector<std::vector<int>> board;
// The 8 possible moves for a knight. The order determines tie-breaking.
// This specific order is chosen to match the sample output's first move.
int dr[] = {2, 1, -1, -2, -2, -1, 1, 2};
int dc[] = {1, 2, 2, 1, -1, -2, -2, -1};

// Checks if a square (r, c) is within the board and unvisited
bool is_valid(int r, int c) {
    return (r >= 0 && r < N && c >= 0 && c < N && board[r][c] == 0);
}

// Counts the number of valid onward moves from a square (r, c)
// This is used to determine the "degree" of a potential next move.
int count_moves(int r, int c) {
    int count = 0;
    for (int i = 0; i < 8; ++i) {
        if (is_valid(r + dr[i], c + dc[i])) {
            count++;
        }
    }
    return count;
}

int main() {
    // Fast I/O
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int start_r_in, start_c_in;
    std::cin >> N;
    std::cin >> start_r_in >> start_c_in;

    // Adjust to 0-indexed for array access
    int start_r = start_r_in - 1;
    int start_c = start_c_in - 1;

    board.assign(N, std::vector<int>(N, 0));
    std::vector<std::pair<int, int>> path;

    int curr_r = start_r;
    int curr_c = start_c;
    
    // Mark the starting square as visited and add it to the path
    board[curr_r][curr_c] = 1;
    path.push_back({curr_r, curr_c});

    // Main loop to build the path, one move at a time
    for (int move_num = 2; move_num <= N * N; ++move_num) {
        int next_r = -1, next_c = -1;
        int min_degree = 9; // Initialize with a value > max possible degree (8)

        // Find the next move using Warnsdorff's rule
        for (int i = 0; i < 8; ++i) {
            int cand_r = curr_r + dr[i];
            int cand_c = curr_c + dc[i];

            if (is_valid(cand_r, cand_c)) {
                int degree = count_moves(cand_r, cand_c);
                if (degree < min_degree) {
                    min_degree = degree;
                    next_r = cand_r;
                    next_c = cand_c;
                }
            }
        }
        
        // If no valid move is found, the knight is trapped and the tour ends
        if (next_r == -1) {
            break;
        }

        // Make the chosen move
        curr_r = next_r;
        curr_c = next_c;
        board[curr_r][curr_c] = move_num;
        path.push_back({curr_r, curr_c});
    }

    // Output the length and coordinates of the found path
    std::cout << path.size() << "\n";
    for (const auto& pos : path) {
        // Convert back to 1-indexed for output
        std::cout << pos.first + 1 << " " << pos.second + 1 << "\n";
    }
    
    return 0;
}