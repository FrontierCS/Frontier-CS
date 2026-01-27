#include <iostream>
#include <vector>
#include <deque>
#include <tuple>
#include <cmath>
#include <algorithm>

using namespace std;

int n;
int grid[55][55];
bool vis[55][55];

// Query returns 1 if palindromic path exists, 0 otherwise.
// Coordinates must satisfy x1 <= x2 and y1 <= y2.
int query(int r1, int c1, int r2, int c2) {
    // Ensure correct order
    if (r1 > r2 || c1 > c2) {
        return query(r2, c2, r1, c1);
    }
    cout << "? " << r1 << " " << c1 << " " << r2 << " " << c2 << endl;
    int res;
    cin >> res;
    if (res == -1) exit(0);
    return res;
}

// Check if a palindromic path exists between (r1, c1) and (r2, c2)
// assuming odd cells are flipped if flip_odd is true.
// Uses local BFS simulation.
bool exists_palindrome(int r1, int c1, int r2, int c2, bool flip_odd) {
    // Value accessor with flip logic
    auto get_val = [&](int r, int c) {
        int v = grid[r][c];
        if (((r + c) % 2 != 0) && flip_odd) v = 1 - v;
        return v;
    };

    if (get_val(r1, c1) != get_val(r2, c2)) return false;

    // Pairs of (u, v) in compressed format r*100+c
    vector<pair<int, int>> curr_level;
    curr_level.push_back({r1 * 100 + c1, r2 * 100 + c2});
    
    int dist = (r2 + c2) - (r1 + c1); 
    // We run for steps = (dist - 1) / 2
    
    for (int step = 0; step < (dist - 1) / 2; ++step) {
        vector<pair<int, int>> next_level;
        
        for (auto p : curr_level) {
            int u = p.first;
            int v = p.second;
            int ur = u / 100, uc = u % 100;
            int vr = v / 100, vc = v % 100;
            
            // Expand u: Right, Down
            int next_u[2][2] = {{ur + 1, uc}, {ur, uc + 1}};
            // Expand v: Up, Left
            int next_v[2][2] = {{vr - 1, vc}, {vr, vc - 1}};
            
            for (int i = 0; i < 2; ++i) {
                int nur = next_u[i][0];
                int nuc = next_u[i][1];
                if (nur > n || nuc > n) continue; 
                
                for (int j = 0; j < 2; ++j) {
                    int nvr = next_v[j][0];
                    int nvc = next_v[j][1];
                    if (nvr < 1 || nvc < 1) continue;
                    
                    // Optimization: Bounds check relative to each other?
                    // nur <= nvr && nuc <= nvc is implicitly maintained by steps
                    
                    if (get_val(nur, nuc) == get_val(nvr, nvc)) {
                        next_level.push_back({nur * 100 + nuc, nvr * 100 + nvc});
                    }
                }
            }
        }
        
        std::sort(next_level.begin(), next_level.end());
        next_level.erase(std::unique(next_level.begin(), next_level.end()), next_level.end());
        
        curr_level = next_level;
        if (curr_level.empty()) return false;
    }
    
    return !curr_level.empty();
}

