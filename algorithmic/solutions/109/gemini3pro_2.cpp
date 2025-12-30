#include <iostream>
#include <vector>

using namespace std;

// Maximum board size as per constraints N <= 666
const int MAXN = 700;
bool visited[MAXN][MAXN];
int N;

// 8 possible moves for a knight
const int dr[] = {-2, -2, -1, -1, 1, 1, 2, 2};
const int dc[] = {-1, 1, -2, 2, -2, 2, -1, 1};

// Check if a position is within the board and unvisited
inline bool isValid(int r, int c) {
    return r >= 1 && r <= N && c >= 1 && c <= N && !visited[r][c];
}

// Warnsdorff's heuristic: Count the number of unvisited neighbors (degree)
// We want to move to a square with the minimum degree to avoid dead ends
int getDegree(int r, int c) {
    int count = 0;
    for (int i = 0; i < 8; ++i) {
        if (isValid(r + dr[i], c + dc[i])) {
            count++;
        }
    }
    return count;
}

struct Point {
    int r, c;
};

int main() {
    // Optimization for faster I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int startR, startC;
    if (!(cin >> N >> startR >> startC)) return 0;

    vector<Point> path;
    // Reserve memory to avoid reallocations
    path.reserve(N * N);

    int currR = startR;
    int currC = startC;

    // Mark starting position as visited
    visited[currR][currC] = true;
    path.push_back({currR, currC});

    // Try to extend the path. Maximum length is N*N.
    // We already have 1 point, so iterate at most N*N - 1 times.
    for (int step = 1; step < N * N; ++step) {
        int bestIdx = -1;
        int minDeg = 9; // Knight has max 8 moves, so 9 is infinity here

        // Iterate through all possible moves
        for (int k = 0; k < 8; ++k) {
            int nextR = currR + dr[k];
            int nextC = currC + dc[k];

            if (isValid(nextR, nextC)) {
                int deg = getDegree(nextR, nextC);
                // Apply Warnsdorff's rule: choose the neighbor with the minimum degree
                // Using strictly less (<) handles tie-breaking by picking the first one found in our fixed order
                if (deg < minDeg) {
                    minDeg = deg;
                    bestIdx = k;
                }
            }
        }

        if (bestIdx != -1) {
            // Make the move
            currR += dr[bestIdx];
            currC += dc[bestIdx];
            visited[currR][currC] = true;
            path.push_back({currR, currC});
        } else {
            // No valid moves left
            break;
        }
    }

    // Output the length of the path
    cout << path.size() << "\n";
    // Output the path coordinates
    for (const auto& p : path) {
        cout << p.r << " " << p.c << "\n";
    }

    return 0;
}