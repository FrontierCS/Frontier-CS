#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <map>

using namespace std;

// Coordinate structure
struct Point {
    int x, y;
    bool operator==(const Point& other) const {
        return x == other.x && y == other.y;
    }
    bool operator!=(const Point& other) const {
        return !(*this == other);
    }
};

struct Operation {
    int x1, y1, x2, y2;
};

// Global variables
int N = 30;
int grid[30][30];
Point pos[465]; // pos[v] stores coordinates of value v (0 to 464)
bool locked[30][30]; // Keeps track of balls that are in their final position
vector<Operation> ops;

// Function to perform swap and record operation
void swap_balls(Point p1, Point p2) {
    if (ops.size() >= 10000) return;
    int v1 = grid[p1.x][p1.y];
    int v2 = grid[p2.x][p2.y];
    
    // Swap in grid
    swap(grid[p1.x][p1.y], grid[p2.x][p2.y]);
    
    // Update positions
    pos[v1] = p2;
    pos[v2] = p1;
    
    ops.push_back({p1.x, p1.y, p2.x, p2.y});
}

// Distance in the triangular grid structure
// The possible moves are vectors (1,0), (0,1), (1,1) and their negatives.
// This corresponds to a hexagonal grid distance metric.
int dist(Point p1, Point p2) {
    int dx = p1.x - p2.x;
    int dy = p1.y - p2.y;
    return max({abs(dx), abs(dy), abs(dx - dy)});
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    // Read Input
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j <= i; ++j) {
            cin >> grid[i][j];
            pos[grid[i][j]] = {i, j};
            locked[i][j] = false;
        }
    }

    // Assign target values for each tier
    // We aim to place the smallest numbers in the top tiers.
    // Specifically, tier r will contain numbers corresponding to the r-th batch in sorted order.
    // This strictly satisfies the condition that parent < children (since parent is in tier r, children in r+1).
    vector<int> target_vals[30];
    int current_val = 0;
    for (int r = 0; r < N; ++r) {
        for (int c = 0; c <= r; ++c) {
            target_vals[r].push_back(current_val++);
        }
    }

    // Process tier by tier from top (0) to bottom (29)
    for (int r = 0; r < N; ++r) {
        // Values required for this tier
        vector<int> vals = target_vals[r];
        
        // Target slots in this tier
        vector<Point> slots;
        for (int c = 0; c <= r; ++c) slots.push_back({r, c});
        
        // Heuristic matching: Assign balls to slots to minimize lateral movement.
        // We sort the required balls by their current column index and assign to slots left-to-right.
        vector<pair<int, int>> val_infos; // {current_column, value}
        for (int v : vals) {
            val_infos.push_back({pos[v].y, v});
        }
        sort(val_infos.begin(), val_infos.end());
        
        // Move each ball to its assigned slot
        for (int i = 0; i < (int)vals.size(); ++i) {
            int v = val_infos[i].second;
            Point target = slots[i];
            
            // Greedy pathfinding to target
            while (pos[v] != target) {
                if (ops.size() >= 10000) break;
                
                Point curr = pos[v];
                Point best_next = curr;
                int min_d = 999999;
                
                // 6 Adjacent Directions
                int dx[] = {-1, -1, 0, 0, 1, 1};
                int dy[] = {-1, 0, -1, 1, 0, 1};
                
                for (int k = 0; k < 6; ++k) {
                    int nx = curr.x + dx[k];
                    int ny = curr.y + dy[k];
                    
                    // Check bounds
                    if (nx >= 0 && nx < N && ny >= 0 && ny <= nx) {
                        // Do not swap with balls that are already in their final position (locked)
                        if (locked[nx][ny]) continue; 
                        
                        Point next = {nx, ny};
                        int d = dist(next, target);
                        
                        if (d < min_d) {
                            min_d = d;
                            best_next = next;
                        }
                    }
                }
                
                if (best_next != curr) {
                    swap_balls(curr, best_next);
                } else {
                    // Should not be reachable unless trapped, but logically shouldn't happen
                    break;
                }
            }
            // Lock the slot as the correct ball is now in place
            locked[target.x][target.y] = true;
            if (ops.size() >= 10000) break;
        }
        if (ops.size() >= 10000) break;
    }

    // Output results
    cout << ops.size() << "\n";
    for (const auto& op : ops) {
        cout << op.x1 << " " << op.y1 << " " << op.x2 << " " << op.y2 << "\n";
    }

    return 0;
}