void solve() {
    if (!(cin >> n)) return;
    
    for (int i = 1; i <= n; ++i)
        for (int j = 1; j <= n; ++j) {
            grid[i][j] = -1;
            vis[i][j] = false;
        }

    // Base cases
    grid[1][1] = 1;
    grid[n][n] = 0;
    
    //---------------------------------------------------------
    // Determine all Even-sum cells
    //---------------------------------------------------------
    deque<pair<int, int>> q;
    q.push_back({1, 1});
    vis[1][1] = true;
    if (!vis[n][n]) { // Should be false initially
        vis[n][n] = true;
        q.push_back({n, n});
    }

    // Direction vectors for distance 2 moves (including diagonals)
    vector<pair<int, int>> dirs = {
        {0, 2}, {0, -2}, {2, 0}, {-2, 0}, {1, 1}, {-1, -1}, {1, -1}, {-1, 1}
    };

    while(!q.empty()){
        auto [r, c] = q.front();
        q.pop_front();
        
        for (auto p : dirs) {
            int nr = r + p.first;
            int nc = c + p.second;
            
            if (nr >= 1 && nr <= n && nc >= 1 && nc <= n && !vis[nr][nc]) {
                // Determine if query is valid: must be ordered
                if ((r <= nr && c <= nc) || (nr <= r && nc <= c)) {
                    int res = query(r, c, nr, nc);
                    // If palindrome exists, values are same; else different
                    grid[nr][nc] = (res == 1 ? grid[r][c] : 1 - grid[r][c]);
                    vis[nr][nc] = true;
                    q.push_back({nr, nc});
                }
            }
        }
    }

    //---------------------------------------------------------
    // Determine all Odd-sum cells (Tentative with base 0)
    //---------------------------------------------------------
    // Reset queue for odd cells; vis remains true for even cells
    // Find a starting odd cell. (1, 2) is always valid.
    if (!vis[1][2]) {
        grid[1][2] = 0; 
        vis[1][2] = true;
        q.push_back({1, 2});
    }

    while(!q.empty()){
        auto [r, c] = q.front();
        q.pop_front();
        
        for (auto p : dirs) {
            int nr = r + p.first;
            int nc = c + p.second;
            
            if (nr >= 1 && nr <= n && nc >= 1 && nc <= n && !vis[nr][nc]) {
                if ((nr + nc) % 2 != 0) { // Should be odd sum
                    if ((r <= nr && c <= nc) || (nr <= r && nc <= c)) {
                        int res = query(r, c, nr, nc);
                        grid[nr][nc] = (res == 1 ? grid[r][c] : 1 - grid[r][c]);
                        vis[nr][nc] = true;
                        q.push_back({nr, nc});
                    }
                }
            }
        }
    }

    //---------------------------------------------------------
    // Find distinguishing query to fix Odd sum parities
    //---------------------------------------------------------
    int fx1=0, fy1=0, fx2=0, fy2=0;
    bool found_check = false;

    // Prioritize 'linear' pairs for speed if N >= 4
    if (n >= 4) {
        if (exists_palindrome(1, 1, 1, 4, false) != exists_palindrome(1, 1, 1, 4, true)) {
            fx1=1; fy1=1; fx2=1; fy2=4; found_check=true;
        } else if (exists_palindrome(1, 1, 4, 1, false) != exists_palindrome(1, 1, 4, 1, true)) {
            fx1=1; fy1=1; fx2=4; fy2=1; found_check=true;
        }
    }

    if (!found_check) {
        // Search pairs with odd distance >= 3
        for (int r2 = 1; r2 <= n; ++r2) {
            for (int c2 = 1; c2 <= n; ++c2) {
                int dist = (r2 + c2) - 2;
                if (dist < 3 || dist % 2 == 0) continue;
                // Only valid query pairs
                
                if (exists_palindrome(1, 1, r2, c2, false) != exists_palindrome(1, 1, r2, c2, true)) {
                    fx1 = 1; fy1 = 1; fx2 = r2; fy2 = c2;
                    found_check = true;
                    goto end_search;
                }
            }
        }
        end_search:;
    }

    bool do_flip = false;
    if (found_check) {
        int res = query(fx1, fy1, fx2, fy2);
        bool can0 = exists_palindrome(fx1, fy1, fx2, fy2, false);
        // If query (reality) differs from can0 (assumption X=0), then assumption is wrong
        if (res != can0) do_flip = true;
    } else {
        // This case should not happen given problem guarantees
        // If it did, maybe N=3 edge cases were poorly covered? 
        // But (1,1)->(2,3) is covered by loops.
    }

    // Output
    cout << "!" << endl;
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) {
            int v = grid[i][j];
            if ((i + j) % 2 != 0 && do_flip) v = 1 - v;
            cout << v;
        }
        cout << endl;
    }
}

int main() {
    solve();
    return 0;
}