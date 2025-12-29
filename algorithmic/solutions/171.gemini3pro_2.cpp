#include <iostream>
#include <vector>
#include <queue>
#include <algorithm>

using namespace std;

// Problem constants
const int N_SIZE = 20;

// Directions: U, D, L, R
// Corresponds to indices: 0: U, 1: D, 2: L, 3: R
const int dr[] = {-1, 1, 0, 0};
const int dc[] = {0, 0, -1, 1};
const char dchar[] = {'U', 'D', 'L', 'R'};

struct NodeInfo {
    int dist;
    char action; // 'M' for Move, 'S' for Slide
    char dir;    // 'U', 'D', 'L', 'R'
    int pr, pc;  // Parent coordinates for path reconstruction
};

// Global grid to keep track of blocks.
// In this solution, we do not place blocks ('Alter'), so this remains false (empty)
// except potentially for boundary checks which are handled separately.
bool grid[N_SIZE][N_SIZE];

// Check if coordinates are within the grid
bool is_valid(int r, int c) {
    return r >= 0 && r < N_SIZE && c >= 0 && c < N_SIZE;
}

// Check if a cell is a block (either outside boundary or an explicit block on grid)
bool is_block(int r, int c) {
    if (!is_valid(r, c)) return true;
    return grid[r][c];
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int N, M;
    if (!(cin >> N >> M)) return 0;

    vector<pair<int, int>> targets(M);
    for (int i = 0; i < M; ++i) {
        cin >> targets[i].first >> targets[i].second;
    }

    // Initialize grid (all empty initially)
    for (int r = 0; r < N_SIZE; ++r) {
        for (int c = 0; c < N_SIZE; ++c) {
            grid[r][c] = false;
        }
    }

    int curr_r = targets[0].first;
    int curr_c = targets[0].second;

    // Process each target sequentially
    // Strategy: Use BFS to find the shortest path of Moves and Slides to the next target.
    // We do not use Alter to place blocks, as the overhead is generally too high compared to walking.
    for (int i = 0; i < M - 1; ++i) {
        int target_r = targets[i+1].first;
        int target_c = targets[i+1].second;

        // BFS structures
        static NodeInfo info[N_SIZE][N_SIZE];
        for(int r=0; r<N_SIZE; ++r) {
            for(int c=0; c<N_SIZE; ++c) {
                info[r][c] = {-1, ' ', ' ', -1, -1};
            }
        }

        queue<pair<int, int>> q;
        info[curr_r][curr_c] = {0, ' ', ' ', -1, -1};
        q.push({curr_r, curr_c});

        bool reached = false;

        while (!q.empty()) {
            pair<int, int> curr = q.front();
            q.pop();
            int r = curr.first;
            int c = curr.second;

            if (r == target_r && c == target_c) {
                reached = true;
                break;
            }

            int d = info[r][c].dist;

            // Try Move actions (1 step)
            for (int k = 0; k < 4; ++k) {
                int nr = r + dr[k];
                int nc = c + dc[k];
                
                // Can move if valid and not a block
                if (is_valid(nr, nc) && !grid[nr][nc]) {
                    if (info[nr][nc].dist == -1) {
                        info[nr][nc] = {d + 1, 'M', dchar[k], r, c};
                        q.push({nr, nc});
                    }
                }
            }

            // Try Slide actions (until block)
            for (int k = 0; k < 4; ++k) {
                int nr = r;
                int nc = c;
                // Simulate slide
                while (true) {
                    int next_r = nr + dr[k];
                    int next_c = nc + dc[k];
                    if (is_block(next_r, next_c)) {
                        break; // Stop immediately before the block
                    }
                    nr = next_r;
                    nc = next_c;
                }

                // If we moved at least one square
                if (nr != r || nc != c) {
                    if (info[nr][nc].dist == -1) {
                        info[nr][nc] = {d + 1, 'S', dchar[k], r, c};
                        q.push({nr, nc});
                    }
                }
            }
        }

        // Reconstruct path
        if (reached) {
            vector<pair<char, char>> path;
            int r = target_r;
            int c = target_c;
            while (r != curr_r || c != curr_c) {
                NodeInfo& ni = info[r][c];
                path.push_back({ni.action, ni.dir});
                int pr = ni.pr;
                int pc = ni.pc;
                r = pr;
                c = pc;
            }
            // Path is backwards, reverse it
            reverse(path.begin(), path.end());
            for (auto& p : path) {
                cout << p.first << " " << p.second << "\n";
            }
        }

        // Update current position for next leg
        curr_r = target_r;
        curr_c = target_c;
    }

    return 0;
}