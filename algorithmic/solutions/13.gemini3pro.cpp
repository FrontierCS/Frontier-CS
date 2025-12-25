#include <iostream>
#include <vector>
#include <queue>
#include <algorithm>
#include <cmath>

using namespace std;

const int MAX_COORD = 3005;
const int LIMIT_T = 3000;
bool is_black[MAX_COORD][MAX_COORD];
int visited[MAX_COORD][MAX_COORD];
int visited_token = 0;

int cur_rx, cur_ry;
int B;

// Directions for King's move (8 directions)
int dx[] = {0, 0, 1, -1, 1, 1, -1, -1};
int dy[] = {1, -1, 0, 0, 1, -1, 1, -1};

struct Point {
    int x, y;
};

bool isValid(int x, int y) {
    return x >= 1 && y >= 1 && x <= LIMIT_T && y <= LIMIT_T;
}

int countBlackNeighbors(int x, int y) {
    int cnt = 0;
    for (int i = 0; i < 8; ++i) {
        int nx = x + dx[i];
        int ny = y + dy[i];
        if (isValid(nx, ny) && is_black[nx][ny]) {
            cnt++;
        }
    }
    return cnt;
}

int main() {
    // Fast IO
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> cur_rx >> cur_ry)) return 0;

    // Initial boundary is set slightly further from the robot.
    // We will dynamically adjust it as the robot moves.
    B = max(cur_rx, cur_ry) + 15;
    if (B > LIMIT_T) B = LIMIT_T;

    for (int turn = 1; turn <= LIMIT_T; ++turn) {
        // Expand boundary if robot is too close to the current boundary
        if (max(cur_rx, cur_ry) + 5 >= B) {
            B = max(cur_rx, cur_ry) + 20;
            if (B > LIMIT_T) B = LIMIT_T;
        }

        // BFS initialization
        visited_token++;
        
        // Queue stores {point, distance}
        queue<pair<Point, int>> bfs_q;
        bfs_q.push({{cur_rx, cur_ry}, 0});
        visited[cur_rx][cur_ry] = visited_token;
        
        vector<Point> candidates;
        int min_dist = -1;
        bool trapped = true;
        
        // BFS to find the shortest path to the virtual boundary defined by B
        while(!bfs_q.empty()) {
            pair<Point, int> curr = bfs_q.front();
            bfs_q.pop();
            Point p = curr.first;
            int d = curr.second;
            
            // If we found candidates at min_dist, we don't explore deeper layers
            if (min_dist != -1 && d > min_dist) {
                break; 
            }
            
            // Check boundary condition: a cell is considered a boundary target if max(x, y) >= B
            if (max(p.x, p.y) >= B) {
                if (min_dist == -1) min_dist = d;
                if (d == min_dist) {
                    candidates.push_back(p);
                }
                trapped = false;
                // Do not expand from boundary cells further
                continue;
            }
            
            for (int i = 0; i < 8; ++i) {
                int nx = p.x + dx[i];
                int ny = p.y + dy[i];
                
                // Only traverse valid white cells
                if (isValid(nx, ny) && !is_black[nx][ny] && visited[nx][ny] != visited_token) {
                    visited[nx][ny] = visited_token;
                    bfs_q.push({{nx, ny}, d + 1});
                }
            }
        }
        
        Point target = { -1, -1 };
        
        if (trapped) {
            // Squeeze mode: the robot is trapped inside the black cells.
            // We just need to reduce its available space. Pick any white neighbor.
            for (int i = 0; i < 8; ++i) {
                int nx = cur_rx + dx[i];
                int ny = cur_ry + dy[i];
                if (isValid(nx, ny) && !is_black[nx][ny]) {
                    target = {nx, ny};
                    break;
                }
            }
            // Fallback (should not happen if the robot can still move)
            if (target.x == -1) {
                // Robot has no white neighbors -> likely about to explode or game logic will handle it.
                // Output a valid coordinate far away to not break interaction.
                target = {1, 1};
                while(target.x <= LIMIT_T) {
                    if (!is_black[target.x][1]) { target.y = 1; break; }
                    target.x++;
                }
            }
        } else {
            // Select best candidate from the closest boundary cells.
            // Heuristic: prioritize cells that are adjacent to existing black cells (to extend walls).
            int best_bn = -1;
            for (const auto& cand : candidates) {
                int bn = countBlackNeighbors(cand.x, cand.y);
                if (bn > best_bn) {
                    best_bn = bn;
                    target = cand;
                }
            }
        }
        
        // Output move
        cout << target.x << " " << target.y << endl;
        is_black[target.x][target.y] = true;
        
        // Read response
        int rx_new, ry_new;
        if (!(cin >> rx_new >> ry_new)) break;
        
        if (rx_new == 0 && ry_new == 0) {
            return 0; // Robot exploded
        }
        
        cur_rx = rx_new;
        cur_ry = ry_new;
    }

    return 0;
}