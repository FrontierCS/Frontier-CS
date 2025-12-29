#include <bits/stdc++.h>
using namespace std;

const int N = 54;           // side length of the square we fill
const int BIG = 10000;      // multiplier to prioritize higher layers

int main() {
    // Precompute all cells inside the square [1..N] x [1..N]
    vector<tuple<int, int, int>> cells;  // (layer, x, y)
    for (int x = 1; x <= N; ++x) {
        for (int y = 1; y <= N; ++y) {
            int layer = max(x, y);
            cells.emplace_back(layer, x, y);
        }
    }
    
    bool marked[N + 1][N + 1] = {false}; // 1‑based indexing
    
    int rx, ry;
    cin >> rx >> ry; // read initial robot position
    
    while (true) {
        // Choose the best cell to mark
        int best_x = -1, best_y = -1;
        int best_priority = -1e9;
        
        for (auto [layer, x, y] : cells) {
            if (marked[x][y]) continue;
            if (x == rx && y == ry) continue; // avoid marking the robot's cell if possible
            int dist = max(abs(x - rx), abs(y - ry));
            int priority = layer * BIG - dist;
            if (priority > best_priority) {
                best_priority = priority;
                best_x = x;
                best_y = y;
            }
        }
        
        // If all cells are already marked, we mark the robot's current cell
        if (best_x == -1) {
            best_x = rx;
            best_y = ry;
        }
        
        // Output our move and mark the cell
        cout << best_x << ' ' << best_y << endl;
        cout.flush();
        marked[best_x][best_y] = true;
        
        // Read the interactor's response
        cin >> rx >> ry;
        if (rx == 0 && ry == 0) {
            // robot exploded
            break;
        }
        // otherwise (rx, ry) is the new robot position
    }
    
    return 0;
}