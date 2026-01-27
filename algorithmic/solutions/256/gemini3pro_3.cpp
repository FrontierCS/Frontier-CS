#include <iostream>
#include <vector>
#include <queue>
#include <cmath>
#include <tuple>
#include <algorithm>

using namespace std;

int n;
int grid_val[55][55]; // -1 unknown, 0/1 known (for Even cells)
int odd_rel[55][55];  // -1 unknown, 0/1 relative value (for Odd cells)
bool visited_even[55][55];
bool visited_odd[55][55];

// Function to perform query
int query(int r1, int c1, int r2, int c2) {
    // Ensure r1 <= r2 and y1 <= y2 if on same row
    if (r1 > r2) { swap(r1, r2); swap(c1, c2); }
    else if (r1 == r2 && c1 > c2) { swap(c1, c2); }
    
    // The problem requires x1 <= x2 and y1 <= y2. 
    // However, if we have points A and B, we can query A, B or B, A 
    // as long as one is reachable from other to the right/down.
    // If neither is reachable from other, query is invalid.
    // Our logic generates neighbors with Manhattan dist, but we must filter for reachability.
    // Actually, dist 2 neighbors in grid could be e.g. (r, c+2), (r+1, c+1), (r+2, c).
    // All these satisfy x1<=x2, y1<=y2.
    // The "reverse" neighbors (e.g. r-2) means we swap order.
    
    cout << "? " << r1 << " " << c1 << " " << r2 << " " << c2 << endl;
    int res;
    cin >> res;
    if (res == -1) exit(0);
    return res;
}

bool is_valid(int r, int c) {
    return r >= 1 && r <= n && c >= 1 && c <= n;
}

