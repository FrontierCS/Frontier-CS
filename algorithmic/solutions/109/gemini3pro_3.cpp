#include <iostream>
#include <vector>

using namespace std;

const int MAXN = 700;
int N;
bool visited[MAXN][MAXN];
// 8 possible moves for a knight
int dr[] = {-2, -1, 1, 2, 2, 1, -1, -2};
int dc[] = {1, 2, 2, 1, -1, -2, -2, -1};

// Check if position is inside the board and not yet visited
bool isValid(int r, int c) {
    return r >= 1 && r <= N && c >= 1 && c <= N && !visited[r][c];
}

// Calculate the number of valid onward moves from (r, c)
// This implements Warnsdorff's heuristic
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
    // Optimize I/O operations for speed
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int start_r, start_c;
    if (!(cin >> N >> start_r >> start_c)) return 0;

    vector<pair<int, int>> path;
    path.reserve(N * N);

    int curr_r = start_r;
    int curr_c = start_c;

    // Mark starting position
    visited[curr_r][curr_c] = true;
    path.push_back({curr_r, curr_c});

    int max_steps = N * N - 1;
    for (int step = 0; step < max_steps; ++step) {
        int best_r = -1, best_c = -1;
        int min_deg = 9; // Degrees are between 0 and 8

        // Greedily choose the neighbor with the minimum degree (Warnsdorff's Rule)
        for (int i = 0; i < 8; ++i) {
            int nr = curr_r + dr[i];
            int nc = curr_c + dc[i];

            if (isValid(nr, nc)) {
                int deg = getDegree(nr, nc);
                if (deg < min_deg) {
                    min_deg = deg;
                    best_r = nr;
                    best_c = nc;
                }
            }
        }

        if (best_r != -1) {
            visited[best_r][best_c] = true;
            curr_r = best_r;
            curr_c = best_c;
            path.push_back({curr_r, curr_c});
        } else {
            // No further valid moves possible
            break;
        }
    }

    // Output the length of the path
    cout << path.size() << "\n";
    // Output the path coordinates
    for (const auto& p : path) {
        cout << p.first << " " << p.second << "\n";
    }

    return 0;
}