#include <iostream>
#include <vector>
#include <set>
#include <algorithm>
#include <cmath>

using namespace std;

using Point = pair<int, int>;
set<Point> black_cells;

// Function to mark a cell, ensuring coordinates are valid.
void mark(int x, int y) {
    if (x <= 0 || y <= 0 || x > 3000 || y > 3000) {
        // Fallback for invalid coordinates, should not happen with this logic.
        // A move must be made.
        if (black_cells.find({1, 1}) == black_cells.end()) {
             cout << 1 << " " << 1 << endl;
             cout.flush();
             black_cells.insert({1, 1});
        } else {
             cout << 1 << " " << 2 << endl;
             cout.flush();
             black_cells.insert({1, 2});
        }
        return;
    }
    cout << x << " " << y << endl;
    cout.flush();
    black_cells.insert({x, y});
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int sx, sy;
    cin >> sx >> sy;

    int rx = sx;
    int ry = sy;
    
    // Define a trap centered at (200, 200)
    int trap_center_x = 200, trap_center_y = 200;
    
    vector<Point> trap_cells_static;
    // U-shaped trap around (200,200), open at y=203.
    for(int y = trap_center_y; y <= trap_center_y + 2; ++y) {
        trap_cells_static.push_back({trap_center_x - 1, y});
        trap_cells_static.push_back({trap_center_x + 1, y});
    }
    trap_cells_static.push_back({trap_center_x, trap_center_y});

    for (int turn = 0; turn < 3000; ++turn) {
        Point to_mark = {-1, -1};

        // Priority 1: Build the static trap.
        for (const auto& p : trap_cells_static) {
            if (black_cells.find(p) == black_cells.end()) {
                to_mark = p;
                break;
            }
        }

        // Priority 2: If trap is built, or we need to herd, place adaptive walls.
        if (to_mark.first == -1) {
            if (ry > trap_center_y + 2 || (ry == trap_center_y + 2 && abs(rx - trap_center_x) > 1)) {
                // Above trap: build a roof to push down
                if (black_cells.find({rx, ry + 1}) == black_cells.end()) to_mark = {rx, ry + 1};
                else if (black_cells.find({rx-1, ry + 1}) == black_cells.end()) to_mark = {rx-1, ry+1};
                else if (black_cells.find({rx+1, ry + 1}) == black_cells.end()) to_mark = {rx+1, ry+1};
            } else if (rx > trap_center_x + 1) {
                // Right of trap: build a wall to push left
                if (black_cells.find({rx - 1, ry}) == black_cells.end()) to_mark = {rx - 1, ry};
                else if (black_cells.find({rx-1, ry+1}) == black_cells.end()) to_mark = {rx-1, ry+1};
                else if (black_cells.find({rx-1, ry-1}) == black_cells.end()) to_mark = {rx-1, ry-1};
            } else if (rx < trap_center_x - 1) {
                // Left of trap: build a wall to push right
                if (black_cells.find({rx + 1, ry}) == black_cells.end()) to_mark = {rx + 1, ry};
                else if (black_cells.find({rx+1, ry+1}) == black_cells.end()) to_mark = {rx+1, ry+1};
                else if (black_cells.find({rx+1, ry-1}) == black_cells.end()) to_mark = {rx+1, ry-1};
            } else { // Inside the trap structure
                if (black_cells.find({trap_center_x, trap_center_y + 1}) == black_cells.end()) {
                    to_mark = {trap_center_x, trap_center_y + 1};
                } else if (black_cells.find({trap_center_x, trap_center_y + 2}) == black_cells.end()){
                    to_mark = {trap_center_x, trap_center_y + 2};
                }
            }
        }
        
        // If no specific move decided, fill any remaining gaps or expand walls.
        if (to_mark.first == -1) {
            to_mark = {rx, ry-1}; // Default push down
        }

        mark(to_mark.first, to_mark.second);

        cin >> rx >> ry;
        if (rx == 0 && ry == 0) {
            return 0;
        }
    }

    return 0;
}