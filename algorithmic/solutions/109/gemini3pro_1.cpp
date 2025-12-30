#include <iostream>
#include <vector>

using namespace std;

// Maximum N is 666, so 700 is a safe buffer
const int MAXN = 700;
bool visited[MAXN][MAXN];
int N;
int start_r, start_c;

// 8 possible moves for a knight
const int dr[] = {-2, -2, -1, -1, 1, 1, 2, 2};
const int dc[] = {-1, 1, -2, 2, -2, 2, -1, 1};

// Check if a move is within board boundaries and not visited
bool isValid(int r, int c) {
    return r >= 1 && r <= N && c >= 1 && c <= N && !visited[r][c];
}

// Calculate the number of valid onward moves (degree) to unvisited squares
int getDegree(int r, int c) {
    int deg = 0;
    for (int i = 0; i < 8; ++i) {
        if (isValid(r + dr[i], c + dc[i])) {
            deg++;
        }
    }
    return deg;
}

int main() {
    // Optimize I/O operations for speed
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N >> start_r >> start_c)) return 0;

    vector<pair<int, int>> path;
    path.reserve(N * N);

    int curr_r = start_r;
    int curr_c = start_c;

    // Mark start position
    visited[curr_r][curr_c] = true;
    path.push_back({curr_r, curr_c});

    // We can visit at most N*N - 1 more squares
    int target_steps = N * N - 1;
    
    // Constant for distance calculation heuristic
    // Center of board is roughly (N+1)/2. 
    // We use scaled coordinates (2*r) to keep calculations in integers.
    // Center offset becomes N+1.
    int center_offset = N + 1;

    for (int step = 0; step < target_steps; ++step) {
        int best_r = -1, best_c = -1;
        int min_deg = 9; // Max possible degree is 8
        long long max_dist = -1;

        // Iterate through all 8 possible moves
        for (int i = 0; i < 8; ++i) {
            int nr = curr_r + dr[i];
            int nc = curr_c + dc[i];

            if (isValid(nr, nc)) {
                // Warnsdorff's Rule: Choose neighbor with fewest onward moves
                int deg = getDegree(nr, nc);
                
                // Tie-breaking Heuristic: Choose neighbor furthest from center
                // Distance squared proportional to (2*nr - (N+1))^2 + (2*nc - (N+1))^2
                long long dist = 1LL * (2 * nr - center_offset) * (2 * nr - center_offset) + 
                                 1LL * (2 * nc - center_offset) * (2 * nc - center_offset);

                if (deg < min_deg) {
                    min_deg = deg;
                    best_r = nr;
                    best_c = nc;
                    max_dist = dist;
                } else if (deg == min_deg) {
                    // Tie-breaker
                    if (dist > max_dist) {
                        max_dist = dist;
                        best_r = nr;
                        best_c = nc;
                    }
                }
            }
        }

        if (best_r != -1) {
            visited[best_r][best_c] = true;
            curr_r = best_r;
            curr_c = best_c;
            path.push_back({curr_r, curr_c});
        } else {
            // No valid moves left
            break;
        }
    }

    // Output results
    cout << path.size() << "\n";
    for (const auto& p : path) {
        cout << p.first << " " << p.second << "\n";
    }

    return 0;
}