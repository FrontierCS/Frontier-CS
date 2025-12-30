#include <iostream>
#include <vector>
#include <set>
#include <algorithm>

// Global variables for robot's position
int rx, ry;
// Keep track of cells we've marked black
std::set<std::pair<int, int>> black_cells;

// Function to send a query and read the response.
// Returns true if the game ends, false otherwise.
bool query(int x, int y) {
    // A simple safeguard to ensure we always make a valid move within bounds.
    if (x <= 0 || y <= 0 || x > 3000 || y > 3000) {
        // This case should ideally not be reached with the current strategy.
        // If it does, we find an arbitrary valid unpainted cell to mark.
        x = 1; y = 1;
        while(black_cells.count({x,y})) {
            x++;
            if (x > 3000) { x = 1; y++; }
        }
    }

    // Output our move and flush the stream.
    std::cout << x << " " << y << std::endl;
    
    // Add the cell to our set of black cells.
    black_cells.insert({x, y});

    // Read the robot's new position.
    std::cin >> rx >> ry;
    
    // Check for game termination signals.
    if (rx == 0 && ry == 0) return true; // Robot exploded.
    if (rx == -1 && ry == -1) return true; // Error or other termination.
    
    return false; // Game continues.
}

// The main solver function.
void solve() {
    // Read the initial robot position.
    std::cin >> rx >> ry;

    // Phase 1: Force the robot's y-coordinate downwards.
    // We repeatedly mark the three cells directly above the robot's current position.
    // This creates a "roof" that prevents the robot from increasing its y-coordinate.
    // An adversarial robot will be forced to move sideways or down. Over time,
    // this will strongly push it towards the y=1 boundary.
    for (int i = 0; i < 150; ++i) {
        if (query(rx - 1, ry + 1)) return;
        if (query(rx, ry + 1)) return;
        if (query(rx + 1, ry + 1)) return;
    }

    // Phase 2: Force the robot's x-coordinate to the left.
    // Similar to Phase 1, we build a "wall" to the right of the robot
    // by marking the three adjacent cells in the +x direction.
    // This pushes the robot towards the x=1 boundary.
    for (int i = 0; i < 150; ++i) {
        if (query(rx + 1, ry - 1)) return;
        if (query(rx + 1, ry)) return;
        if (query(rx + 1, ry + 1)) return;
    }

    // After these two phases, the robot is highly likely to be in the
    // bottom-left corner of the grid, with small x and y coordinates.
    // Now we can trap it by surrounding its current position.
    
    // Phase 3: Trap the robot.
    // We systematically mark all 8 neighbors of the robot's current position.
    // Since the robot can only move one cell at a time, this chase will
    // eventually corner it.
    while (true) {
        if (query(rx - 1, ry + 1)) return;
        if (query(rx,     ry + 1)) return;
        if (query(rx + 1, ry + 1)) return;
        if (query(rx - 1, ry    )) return;
        if (query(rx + 1, ry    )) return;
        if (query(rx - 1, ry - 1)) return;
        if (query(rx,     ry - 1)) return;
        if (query(rx + 1, ry - 1)) return;
    }
}

int main() {
    // Fast I/O
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    solve();
    return 0;
}