#include <iostream>
#include <vector>

using namespace std;

// Direction offsets for a knight
const int dr[] = {-2, -2, -1, -1, 1, 1, 2, 2};
const int dc[] = {-1, 1, -2, 2, -2, 2, -1, 1};

int N;
int startR, startC;
bool visited[700][700];

struct Point {
    int r, c;
};

// Function to check if a cell is within grid boundaries and not visited
bool isValid(int r, int c) {
    return r >= 1 && r <= N && c >= 1 && c <= N && !visited[r][c];
}

// Function to calculate the number of valid moves from a given cell
// (Warnsdorff's heuristic uses this degree)
int getDegree(int r, int c) {
    int count = 0;
    for (int i = 0; i < 8; ++i) {
        int nr = r + dr[i];
        int nc = c + dc[i];
        if (isValid(nr, nc)) {
            count++;
        }
    }
    return count;
}

int main() {
    // Optimize standard I/O streams for speed
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (cin >> N >> startR >> startC) {
        // Path storage
        vector<Point> path;
        path.reserve(N * N);

        int curR = startR;
        int curC = startC;

        // Mark the starting cell as visited
        visited[curR][curC] = true;
        path.push_back({curR, curC});

        // The maximum path length is N*N. We already have 1, so we try N*N - 1 steps.
        int totalSteps = N * N - 1;
        for (int step = 0; step < totalSteps; ++step) {
            int bestIdx = -1;
            int minDegree = 9; // Initialize with a value larger than max possible degree (8)

            // Iterate over all possible moves
            for (int i = 0; i < 8; ++i) {
                int nr = curR + dr[i];
                int nc = curC + dc[i];

                if (isValid(nr, nc)) {
                    int deg = getDegree(nr, nc);
                    // Select the move with the minimum degree (Warnsdorff's rule)
                    if (deg < minDegree) {
                        minDegree = deg;
                        bestIdx = i;
                    }
                }
            }

            if (bestIdx != -1) {
                // Perform the best move
                int nextR = curR + dr[bestIdx];
                int nextC = curC + dc[bestIdx];
                visited[nextR][nextC] = true;
                path.push_back({nextR, nextC});
                curR = nextR;
                curC = nextC;
            } else {
                // No valid moves left
                break;
            }
        }

        // Output the path length
        cout << path.size() << "\n";
        // Output the path coordinates
        for (const auto& p : path) {
            cout << p.r << " " << p.c << "\n";
        }
    }

    return 0;
}