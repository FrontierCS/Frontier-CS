#include <iostream>
#include <vector>
#include <set>
#include <algorithm>

using namespace std;

// Global state for the solution
int rx, ry;
set<pair<int, int>> black_cells;
const int T = 3000;

// Function to make a move, read the response, and return true if the game is over.
bool query(int x, int y) {
    // Clamp coordinates to be within the allowed range [1, T]
    x = max(1, min(T, x));
    y = max(1, min(T, y));

    // If the chosen cell is already black (e.g., due to clamping), find an alternative.
    // This is a robust fallback, though unlikely to be needed frequently with this strategy.
    while (black_cells.count({x, y})) {
        x++;
        if (x > T) {
            x = 1;
            y++;
            if (y > T) {
                // This state should not be reached within the turn limit.
                y = 1;
            }
        }
    }

    cout << x << " " << y << endl;
    black_cells.insert({x, y});

    cin >> rx >> ry;
    return (rx <= 0 || ry <= 0);
}

int main() {
    // Disable synchronization with stdio for faster I/O in competitive programming.
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    // Read the initial robot position.
    cin >> rx >> ry;

    while (true) {
        // If the last read indicates the game ended, terminate.
        if (rx <= 0 || ry <= 0) {
            break;
        }

        // Define the priority targets: the three neighbors away from the origin.
        vector<pair<int, int>> priority_targets;
        priority_targets.push_back({rx + 1, ry + 1});
        priority_targets.push_back({rx, ry + 1});
        priority_targets.push_back({rx + 1, ry});

        bool move_made = false;
        // Try to mark one of the priority targets if it's not already black.
        for (auto const& [tx, ty] : priority_targets) {
            if (black_cells.find({tx, ty}) == black_cells.end()) {
                if (query(tx, ty)) return 0;
                move_made = true;
                break;
            }
        }

        if (move_made) {
            continue;
        }

        // If all priority targets are already black, the robot is partially trapped.
        // Block any other available neighbor to complete the trap.
        for (int dx = -1; dx <= 1; ++dx) {
            for (int dy = -1; dy <= 1; ++dy) {
                if (dx == 0 && dy == 0) continue;
                
                int nx = rx + dx;
                int ny = ry + dy;

                if (nx > 0 && ny > 0) {
                    if (black_cells.find({nx, ny}) == black_cells.end()) {
                        if (query(nx, ny)) return 0;
                        move_made = true;
                        break;
                    }
                }
            }
            if (move_made) break;
        }
    }

    return 0;
}