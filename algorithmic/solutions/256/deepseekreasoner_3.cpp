#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <cmath>
#include <algorithm>

using namespace std;

int n;
int grid[55][55];
bool visited[55][55];

// Helper to ask queries
int ask(int r1, int c1, int r2, int c2) {
    cout << "? " << r1 << " " << c1 << " " << r2 << " " << c2 << endl;
    int res;
    cin >> res;
    if (res == -1) exit(0);
    return res;
}

struct Node {
    int r, c;
};

// Memoization for checking palindromic paths
int memo[55][55][55][55];
int check_grid[55][55];

// DP to check if there exists a palindromic path in check_grid from (r1,c1) to (r2,c2)
bool has_pal_path(int r1, int c1, int r2, int c2) {
    if (r1 > r2 || c1 > c2) return false;
    if (r1 == r2 && c1 == c2) return true;
    if (memo[r1][c1][r2][c2] != -1) return memo[r1][c1][r2][c2];

    if (check_grid[r1][c1] != check_grid[r2][c2]) {
        return memo[r1][c1][r2][c2] = 0;
    }
    
    // Check neighbors
    // Start moves: (r1+1, c1) or (r1, c1+1)
    // End moves: (r2-1, c2) or (r2, c2-1)
    
    bool res = false;
    
    // S move Down
    if (r1 + 1 <= r2) {
        // E move Up
        if (r2 > r1) {
            if (has_pal_path(r1+1, c1, r2-1, c2)) res = true;
        }
        // E move Left
        if (!res && c2 > c1) {
            if (has_pal_path(r1+1, c1, r2, c2-1)) res = true;
        }
    }
    
    // S move Right
    if (!res && c1 + 1 <= c2) {
         // E move Up
         if (r2 > r1) {
             if (has_pal_path(r1, c1+1, r2-1, c2)) res = true;
         }
         // E move Left
         if (!res && c2 > c1) {
             if (has_pal_path(r1, c1+1, r2, c2-1)) res = true;
         }
    }
    
    return memo[r1][c1][r2][c2] = res;
}

