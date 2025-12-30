#include <iostream>
#include <vector>
#include <algorithm>
#include <climits>

using namespace std;

const int MAX_COORD = 3000;
const int INF = INT_MAX;

// Directions: 8 adjacent moves
const int dx[8] = {-1, -1, -1, 0, 0, 1, 1, 1};
const int dy[8] = {-1, 0, 1, -1, 1, -1, 0, 1};

vector<vector<bool>> black(MAX_COORD + 1, vector<bool>(MAX_COORD + 1, false));

// Check if a cell is black. Only cells within [1,3000] can be black.
bool isBlack(int x, int y) {
    if (x < 1 || x > MAX_COORD || y < 1 || y > MAX_COORD)
        return false;
    return black[x][y];
}

// Count white neighbors of (x,y), considering an additional temporary black cell (mx,my)
int countWhiteNeighbors(int x, int y, int mx, int my) {
    int cnt = 0;
    for (int d = 0; d < 8; ++d) {
        int nx = x + dx[d];
        int ny = y + dy[d];
        if (nx <= 0 || ny <= 0) continue; // robot cannot move there
        // Check if the cell is black (including temporary)
        if (nx == mx && ny == my) continue; // temporary black
        if (!isBlack(nx, ny))
            ++cnt;
    }
    return cnt;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int rx, ry;
    cin >> rx >> ry;

    for (int turn = 1; turn <= MAX_COORD; ++turn) {
        int best_x = -1, best_y = -1;
        int best_val = INF;

        // Evaluate each neighbor of the robot as a candidate to mark
        for (int d = 0; d < 8; ++d) {
            int mx = rx + dx[d];
            int my = ry + dy[d];
            // We can only mark within [1,3000]
            if (mx < 1 || mx > MAX_COORD || my < 1 || my > MAX_COORD) continue;
            if (isBlack(mx, my)) continue; // already black, skip

            // Simulate marking (mx, my) temporarily
            // Find white neighbors of the robot after this mark
            vector<pair<int, int>> white_neighbors;
            for (int nd = 0; nd < 8; ++nd) {
                int nx = rx + dx[nd];
                int ny = ry + dy[nd];
                if (nx <= 0 || ny <= 0) continue;
                if (nx == mx && ny == my) continue; // just marked black
                if (!isBlack(nx, ny))
                    white_neighbors.emplace_back(nx, ny);
            }

            // If no white neighbors, robot explodes -> perfect move
            if (white_neighbors.empty()) {
                best_x = mx;
                best_y = my;
                break;
            }

            // Otherwise, find the maximum number of white neighbors that any
            // possible next position would have.
            int max_cnt = 0;
            for (auto& w : white_neighbors) {
                int cnt = countWhiteNeighbors(w.first, w.second, mx, my);
                if (cnt > max_cnt) max_cnt = cnt;
            }

            if (max_cnt < best_val) {
                best_val = max_cnt;
                best_x = mx;
                best_y = my;
            }
        }

        // If no candidate found (should not happen), fallback to (1,1) or first white cell.
        if (best_x == -1) {
            // Try to find any white cell within bounds
            for (int x = 1; x <= MAX_COORD; ++x) {
                for (int y = 1; y <= MAX_COORD; ++y) {
                    if (!isBlack(x, y)) {
                        best_x = x;
                        best_y = y;
                        break;
                    }
                }
                if (best_x != -1) break;
            }
            if (best_x == -1) best_x = 1, best_y = 1; // should not happen
        }

        // Output the chosen cell
        cout << best_x << ' ' << best_y << endl;

        // Mark it black
        black[best_x][best_y] = true;

        // Read robot's new position
        int nrx, nry;
        cin >> nrx >> nry;
        if (nrx == 0 && nry == 0) {
            // Robot exploded
            return 0;
        }
        rx = nrx;
        ry = nry;
    }

    // If we reach here, we didn't catch the robot in 3000 turns.
    // According to the problem, this is incorrect.
    return 0;
}