// Get valid neighbors at Manhattan distance 2 that allow a valid query
vector<pair<int,int>> get_dist2_neighbors(int r, int c) {
    vector<pair<int,int>> res;
    // Possible relative positions (dx, dy) with |dx|+|dy|=2
    int dr[] = {0, 0, 2, -2, 1, 1, -1, -1};
    int dc[] = {2, -2, 0, 0, 1, -1, 1, -1};
    for(int i=0; i<8; ++i) {
        int nr = r + dr[i];
        int nc = c + dc[i];
        if (is_valid(nr, nc)) {
            // Check reachability for query validity
            // Either (r,c) -> (nr,nc) or (nr,nc) -> (r,c) must be valid (right/down moves)
            if ((nr >= r && nc >= c) || (r >= nr && c >= nc)) {
                res.push_back({nr, nc});
            }
        }
    }
    return res;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    if (!(cin >> n)) return 0;

    for(int i=1; i<=n; ++i) 
        for(int j=1; j<=n; ++j) {
            grid_val[i][j] = -1;
            odd_rel[i][j] = -1;
        }

    // Even cells: (r+c) % 2 == (1+1) % 2 == 0
    // Odd cells: (r+c) % 2 == 1
    
    // Step 1: Solve Even cells
    grid_val[1][1] = 1;
    grid_val[n][n] = 0;
    
    queue<pair<int,int>> q_even;
    q_even.push({1, 1});
    visited_even[1][1] = true;
    
    // (n,n) is also even since n is odd (odd+odd=even)
    // If not visited (n>1), add to queue
    if (!visited_even[n][n]) {
        q_even.push({n, n});
        visited_even[n][n] = true;
    }

    while(!q_even.empty()) {
        auto [r, c] = q_even.front();
        q_even.pop();

        vector<pair<int,int>> neighbors = get_dist2_neighbors(r, c);
        for(auto [nr, nc] : neighbors) {
            // Must be Even
            if ( ((nr + nc) % 2) != 0 ) continue; 

            if (!visited_even[nr][nc]) {
                int res = query(r, c, nr, nc);
                // For dist 2, res=1 <=> val(u) == val(v)
                if (res == 1) grid_val[nr][nc] = grid_val[r][c];
                else grid_val[nr][nc] = 1 - grid_val[r][c];
                
                visited_even[nr][nc] = true;
                q_even.push({nr, nc});
            }
        }
    }

    // Step 2: Solve Odd cells relative values
    // Find an odd cell to start, e.g., (1,2)
    int start_odd_r = 1, start_odd_c = 2;
    if (!is_valid(start_odd_r, start_odd_c)) {
        // n=1? But constraints n>=3.
        // n=3 => (1,2) valid.
    }
    odd_rel[start_odd_r][start_odd_c] = 0; // Reference 0
    
    queue<pair<int,int>> q_odd;
    q_odd.push({start_odd_r, start_odd_c});
    visited_odd[start_odd_r][start_odd_c] = true;

    while(!q_odd.empty()) {
        auto [r, c] = q_odd.front();
        q_odd.pop();

        vector<pair<int,int>> neighbors = get_dist2_neighbors(r, c);
        for(auto [nr, nc] : neighbors) {
            if ( ((nr + nc) % 2) == 0 ) continue; // Skip Even

            if (!visited_odd[nr][nc]) {
                int res = query(r, c, nr, nc);
                if (res == 1) odd_rel[nr][nc] = odd_rel[r][c];
                else odd_rel[nr][nc] = 1 - odd_rel[r][c];

                visited_odd[nr][nc] = true;
                q_odd.push({nr, nc});
            }
        }
    }

    // Step 3: Determine flip for Odd cells
    int final_flip = -1;
    
    // We search for a query between an Even cell and an Odd cell with distance 3
    // Such that the query result allows distinguishing between flip=0 and flip=1.
    
    for(int r1=1; r1<=n && final_flip == -1; ++r1) {
        for(int c1=1; c1<=n && final_flip == -1; ++c1) {
            if ((r1+c1)%2 != 0) continue; // Must be Even

            // Neighbors with dist 3: (r1, c1) -> (r2, c2)
            // Offsets (0,3), (1,2), (2,1), (3,0)
            int drs[] = {0, 1, 2, 3};
            int dcs[] = {3, 2, 1, 0};

            for(int i=0; i<4; ++i) {
                int r2 = r1 + drs[i];
                int c2 = c1 + dcs[i];
                if (!is_valid(r2, c2)) continue;
                
                // Paths u -> m1 -> m2 -> v
                // u=(r1,c1) Even, v=(r2,c2) Odd
                // m1 is dist 1 from u -> Odd
                // m2 is dist 2 from u -> Even
                
                bool possible0 = false;
                bool possible1 = false;
                
                vector<pair<int,int>> m1s;
                if(is_valid(r1+1, c1)) m1s.push_back({r1+1, c1});
                if(is_valid(r1, c1+1)) m1s.push_back({r1, c1+1});
                
                vector<pair<int,int>> m2s;
                if(is_valid(r2-1, c2)) m2s.push_back({r2-1, c2});
                if(is_valid(r2, c2-1)) m2s.push_back({r2, c2-1});
                
                for(auto p1 : m1s) {
                    for(auto p2 : m2s) {
                        // Check if p1 -> p2 is valid move
                        if (abs(p1.first - p2.first) + abs(p1.second - p2.second) == 1) {
                            // Palindrome conditions:
                            // 1. val(u) == val(v)
                            // 2. val(p1) == val(p2)
                            
                            // Values:
                            // val(u) and val(p2) are known (Even)
                            // val(v) and val(p1) depend on flip (Odd)
                            
                            int u_val = grid_val[r1][c1];
                            int p2_val = grid_val[p2.first][p2.second];
                            
                            int v_rel = odd_rel[r2][c2];
                            int p1_rel = odd_rel[p1.first][p1.second];
                            
                            // If flip = 0: val(v)=v_rel, val(p1)=p1_rel
                            if (u_val == v_rel && p1_rel == p2_val) possible0 = true;
                            
                            // If flip = 1: val(v)=1-v_rel, val(p1)=1-p1_rel
                            if (u_val == (1-v_rel) && (1-p1_rel) == p2_val) possible1 = true;
                        }
                    }
                }
                
                if (possible0 != possible1) {
                    int res = query(r1, c1, r2, c2);
                    if (res == 1) {
                        final_flip = possible0 ? 0 : 1;
                    } else {
                        final_flip = possible0 ? 1 : 0;
                    }
                    goto done_disc;
                }
            }
        }
    }
    
    done_disc:;
    
    cout << "!" << endl;
    for(int i=1; i<=n; ++i) {
        for(int j=1; j<=n; ++j) {
            if (grid_val[i][j] != -1) cout << grid_val[i][j];
            else cout << (odd_rel[i][j] ^ final_flip);
        }
        cout << endl;
    }
    
    return 0;
}