bool solve_check(int r1, int c1, int r2, int c2) {
    // reset memo only for relevant range to optimize
    for(int i=r1; i<=r2; ++i)
        for(int j=c1; j<=c2; ++j)
            for(int k=r1; k<=r2; ++k)
                for(int l=c1; l<=c2; ++l)
                    memo[i][j][k][l] = -1;
    return has_pal_path(r1, c1, r2, c2);
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n)) return 0;

    for (int i = 1; i <= n; ++i)
        for (int j = 1; j <= n; ++j)
            grid[i][j] = -1;

    // Component 0 (White): sum of coords even. (1,1) and (n,n) belong here.
    grid[1][1] = 1;
    grid[n][n] = 0;
    visited[1][1] = true;
    visited[n][n] = true;

    vector<Node> q;
    q.push_back({1, 1});
    q.push_back({n, n});
    
    int head = 0;
    
    // Directions for distance 2 moves (to keep parity same)
    int dr[] = {1, 2, 0, -1, -2, 0};
    int dc[] = {1, 0, 2, -1, 0, -2};
            
    while(head < q.size()){
        Node u = q[head++];
        int r = u.r;
        int c = u.c;
        
        for(int k=0; k<6; ++k) {
            int nr = r + dr[k];
            int nc = c + dc[k];
            
            if (nr < 1 || nr > n || nc < 1 || nc > n) continue;
            if (visited[nr][nc]) continue;
            if ((nr + nc) % 2 != (r + c) % 2) continue;
            
            // Should satisfy x1 <= x2, y1 <= y2 for query
            bool valid_dir = false;
            if (nr >= r && nc >= c) valid_dir = true;
            if (nr <= r && nc <= c) valid_dir = true;
            
            if (!valid_dir) continue;
            
            int r1 = min(r, nr), c1 = min(c, nc);
            int r2 = max(r, nr), c2 = max(c, nc);
            
            int ans = ask(r1, c1, r2, c2);
            if (ans == 1) grid[nr][nc] = grid[r][c];
            else grid[nr][nc] = 1 - grid[r][c];
            
            visited[nr][nc] = true;
            q.push_back({nr, nc});
        }
    }
    
    // Component 1 (Black): sum of coords odd.
    int br = -1, bc = -1;
    for(int i=1; i<=n; ++i) {
        for(int j=1; j<=n; ++j) {
            if (!visited[i][j] && (i+j)%2 == 1) {
                br = i; bc = j;
                break;
            }
        }
        if (br != -1) break;
    }
    
    if (br != -1) {
        grid[br][bc] = 0; // Assume 0 initially, will fix later
        visited[br][bc] = true;
        q.clear();
        q.push_back({br, bc});
        head = 0;
        
        while(head < q.size()){
            Node u = q[head++];
            int r = u.r;
            int c = u.c;
            
            for(int k=0; k<6; ++k) {
                int nr = r + dr[k];
                int nc = c + dc[k];
                
                if (nr < 1 || nr > n || nc < 1 || nc > n) continue;
                if (visited[nr][nc]) continue;
                if ((nr + nc) % 2 != (r + c) % 2) continue;
                
                bool valid_dir = false;
                if (nr >= r && nc >= c) valid_dir = true;
                if (nr <= r && nc <= c) valid_dir = true;
                
                if (!valid_dir) continue;
                
                int r1 = min(r, nr), c1 = min(c, nc);
                int r2 = max(r, nr), c2 = max(c, nc);
                
                int ans = ask(r1, c1, r2, c2);
                if (ans == 1) grid[nr][nc] = grid[r][c];
                else grid[nr][nc] = 1 - grid[r][c];
                
                visited[nr][nc] = true;
                q.push_back({nr, nc});
            }
        }
    }
    
    // Determine if black cells need flip
    int best_r1 = -1, best_c1 = -1, best_r2 = -1, best_c2 = -1;
    int expected1 = -1;
    bool found = false;

    // Search for a distinguishing query (odd distance, e.g., dist 3)
    for(int r=1; r<=n && !found; ++r) {
        for(int c=1; c<=n && !found; ++c) {
             // Targets: (r+1, c+2), (r+2, c+1)
             int targets[2][2] = {{1, 2}, {2, 1}};
             for(int k=0; k<2; ++k) {
                 int tr = r + targets[k][0];
                 int tc = c + targets[k][1];
                 if (tr <= n && tc <= n) {
                     // Check Grid1
                     for(int i=1;i<=n;++i) 
                        for(int j=1;j<=n;++j) check_grid[i][j] = grid[i][j];
                     bool ans1 = solve_check(r, c, tr, tc);
                     
                     // Check Grid2 (Blacks flipped)
                     for(int i=1;i<=n;++i) 
                        for(int j=1;j<=n;++j) {
                            if ((i+j)%2 == 1) check_grid[i][j] = 1 - grid[i][j];
                            else check_grid[i][j] = grid[i][j];
                        }
                     bool ans2 = solve_check(r, c, tr, tc);
                     
                     if (ans1 != ans2) {
                         best_r1 = r; best_c1 = c;
                         best_r2 = tr; best_c2 = tc;
                         expected1 = ans1;
                         found = true;
                         break;
                     }
                 }
             }
        }
    }
    
    if (found) {
        int actual = ask(best_r1, best_c1, best_r2, best_c2);
        if (actual != expected1) {
            // Flip black cells
            for(int i=1; i<=n; ++i)
                for(int j=1; j<=n; ++j)
                    if ((i+j)%2 == 1) grid[i][j] = 1 - grid[i][j];
        }
    }

    cout << "!" << endl;
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) {
            cout << grid[i][j];
        }
        cout << endl;
    }
    cout.flush();

    return 0;
}