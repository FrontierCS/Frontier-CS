#include <iostream>
#include <vector>
#include <queue>
#include <tuple>
#include <cstring>
#include <algorithm>

using namespace std;

const int GRID_MAX = 405;
int black[GRID_MAX][GRID_MAX];
int dist[GRID_MAX][GRID_MAX];
pair<int, int> parent[GRID_MAX][GRID_MAX];

// Directions for 8 neighbors
int dx[] = {0, 0, 1, -1, 1, 1, -1, -1};
int dy[] = {1, -1, 0, 0, 1, -1, 1, -1};

bool is_valid(int x, int y, int limit) {
    return x >= 1 && x <= limit && y >= 1 && y <= limit;
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int sx, sy;
    if (!(cin >> sx >> sy)) return 0;

    // Initial boundary. The strategy is to block the shortest path to this boundary.
    // If the robot breaches it, we expand.
    int BOUND = max(max(sx, sy) + 30, 70);

    for (int turn = 0; turn < 3000; ++turn) {
        // If robot escaped the bound, expand bound to keep strategy valid
        if (sx >= BOUND || sy >= BOUND) {
            BOUND = max(sx, sy) + 20;
        }

        // Limit BFS search space for performance
        int search_limit = BOUND + 2;
        if (search_limit >= GRID_MAX) search_limit = GRID_MAX - 1;

        // BFS initialization
        // We use a manual loop or smaller memset if performance is critical, 
        // but with bounded search_limit and 3000 turns, full memset on small grid is fine?
        // Actually, let's just clear the visited/dist array for the relevant range.
        for(int i=1; i<=search_limit; ++i) {
            for(int j=1; j<=search_limit; ++j) {
                dist[i][j] = -1;
            }
        }

        queue<pair<int, int>> q;
        q.push({sx, sy});
        dist[sx][sy] = 0;
        
        int target_x = -1, target_y = -1;
        bool trapped = true;
        
        while (!q.empty()) {
            pair<int, int> curr = q.front();
            q.pop();
            int cx = curr.first;
            int cy = curr.second;
            
            // Check if we reached the virtual boundary
            if (cx >= BOUND || cy >= BOUND) {
                target_x = cx;
                target_y = cy;
                trapped = false;
                break;
            }
            
            for (int i = 0; i < 8; ++i) {
                int nx = cx + dx[i];
                int ny = cy + dy[i];
                
                // Treat black cells as walls
                if (is_valid(nx, ny, search_limit) && !black[nx][ny] && dist[nx][ny] == -1) {
                    dist[nx][ny] = dist[cx][cy] + 1;
                    parent[nx][ny] = {cx, cy};
                    q.push({nx, ny});
                }
            }
        }
        
        int mx = -1, my = -1;
        
        if (!trapped) {
            if (dist[target_x][target_y] == 0) {
                // Robot is already on or past boundary (should be handled by BOUND expansion, but strictly safe)
                // Just attack any valid white neighbor to push back
                for (int i = 0; i < 8; ++i) {
                    int nx = sx + dx[i];
                    int ny = sy + dy[i];
                    if (nx >= 1 && ny >= 1 && !black[nx][ny]) {
                        mx = nx; my = ny; break;
                    }
                }
            } else {
                // Trace back to finding the first step from start
                int curr_x = target_x;
                int curr_y = target_y;
                while (true) {
                    pair<int, int> p = parent[curr_x][curr_y];
                    if (p.first == sx && p.second == sy) {
                        mx = curr_x;
                        my = curr_y;
                        break;
                    }
                    curr_x = p.first;
                    curr_y = p.second;
                }
            }
        } else {
            // Trapped: Robot cannot reach the boundary.
            // Strategy: Reduce the safe area. Attack a neighbor.
            for (int i = 0; i < 8; ++i) {
                int nx = sx + dx[i];
                int ny = sy + dy[i];
                if (nx >= 1 && ny >= 1 && !black[nx][ny]) {
                    mx = nx; my = ny;
                    // Heuristic: prefer neighbors that are "closer" to origin or just first found
                    break; 
                }
            }
        }
        
        // Fallback if no move found (e.g. fully surrounded by black/walls but somehow still playing)
        if (mx == -1) {
            // Find any valid spot to mark to not crash
             for(int i=1; i<=BOUND; ++i) {
                 for(int j=1; j<=BOUND; ++j) {
                     if(!black[i][j] && (i!=sx || j!=sy)) {
                         mx = i; my = j; goto found;
                     }
                 }
             }
             found:;
             if(mx == -1) { mx = 1; my = 1; } // Should not happen
        }
        
        // Output move
        cout << mx << " " << my << endl;
        black[mx][my] = 1;
        
        // Read interaction
        int rx, ry;
        cin >> rx >> ry;
        if (rx == 0 && ry == 0) {
            return 0; // Robot exploded
        }
        sx = rx;
        sy = ry;
    }
    
    return 0;
}