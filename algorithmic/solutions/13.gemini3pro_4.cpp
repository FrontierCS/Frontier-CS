#include <iostream>
#include <vector>
#include <queue>
#include <algorithm>

using namespace std;

// Maximum coordinate size we expect to use. 
// Robot starts <= 20. T=3000. 
// We will constrain the robot within a much smaller box (approx 200x200).
const int MAX_COORD = 500;
int grid[MAX_COORD][MAX_COORD]; // 0: white, 1: black
int vis[MAX_COORD][MAX_COORD];
int vis_gen = 0;

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int sx, sy;
    if (!(cin >> sx >> sy)) return 0;

    int rx = sx, ry = sy;
    // Set target barrier line K.
    // Based on sx, sy <= 20, a buffer is needed to build the wall.
    // K = sx + sy + 70 gives enough time to build a blocking wall on the diagonal x+y=K.
    // The robot moves towards the wall, and we greedily block the closest points.
    int K = max(60, sx + sy + 70);

    int turns = 3000;
    bool trapped = false;

    // 8 directions for robot movement
    int dx[] = {1, 1, 1, 0, 0, -1, -1, -1};
    int dy[] = {1, 0, -1, 1, -1, 1, 0, -1};

    for (int t = 1; t <= turns; ++t) {
        int mx = -1, my = -1;
        bool escape_found = false;

        if (!trapped) {
            // Phase 1: Build the wall at x+y=K
            // We use BFS to find the reachable cell on the line x+y=K that is closest to the robot.
            vis_gen++;
            queue<pair<int, int>> q;
            q.push({rx, ry});
            vis[rx][ry] = vis_gen;
            
            while(!q.empty()){
                pair<int, int> curr = q.front();
                q.pop();
                int cx = curr.first;
                int cy = curr.second;

                // Priority target found: a cell on our defensive wall
                if (cx + cy == K) {
                    mx = cx; my = cy;
                    escape_found = true;
                    break;
                }

                // Optimization: don't search beyond the wall.
                for(int i=0; i<8; ++i){
                    int nx = cx + dx[i];
                    int ny = cy + dy[i];
                    
                    if(nx < 1 || ny < 1) continue;
                    // If nx + ny > K, we don't process it as a path to the wall 
                    // (assuming we successfully block K).
                    if (nx + ny > K) continue;

                    if(grid[nx][ny] == 0 && vis[nx][ny] != vis_gen){
                        vis[nx][ny] = vis_gen;
                        q.push({nx, ny});
                    }
                }
            }
            
            // If BFS could not find a path to x+y=K, the robot is trapped inside.
            if (!escape_found) {
                trapped = true;
            }
        }

        if (trapped) {
            // Phase 2: Squeeze the robot.
            // The robot is confined to a finite area. We need to make it explode.
            // Strategy: Block an immediate white neighbor to reduce mobility quickly.
            for(int i=0; i<8; ++i){
                int nx = rx + dx[i];
                int ny = ry + dy[i];
                if(nx >= 1 && ny >= 1 && grid[nx][ny] == 0) {
                    mx = nx; my = ny;
                    break;
                }
            }
            
            // If no immediate neighbors are white (or we want to search deeper),
            // find the closest reachable white cell to fill the space.
            if (mx == -1) {
                vis_gen++;
                queue<pair<int, int>> q;
                q.push({rx, ry});
                vis[rx][ry] = vis_gen;
                
                while(!q.empty()){
                    pair<int, int> curr = q.front();
                    q.pop();
                    int cx = curr.first;
                    int cy = curr.second;
                    
                    // Found a candidate that is not the robot itself
                    if (!(cx == rx && cy == ry) && grid[cx][cy] == 0) {
                        mx = cx; my = cy;
                        break;
                    }
                    
                    for(int i=0; i<8; ++i){
                        int nx = cx + dx[i];
                        int ny = cy + dy[i];
                        if(nx < 1 || ny < 1) continue;
                        if(grid[nx][ny] == 0 && vis[nx][ny] != vis_gen){
                            vis[nx][ny] = vis_gen;
                            q.push({nx, ny});
                        }
                    }
                }
            }
        }

        // Fallback: If no strategic move found (e.g. map is somehow full), pick any white cell.
        if (mx == -1) {
             for(int i=1; i<=K; ++i){
                for(int j=1; j<=K; ++j){
                     if(grid[i][j] == 0) { mx=i; my=j; goto move_found; }
                }
            }
            // If absolutely nothing (unlikely), block (1,1)
            mx = 1; my = 1;
        }
        move_found:;

        // Output move
        cout << mx << " " << my << endl;
        grid[mx][my] = 1;

        // Read response
        int n_rx, n_ry;
        cin >> n_rx >> n_ry;
        if (n_rx == 0 && n_ry == 0) {
            return 0; // Robot exploded
        }
        rx = n_rx;
        ry = n_ry;
    }

    return 0;
}