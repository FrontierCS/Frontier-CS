#include <iostream>
#include <vector>
#include <cmath>
#include <utility>
#include <set>

using namespace std;

// Function to print a move and flush the output stream.
void make_move(int x, int y) {
    cout << x << " " << y << endl;
}

// Function to read the robot's new coordinates from the input stream.
pair<int, int> read_pos() {
    int x, y;
    cin >> x >> y;
    return {x, y};
}

// Signum function to determine the sign of an integer.
int sgn(int val) {
    if (val < 0) return -1;
    if (val > 0) return 1;
    return 0;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int sx, sy;
    cin >> sx >> sy;

    int rx = sx, ry = sy;
    set<pair<int, int>> black_cells;

    // Phase 1: Build a trap near a boundary (y=1) to minimize neighbors.
    // The trap cell is (tx, 1), which has 5 valid neighbors.
    int tx = 150;
    // If the robot starts far to the right, build the trap on the left.
    if (sx > 100) {
        tx = 50;
    }

    vector<pair<int, int>> trap_neighbors;
    trap_neighbors.push_back({tx - 1, 1});
    trap_neighbors.push_back({tx + 1, 1});
    trap_neighbors.push_back({tx - 1, 2});
    trap_neighbors.push_back({tx, 2});
    trap_neighbors.push_back({tx + 1, 2});

    for (const auto& p : trap_neighbors) {
        if (rx == 0 && ry == 0) return 0; // Check if robot exploded prematurely.
        make_move(p.first, p.second);
        black_cells.insert(p);
        tie(rx, ry) = read_pos();
    }
    
    // Phase 2: Herd the robot to the trap cell (tx, 1).
    while (rx != tx || ry != 1) {
        if (rx == 0 && ry == 0) return 0;

        // Heuristic: block the neighbor "opposite" to the target direction.
        int away_dx = sgn(rx - tx);
        int away_dy = sgn(ry - 1);
        
        pair<int, int> block_pos;

        // If robot is on the target column, prioritize vertical herding.
        if (rx == tx && away_dy != 0) {
            block_pos = {rx, ry + away_dy};
        } 
        // Otherwise, block the corner diagonally opposite to the target.
        else {
            block_pos = {rx + away_dx, ry + away_dy};
        }

        // Ensure the blocked cell is within the first quadrant.
        if (block_pos.first <= 0) block_pos.first = 1;
        if (block_pos.second <= 0) block_pos.second = 1;

        make_move(block_pos.first, block_pos.second);
        black_cells.insert(block_pos);
        tie(rx, ry) = read_pos();
    }

    // Phase 3: Robot is at the trap cell (tx, 1).
    // All its valid neighbors are black. The next move is fatal.
    // The interactor will print 0 0. We make a final move on the now-irrelevant trap cell
    // to prompt the interactor's final response if it hasn't terminated yet.
     if (rx != 0 || ry != 0) {
       make_move(tx, 1);
     }

    return 0;
}