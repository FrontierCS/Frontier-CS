#include <iostream>
#include <vector>
#include <algorithm>
#include <queue>

using namespace std;

// Structure to represent coordinates in the pyramid
struct Point {
    int x, y;
    bool operator==(const Point& other) const {
        return x == other.x && y == other.y;
    }
    bool operator!=(const Point& other) const {
        return !(*this == other);
    }
};

// Structure to store operations
struct Move {
    Point p1;
    Point p2;
};

const int N = 30;
int grid[N][N];
vector<Move> operations;

// Get adjacent neighbors in 6 directions
vector<Point> get_neighbors(Point p) {
    vector<Point> res;
    res.reserve(6);
    int x = p.x;
    int y = p.y;
    // Directions: Top-Left, Top-Right, Left, Right, Bottom-Left, Bottom-Right
    int dx[] = {-1, -1, 0, 0, 1, 1};
    int dy[] = {-1, 0, -1, 1, 0, 1};
    
    for (int i = 0; i < 6; ++i) {
        int nx = x + dx[i];
        int ny = y + dy[i];
        // Check pyramid bounds: 0 <= nx < N, 0 <= ny <= nx
        if (nx >= 0 && nx < N && ny >= 0 && ny <= nx) {
            res.push_back({nx, ny});
        }
    }
    return res;
}

// Perform a swap and record the operation
void perform_swap(Point p1, Point p2) {
    operations.push_back({p1, p2});
    swap(grid[p1.x][p1.y], grid[p2.x][p2.y]);
}

// Check if a point is a valid node to traverse
// It must not be in a fixed tier (< current_tier)
// And if it is in current_tier, it must not be a "locked" slot (already correct)
bool is_valid(Point p, int current_tier, const vector<vector<bool>>& locked) {
    if (p.x < current_tier) return false;
    if (p.x == current_tier && locked[p.x][p.y]) return false;
    return true;
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    // Read Input
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j <= i; ++j) {
            cin >> grid[i][j];
        }
    }

    // Keep track of which slots are "locked" (contain a correct value for their tier)
    vector<vector<bool>> locked(N, vector<bool>(N, false));

    // Iterate through each tier from top to bottom
    for (int tier = 0; tier < N; ++tier) {
        // Calculate the range of values that belong to this tier in a sorted pyramid
        // Tier k should ideally contain values from k*(k+1)/2 to (k+1)*(k+2)/2 - 1
        int start_val = tier * (tier + 1) / 2;
        int end_val = (tier + 1) * (tier + 2) / 2 - 1;
        
        while (true) {
            vector<Point> active_slots;
            
            // Identify which slots in the current tier are correct (locked) and which need filling (active)
            for (int j = 0; j <= tier; ++j) {
                int val = grid[tier][j];
                if (val >= start_val && val <= end_val) {
                    locked[tier][j] = true;
                } else {
                    locked[tier][j] = false;
                    active_slots.push_back({tier, j});
                }
            }

            // If no active slots remain, the tier is correctly filled
            if (active_slots.empty()) break;

            // BFS Initialization
            // We start BFS from all active slots simultaneously to find the nearest target ball
            queue<Point> q;
            vector<vector<Point>> parent(N, vector<Point>(N, {-1, -1}));
            vector<vector<bool>> visited(N, vector<bool>(N, false));
            
            for (auto p : active_slots) {
                q.push(p);
                visited[p.x][p.y] = true;
            }
            
            Point found_ball_pos = {-1, -1};
            bool found = false;
            
            while (!q.empty()) {
                Point curr = q.front();
                q.pop();
                
                int val = grid[curr.x][curr.y];
                // Check if the current ball belongs to the target range for this tier
                // Since active slots contain wrong values, and locked slots are not visited/valid,
                // any encountered value in range must be a target ball located deeper in the pyramid.
                if (val >= start_val && val <= end_val) {
                    found_ball_pos = curr;
                    found = true;
                    break;
                }
                
                for (Point next : get_neighbors(curr)) {
                    // Traverse only valid nodes (not fixed tiers, not locked slots in current tier)
                    if (is_valid(next, tier, locked) && !visited[next.x][next.y]) {
                        visited[next.x][next.y] = true;
                        parent[next.x][next.y] = curr;
                        q.push(next);
                    }
                }
            }
            
            if (found) {
                // Reconstruct path and move the ball
                // The BFS parent pointers point towards the slot (source of BFS)
                // So we swap from found_ball_pos towards the slot
                Point curr = found_ball_pos;
                while (true) {
                    Point par = parent[curr.x][curr.y];
                    if (par.x == -1) break; // Reached the slot
                    perform_swap(curr, par);
                    curr = par;
                }
            } else {
                // Should not happen for solvable cases
                break; 
            }
        }
    }

    // Output results
    cout << operations.size() << "\n";
    for (const auto& op : operations) {
        cout << op.p1.x << " " << op.p1.y << " " << op.p2.x << " " << op.p2.y << "\n";
    }

    return 0;
}