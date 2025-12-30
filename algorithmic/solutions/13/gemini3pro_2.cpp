#include <iostream>
#include <vector>
#include <set>
#include <algorithm>

using namespace std;

// Structure to represent grid coordinates
struct Point {
    int x, y;
    bool operator<(const Point& other) const {
        if (x != other.x) return x < other.x;
        return y < other.y;
    }
    bool operator==(const Point& other) const {
        return x == other.x && y == other.y;
    }
};

// Global state
set<Point> black_cells;
int cur_x, cur_y;

// Directions for 8 adjacent cells
int dx[] = {1, 1, 0, -1, -1, -1, 0, 1};
int dy[] = {0, 1, 1, 1, 0, -1, -1, -1};

// Check if a cell is valid (within first quadrant and not black)
bool is_valid(int x, int y) {
    if (x <= 0 || y <= 0) return false;
    if (black_cells.count({x, y})) return false;
    return true;
}

// Count number of valid moves available from (x, y)
int count_valid_neighbors(int x, int y) {
    int count = 0;
    for (int i = 0; i < 8; ++i) {
        int nx = x + dx[i];
        int ny = y + dy[i];
        if (is_valid(nx, ny)) {
            count++;
        }
    }
    return count;
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int sx, sy;
    if (!(cin >> sx >> sy)) return 0;
    cur_x = sx;
    cur_y = sy;

    int T = 3000;
    // Game loop
    for (int t = 1; t <= T; ++t) {
        // Identify all valid moves for the robot from its current position
        vector<Point> candidates;
        for (int i = 0; i < 8; ++i) {
            int nx = cur_x + dx[i];
            int ny = cur_y + dy[i];
            if (is_valid(nx, ny)) {
                candidates.push_back({nx, ny});
            }
        }

        Point best_move = {-1, -1};
        
        if (candidates.empty()) {
             // Robot is completely surrounded and has no valid moves.
             // We still need to print a move to satisfy the protocol.
             // We search for any valid white cell to mark.
             bool found = false;
             for (int r = 1; r <= T && !found; ++r) {
                 // Try simple positions close to axes
                 if (is_valid(r, 1)) { best_move = {r, 1}; found = true; }
                 else if (is_valid(1, r)) { best_move = {1, r}; found = true; }
                 else if (is_valid(r, r)) { best_move = {r, r}; found = true; }
             }
             if (!found) {
                 // Fallback (unlikely to be needed)
                 best_move = {1, 1}; 
             }
        } else {
            // Heuristic Strategy:
            // We want to block the robot's "best" escape route.
            // We evaluate each candidate move for the robot.
            // Score based on:
            // 1. Freedom (number of valid moves from that new position) - maximize to find open areas.
            // 2. Distance from origin (x + y) - maximize to find moves leading away.
            // By blocking the candidate with the MAX score, we force the robot to positions
            // with less freedom and closer to the origin/axes (walls).
            
            long long max_score = -1;
            
            for (const auto& p : candidates) {
                int freedom = count_valid_neighbors(p.x, p.y);
                // Weight freedom highly to prioritize cluttering open spaces.
                // Secondary weight on x+y to contain distance.
                long long score = (long long)freedom * 10000 + (p.x + p.y);
                
                if (score > max_score) {
                    max_score = score;
                    best_move = p;
                }
            }
        }

        // Execute our move
        cout << best_move.x << " " << best_move.y << endl;
        black_cells.insert(best_move);

        // Read robot's response
        int rx, ry;
        cin >> rx >> ry;
        if (rx == 0 && ry == 0) {
            // Robot exploded or trapped
            break;
        }
        cur_x = rx;
        cur_y = ry;
    }

    return 0;
}