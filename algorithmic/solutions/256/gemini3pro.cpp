#include <iostream>
#include <vector>
#include <queue>
#include <algorithm>
#include <cstring>

using namespace std;

int n;
int evens[55][55];
int odds[55][55];
int memo[55][55][55][55];
int target_evens[55][55];
int target_odds[55][55];

// Query function: returns 1 if a palindromic path exists, 0 otherwise.
int query(int r1, int c1, int r2, int c2) {
    cout << "? " << r1 << " " << c1 << " " << r2 << " " << c2 << endl;
    int ans;
    cin >> ans;
    if (ans == -1) exit(0);
    return ans;
}

// Fill relative values for a component (Even sum or Odd sum cells)
// type 0 for evens (starting at 1,1 with val 1), 1 for odds (starting at 1,2 with val 0 tentative)
void fill_component(int start_r, int start_c, int type) {
    int (&arr)[55][55] = (type == 0 ? evens : odds);
    for(int i=1; i<=n; ++i) for(int j=1; j<=n; ++j) arr[i][j] = -1;
    
    arr[start_r][start_c] = (type == 0 ? 1 : 0);
    
    queue<pair<int, int>> q;
    q.push({start_r, start_c});
    
    // Moves to reach cells at distance 2
    int ddr[] = {1, 1, 2, 0, -1, -1, -2, 0};
    int ddc[] = {1, -1, 0, 2, 1, -1, 0, -2};
    
    while(!q.empty()){
        auto [r, c] = q.front();
        q.pop();
        
        for(int i=0; i<8; ++i){
            int nr = r + ddr[i];
            int nc = c + ddc[i];
            
            if(nr >= 1 && nr <= n && nc >= 1 && nc <= n){
                if(arr[nr][nc] == -1){
                    int q_res = -1;
                    // Ensure the query is valid (x1<=x2 and y1<=y2)
                    if(r <= nr && c <= nc) {
                        q_res = query(r, c, nr, nc);
                    } else if (nr <= r && nc <= c) {
                        q_res = query(nr, nc, r, c);
                    }
                    
                    if(q_res != -1) {
                        if(q_res == 1) arr[nr][nc] = arr[r][c];
                        else arr[nr][nc] = 1 - arr[r][c];
                        q.push({nr, nc});
                    }
                }
            }
        }
    }
}

// Checks if there exists a palindrome path from (r1, c1) to (r2, c2)
// using the current tentative values in target_evens and target_odds.
bool check_pal(int r1, int c1, int r2, int c2) {
    if(r1 == r2 && c1 == c2) return true;
    
    // Base case: distance 1 (adjacent)
    if (r1 + c1 + 1 == r2 + c2) {
        int v1 = ((r1+c1)%2 == 0) ? target_evens[r1][c1] : target_odds[r1][c1];
        int v2 = ((r2+c2)%2 == 0) ? target_evens[r2][c2] : target_odds[r2][c2];
        return v1 == v2;
    }
    
    if(memo[r1][c1][r2][c2] != -1) return memo[r1][c1][r2][c2];
    
    int v1 = ((r1+c1)%2 == 0) ? target_evens[r1][c1] : target_odds[r1][c1];
    int v2 = ((r2+c2)%2 == 0) ? target_evens[r2][c2] : target_odds[r2][c2];
    
    if(v1 != v2) return memo[r1][c1][r2][c2] = 0;
    
    bool possible = false;
    // Try to move inward from both ends
    int next_starts[2][2] = {{r1+1, c1}, {r1, c1+1}};
    int next_ends[2][2] = {{r2-1, c2}, {r2, c2-1}};
    
    for(int i=0; i<2; ++i) {
        int nr1 = next_starts[i][0];
        int nc1 = next_starts[i][1];
        if(nr1 > r2 || nc1 > c2) continue;
        
        for(int j=0; j<2; ++j) {
            int nr2 = next_ends[j][0];
            int nc2 = next_ends[j][1];
            
            if(nr2 < nr1 || nc2 < nc1) continue;
            
            if(nr1 <= n && nc1 <= n && nr2 >= 1 && nc2 >= 1) {
                if(check_pal(nr1, nc1, nr2, nc2)) {
                    possible = true;
                    break;
                }
            }
        }
        if(possible) break;
    }
    
    return memo[r1][c1][r2][c2] = possible;
}

int main() {
    // Basic setup, no syncing to allow mixing C++ IO if needed, but here we just use cin/cout
    // Do not untie cin from cout for interactive safety or use endl.
    
    cin >> n;
    
    // 1. Determine all cells with Even sum of coordinates (relative to (1,1)=1)
    fill_component(1, 1, 0);
    
    // 2. Determine all cells with Odd sum of coordinates (relative to (1,2)=0 tentative)
    fill_component(1, 2, 1);
    
    // 3. Find a query that distinguishes whether the Odd component assumption was correct or inverted
    for(int i=1; i<=n; ++i) for(int j=1; j<=n; ++j) target_evens[i][j] = evens[i][j];
    
    int found_base = 0; // 0 means assumption valid, 1 means inverted
    
    vector<pair<int, int>> odd_cells;
    for(int i=1; i<=n; ++i) {
        for(int j=1; j<=n; ++j) {
            if((i+j)%2 != 0) {
                odd_cells.push_back({i, j});
            }
        }
    }
    
    // Sort by distance to check closer/cheaper paths first
    sort(odd_cells.begin(), odd_cells.end(), [](pair<int, int> a, pair<int, int> b){
        return (a.first + a.second) < (b.first + b.second);
    });
    
    for(auto p : odd_cells) {
        int r = p.first;
        int c = p.second;
        // Minimum distance must be >= 2 (sum diff >= 2). (1,1) sum is 2. Target sum >= 4.
        if(r+c < 4) continue;
        
        // Try Base 0 (assumption correct)
        for(int i=1; i<=n; ++i) for(int j=1; j<=n; ++j) target_odds[i][j] = odds[i][j];
        memset(memo, -1, sizeof(memo));
        bool res0 = check_pal(1, 1, r, c);
        
        // Try Base 1 (assumption inverted)
        for(int i=1; i<=n; ++i) for(int j=1; j<=n; ++j) target_odds[i][j] = 1 - odds[i][j];
        memset(memo, -1, sizeof(memo));
        bool res1 = check_pal(1, 1, r, c);
        
        // If the query yields different results for the two hypotheses, use it
        if(res0 != res1) {
            int ans = query(1, 1, r, c);
            if(ans == res0) found_base = 0;
            else found_base = 1;
            break;
        }
    }
    
    cout << "!" << endl;
    for(int i=1; i<=n; ++i) {
        for(int j=1; j<=n; ++j) {
            if((i+j)%2 == 0) cout << evens[i][j];
            else cout << (found_base == 0 ? odds[i][j] : 1 - odds[i][j]);
        }
        cout << endl;
    }
    
    return 0;
}