#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <algorithm>
#include <tuple>

using namespace std;

int n;
int grid[55][55];

// Function to query the judge
int query(int r1, int c1, int r2, int c2) {
    cout << "? " << r1 << " " << c1 << " " << r2 << " " << c2 << endl;
    int res;
    cin >> res;
    if (res == -1) exit(0);
    return res;
}

// Check if (r, c) is inside grid
bool isValid(int r, int c) {
    return r >= 1 && r <= n && c >= 1 && c <= n;
}

struct Cell { int r, c; };

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    if (!(cin >> n)) return 0;
    
    // Initialize grid
    for(int i=1; i<=n; ++i)
        for(int j=1; j<=n; ++j)
            grid[i][j] = -1;
            
    grid[1][1] = 1;
    grid[n][n] = 0;
    
    // Valid moves for BFS (connecting u to v such that query(u, v) is valid)
    // A move (dr, dc) connects (r, c) to (r+dr, c+dc).
    // Valid queries require x1 <= x2 and y1 <= y2.
    // The moves below cover forward and backward directions that satisfy this after sorting.
    vector<pair<int, int>> moves = {{0, 2}, {2, 0}, {1, 1}, {0, -2}, {-2, 0}, {-1, -1}};
    
    // Fill Even sum cells
    deque<Cell> q;
    q.push_back({1, 1});
    // grid[1][1] is already set
    
    while(!q.empty()){
        Cell u = q.front(); q.pop_front();
        for(auto mv : moves){
            int nr = u.r + mv.first;
            int nc = u.c + mv.second;
            // Check bounds, not visited, and same parity
            if(isValid(nr, nc) && grid[nr][nc] == -1 && (u.r + u.c)%2 == (nr + nc)%2) {
                int r1=u.r, c1=u.c, r2=nr, c2=nc;
                if(r1 > r2) { swap(r1, r2); swap(c1, c2); }
                
                // Valid query check: row sorted, col must be non-decreasing
                if(c1 <= c2) {
                    int res = query(r1, c1, r2, c2);
                    if(res == 1) grid[nr][nc] = grid[u.r][u.c];
                    else grid[nr][nc] = 1 - grid[u.r][u.c];
                    q.push_back({nr, nc});
                }
            }
        }
    }
    
    // Fill Odd sum cells
    // Start from (1, 2). If n < 2 not possible, but n >= 3.
    // Assume base value 0 for (1, 2)
    grid[1][2] = 0;
    q.push_back({1, 2});
    
    // We also need to ensure (2, 1) is covered.
    // If (2, 1) is not reached from (1, 2) via the moves above, we might miss it.
    // However, (1, 2) connects to (2, 3) (dist 2). (2, 3) connects to (2, 1) (dist 2).
    // So (2, 1) will be reached.
    // But we should check if (2, 1) is initially unvisited.
    // If (2, 1) is not pushed, we might need to push it if not visited.
    // Just in case, we iterate to ensure connectivity if the graph was disconnected (it isn't, but safe).
    // Given the moves and rectangular grid, all nodes of same parity are connected.
    
    while(!q.empty()){
        Cell u = q.front(); q.pop_front();
        for(auto mv : moves){
            int nr = u.r + mv.first;
            int nc = u.c + mv.second;
            if(isValid(nr, nc) && grid[nr][nc] == -1 && (u.r + u.c)%2 == (nr + nc)%2) {
                int r1=u.r, c1=u.c, r2=nr, c2=nc;
                if(r1 > r2) { swap(r1, r2); swap(c1, c2); }
                if(c1 <= c2) {
                    int res = query(r1, c1, r2, c2);
                    if(res == 1) grid[nr][nc] = grid[u.r][u.c];
                    else grid[nr][nc] = 1 - grid[u.r][u.c];
                    q.push_back({nr, nc});
                }
            }
        }
    }
    
    // Determine the correct base for odd cells
    bool determined = false;
    for(int r1=1; r1<=n && !determined; ++r1) {
        for(int c1=1; c1<=n && !determined; ++c1) {
            // Try distance 3 neighbors
            int diffs[][2] = {{0, 3}, {1, 2}, {2, 1}, {3, 0}};
            for(auto d : diffs) {
                int r2 = r1 + d[0];
                int c2 = c1 + d[1];
                if(isValid(r2, c2)) {
                    bool can0 = false;
                    bool can1 = false;
                    
                    // Collect all paths
                    vector<vector<int>> paths;
                    auto get_paths = [&](auto self, int r, int c, vector<int>& p) -> void {
                        p.push_back(grid[r][c]);
                        if(r==r2 && c==c2) {
                            paths.push_back(p);
                            p.pop_back();
                            return;
                        }
                        if(c+1<=c2) self(self, r, c+1, p);
                        if(r+1<=r2) self(self, r+1, c, p);
                        p.pop_back();
                    };
                    vector<int> dummy;
                    get_paths(get_paths, r1, c1, dummy);
                    
                    for(auto &p : paths) {
                        // BaseOdd = 0 condition:
                        // Path is palindrome if sequence matches as is.
                        if(p[0] == p[3] && p[1] == p[2]) can0 = true;
                        
                        // BaseOdd = 1 condition:
                        // Odd sum cells are flipped.
                        // One of (p[0], p[3]) is even, one odd. Same for (p[1], p[2]).
                        // So equality check becomes inequality.
                        if(p[0] != p[3] && p[1] != p[2]) can1 = true;
                    }
                    
                    if(can0 != can1) {
                        int res = query(r1, c1, r2, c2);
                        if((res == 1 && !can0) || (res == 0 && can0)) {
                            // Need flip
                            for(int i=1; i<=n; ++i)
                                for(int j=1; j<=n; ++j)
                                    if((i+j)%2 == 1) grid[i][j] = 1 - grid[i][j];
                        }
                        determined = true;
                        break;
                    }
                }
            }
        }
    }
    
    cout << "!" << endl;
    for(int i=1; i<=n; ++i) {
        for(int j=1; j<=n; ++j) cout << grid[i][j];
        cout << endl;
    }
    
    return 0;
}