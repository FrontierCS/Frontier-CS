#include <iostream>
#include <vector>
#include <queue>
#include <cmath>
#include <algorithm>
#include <cstring>

using namespace std;

int n;
int grid[55][55];
bool vis[55][55];

struct Point {
    int r, c;
};

// Memoization for is_palindrome_path
int memo[55][55][55][55];
int current_check_val_O; // Adjustment for Set O (0 means keep as is, 1 means flip)

// Interactive query
int ask(Point p1, Point p2) {
    if (p1.r + p1.c > p2.r + p2.c) swap(p1, p2);
    cout << "? " << p1.r << " " << p1.c << " " << p2.r << " " << p2.c << endl;
    int res;
    cin >> res;
    if (res == -1) exit(0);
    return res;
}

// Get grid value considering the potential flip for Set O
int get_val(int r, int c) {
    int v = grid[r][c];
    if ((r + c) % 2 != 0) { // Set O
        return (v + current_check_val_O) % 2;
    }
    return v;
}

// DP to check if a palindromic path exists between (r1, c1) and (r2, c2)
// given the current grid values.
bool solve_pal(int r1, int c1, int r2, int c2) {
    if (memo[r1][c1][r2][c2] != -1) return memo[r1][c1][r2][c2];

    int v1 = get_val(r1, c1);
    int v2 = get_val(r2, c2);

    if (v1 != v2) return memo[r1][c1][r2][c2] = 0;

    int dist = abs(r1 - r2) + abs(c1 - c2);
    if (dist == 0) return memo[r1][c1][r2][c2] = 1;
    if (dist == 1) return memo[r1][c1][r2][c2] = 1;

    bool possible = false;
    
    // Try p1 -> right
    if (c1 + 1 <= c2) {
        // p2 <- left
        if (c2 - 1 >= c1 + 1 && solve_pal(r1, c1 + 1, r2, c2 - 1)) possible = true;
        // p2 <- up
        if (!possible && r2 - 1 >= r1 && solve_pal(r1, c1 + 1, r2 - 1, c2)) possible = true;
    }
    
    if (!possible && r1 + 1 <= r2) {
        // p2 <- left
        if (c2 - 1 >= c1 && solve_pal(r1 + 1, c1, r2, c2 - 1)) possible = true;
        // p2 <- up
        if (!possible && r2 - 1 >= r1 + 1 && solve_pal(r1 + 1, c1, r2 - 1, c2)) possible = true;
    }
    
    return memo[r1][c1][r2][c2] = possible;
}

// Helper to check what solve_pal returns with a specific flip for Set O
bool check_existence(Point p1, Point p2, int flipO) {
    current_check_val_O = flipO;
    memset(memo, -1, sizeof(memo));
    if (p1.r + p1.c > p2.r + p2.c) swap(p1, p2);
    return solve_pal(p1.r, p1.c, p2.r, p2.c);
}

int main() {
    ios::sync_with_stdio(false); // cin/cout speed, note: interactive needs flush
    cin.tie(NULL);

    cin >> n;

    for (int i = 1; i <= n; ++i)
        for (int j = 1; j <= n; ++j)
            grid[i][j] = -1;

    // Set E construction
    grid[1][1] = 1;
    // Set O construction
    grid[1][2] = 0; // Tentative

    queue<Point> q;
    
    // Determine Set E
    q.push({1, 1});
    memset(vis, 0, sizeof(vis));
    vis[1][1] = true;
    vis[n][n] = false; // reset for uniform treatment in BFS, though we know (n,n)=0

    // Neighbors at Manh dist 2
    vector<Point> d2_moves;
    d2_moves.push_back({-2, 0}); d2_moves.push_back({2, 0});
    d2_moves.push_back({0, -2}); d2_moves.push_back({0, 2});
    d2_moves.push_back({-1, -1}); d2_moves.push_back({1, 1});
    d2_moves.push_back({-1, 1}); d2_moves.push_back({1, -1});

    while(!q.empty()){
        Point u = q.front(); q.pop();
        for(auto mv : d2_moves){
            Point v = {u.r + mv.r, u.c + mv.c};
            if(v.r >= 1 && v.r <= n && v.c >= 1 && v.c <= n){
                // Check if Set E
                if((v.r + v.c) % 2 == 0 && !vis[v.r][v.c]){
                    Point p1 = u, p2 = v;
                    if(p1.r + p1.c > p2.r + p2.c) swap(p1, p2);
                    if(p1.r <= p2.r && p1.c <= p2.c && p1.r+p1.c+2 <= p2.r+p2.c){
                        int ans = ask(p1, p2);
                        grid[v.r][v.c] = (ans == 1 ? grid[u.r][u.c] : 1 - grid[u.r][u.c]);
                        vis[v.r][v.c] = true;
                        q.push(v);
                    }
                }
            }
        }
    }
    
    // Determine Set O
    q.push({1, 2});
    vis[1][2] = true;
    
    while(!q.empty()){
        Point u = q.front(); q.pop();
        for(auto mv : d2_moves){
            Point v = {u.r + mv.r, u.c + mv.c};
            if(v.r >= 1 && v.r <= n && v.c >= 1 && v.c <= n){
                // Check if Set O
                if((v.r + v.c) % 2 != 0 && !vis[v.r][v.c]){
                    Point p1 = u, p2 = v;
                    if(p1.r + p1.c > p2.r + p2.c) swap(p1, p2);
                    if(p1.r <= p2.r && p1.c <= p2.c && p1.r+p1.c+2 <= p2.r+p2.c){
                        int ans = ask(p1, p2);
                        grid[v.r][v.c] = (ans == 1 ? grid[u.r][u.c] : 1 - grid[u.r][u.c]);
                        vis[v.r][v.c] = true;
                        q.push(v);
                    }
                }
            }
        }
    }
    
    // Find separating query between Set E and Set O
    int final_flip = 0;
    bool determined = false;
    
    // Iterate to find a decisive query
    for(int r1=1; r1<=n && !determined; ++r1){
        for(int c1=1; c1<=n && !determined; ++c1){
            if((r1+c1)%2 != 0) continue; // Must be E
            
            // Try neighbors at dist 3
            int moves[4][2] = {{1, 2}, {2, 1}, {0, 3}, {3, 0}}; 
            
            for(int k=0; k<4; ++k){
                int r2 = r1 + moves[k][0];
                int c2 = c1 + moves[k][1];
                if(r2 <= n && c2 <= n){
                    // This links E to O
                    bool exists0 = check_existence({r1, c1}, {r2, c2}, 0); 
                    bool exists1 = check_existence({r1, c1}, {r2, c2}, 1);
                    
                    if(exists0 != exists1){
                        // Query is decisive
                        int actual = ask({r1, c1}, {r2, c2});
                        if(actual == 1){
                            if(exists0) final_flip = 0;
                            else final_flip = 1;
                        } else {
                            if(exists0) final_flip = 1;
                            else final_flip = 0;
                        }
                        determined = true;
                        break;
                    }
                }
            }
        }
    }
    
    cout << "!" << endl;
    for(int i=1; i<=n; ++i){
        for(int j=1; j<=n; ++j){
            int val = grid[i][j];
            if((i+j)%2 != 0 && final_flip) val = 1 - val;
            cout << val;
        }
        cout << endl;
    }
    
    return 0;
}