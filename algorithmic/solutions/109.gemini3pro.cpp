#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

// Maximum board size as per constraints + padding
const int MAXN = 700;

int N;
// Visited array to keep track of the path
bool visited[MAXN][MAXN];

// Knight's moves: 8 possible L-shapes
int dr[] = {-2, -2, -1, -1, 1, 1, 2, 2};
int dc[] = {-1, 1, -2, 2, -2, 2, -1, 1};

// Check if position (r, c) is on board and not visited
inline bool isValid(int r, int c) {
    return r >= 1 && r <= N && c >= 1 && c <= N && !visited[r][c];
}

// Calculate the degree of a square (number of valid moves from it)
// This counts unvisited neighbors
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
    // Fast I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int startR, startC;
    if (!(cin >> N >> startR >> startC)) {
        return 0;
    }

    // Vector to store the sequence of moves
    vector<pair<int, int>> path;
    path.reserve(N * N);

    // Initial position
    int currR = startR;
    int currC = startC;

    // Mark start as visited
    visited[currR][currC] = true;
    path.push_back({currR, currC});

    // Try to visit as many squares as possible
    // We use Warnsdorff's rule: always move to the neighbor with the fewest onward moves
    while (true) {
        int bestR = -1;
        int bestC = -1;
        int minDeg = 9; // Initialize with value > max degree (8)

        // Iterate over all 8 possible moves
        for (int i = 0; i < 8; ++i) {
            int nextR = currR + dr[i];
            int nextC = currC + dc[i];

            if (isValid(nextR, nextC)) {
                int deg = getDegree(nextR, nextC);
                // Greedy selection: minimum degree
                if (deg < minDeg) {
                    minDeg = deg;
                    bestR = nextR;
                    bestC = nextC;
                }
            }
        }

        // If a valid move exists, take the best one
        if (bestR != -1) {
            visited[bestR][bestC] = true;
            currR = bestR;
            currC = bestC;
            path.push_back({currR, currC});
        } else {
            // No valid moves from current position
            break;
        }
    }

    // Output the total length of the path
    cout << path.size() << "\n";
    
    // Output the path coordinates
    for (const auto& p : path) {
        cout << p.first << " " << p.second << "\n";
    }

    return 0;
}