#include <iostream>
#include <vector>
#include <queue>
#include <tuple>
#include <cmath>
#include <algorithm>

using namespace std;

const int MAX_COORD = 3005;
int grid[MAX_COORD][MAX_COORD]; // 0: white, 1: black
int dist_map[MAX_COORD][MAX_COORD];
int visited_token[MAX_COORD][MAX_COORD];
int token = 0;

int rx, ry;
int T = 3000;

// Directions for BFS (8 neighbors)
int dx[] = {1, 1, 1, 0, 0, -1, -1, -1};
int dy[] = {1, 0, -1, 1, -1, 1, 0, -1};

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> rx >> ry)) return 0;

    // Initial wall distance. Sufficiently large to surround robot but small enough to manage.
    // Start with a diagonal wall at x + y = K.
    int K = rx + ry + 60; 

    for (int t = 1; t <= T; ++t) {
        // If robot pushes too close to the wall, retreat the wall (expand K)
        // This is a defensive measure, though ideally we trap it before.
        if (rx + ry > K - 5) {
            K = rx + ry + 40;
        }

        token++;
        queue<pair<int, int>> q;
        q.push({rx, ry});
        visited_token[rx][ry] = token;
        
        vector<pair<int, int>> cells_at_K;
        vector<pair<int, int>> cells_at_max;
        int max_reached_sum = -1;
        
        // BFS to find reachable cells
        // We limit search to cells with sum <= K
        while(!q.empty()){
            auto [cx, cy] = q.front();
            q.pop();
            
            int s = cx + cy;
            
            // Track max reached sum and cells there
            if (s > max_reached_sum) {
                max_reached_sum = s;
                cells_at_max.clear();
                cells_at_max.push_back({cx, cy});
            } else if (s == max_reached_sum) {
                cells_at_max.push_back({cx, cy});
            }

            if (s == K) {
                cells_at_K.push_back({cx, cy});
                // We don't continue BFS from the boundary K, as we want to seal it.
                continue; 
            }
            
            for(int i=0; i<8; ++i){
                int nx = cx + dx[i];
                int ny = cy + dy[i];
                
                // Bounds check. Stay within first quadrant and don't exceed K for efficiency
                // Note: The problem grid is infinite, but we virtually limit by K.
                if(nx >= 1 && ny >= 1 && nx + ny <= K){
                    if(visited_token[nx][ny] != token && grid[nx][ny] == 0){
                        visited_token[nx][ny] = token;
                        q.push({nx, ny});
                    }
                }
            }
        }
        
        int mx = -1, my = -1;
        
        if (!cells_at_K.empty()) {
            // Target the diagonal x+y=K. 
            // BFS discovers nodes in increasing order of distance (steps).
            // So cells_at_K[0] is the closest one.
            mx = cells_at_K[0].first;
            my = cells_at_K[0].second;
        } else {
            // Wall at K is unreachable (robot is enclosed).
            // Shrink the cage.
            if (max_reached_sum != -1) {
                K = max_reached_sum;
                mx = cells_at_max[0].first;
                my = cells_at_max[0].second;
            } else {
                // Robot has no white neighbors reachable? 
                // This means it's completely surrounded by black cells locally.
                // Just mark a valid cell (won't affect outcome as robot explodes).
                mx = 1; my = 1;
            }
        }
        
        // Ensure we don't mark an already black cell (BFS logic prevents this, but safety check)
        // If mx, my is somehow invalid or 0,0, logic error.
        
        cout << mx << " " << my << endl;
        grid[mx][my] = 1;
        
        int n_rx, n_ry;
        cin >> n_rx >> n_ry;
        if (n_rx == 0 && n_ry == 0) return 0; // Robot exploded
        rx = n_rx;
        ry = n_ry;
    }

    return 0;
}