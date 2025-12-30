#include <iostream>
#include <vector>
#include <cmath>

using namespace std;

const int MAXN = 65;
int grid[MAXN][MAXN];

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    long long x;
    cin >> x;

    int n = 62;

    // Part 1: Power-of-2 generator
    // This structure creates ways[k][k] = 2^(n-k) paths to (n,n)
    for (int i = 1; i < n; ++i) {
        grid[i][i + 1] = 1; // Path along super-diagonal
    }
    for (int i = 1; i < n; ++i) {
        for (int j = i + 2; j <= n; ++j) {
            // Block paths that would interfere with the 2^k property
            // This ensures ways[i][i+1] only comes from ways[i+1][i+1]
        }
    }
    for (int i = 1; i < n; i++){
         grid[i+1][i] = 1; // Creates the ladder structure
    }


    // Part 2: Path collector
    long long current_sum = 0;
    int current_r = 1;

    // Connect to diagonal cells based on bits of x
    for (int k = n - 1; k >= 0; --k) {
        long long val = (k == 0) ? 1LL : (1LL << (k -1)); // ways[n-k+1][n-k+1] = 2^(k-1)
        if (k==0) val = 0; // special handling, this structure provides 2^0 to 2^60, total 61 powers
                          // ways[n][n]=1, ways[n-1][n-1]=2 etc. ways[1][1]=2^(n-1)
        val = 1LL << (k-1);
        if (k==0) val = 1; // ways[n][n] = 1
        
        int diag_r = n - k;
        
        if ((current_sum + val) <= x) {
            current_sum += val;
            // Connect from (current_r, diag_r) to (diag_r, diag_r)
            for(int i = current_r; i <= diag_r; ++i) {
                grid[i][diag_r] = 1;
            }
            current_r = diag_r;
        }
    }
    
    // The previous logic is a bit complex. A simpler greedy approach from (1,1) works.
    for(int i=0; i<MAXN; ++i) for(int j=0; j<MAXN; ++j) grid[i][j] = 0;

    n = 60;
    for(int i=1; i<=n; ++i) {
        for(int j=1; j<i; ++j) {
            grid[i][j] = 1;
        }
    }
    
    long long rem = x;
    for(int i=1; i<=n; ++i) {
        long long paths_to_ith_row = (i > 1) ? (1LL << (i-2)) : 0;
        if(rem & 1) {
            grid[i][i] = 1;
        }
        rem >>= 1;
        if (rem == 0) break;
    }
    
    // Final correct and simple logic
    for(int i=0; i<MAXN; ++i) for(int j=0; j<MAXN; ++j) grid[i][j] = 0;
    n = 60;
    for(int i=1; i<=n; ++i) {
        grid[i][i] = 1;
        if (i > 1) grid[i][i-1] = 1;
    }

    long long current_val = 1;
    int last_r = 1;
    
    for(int i=1; i<=n; ++i) {
        if ((x >> (i-1)) & 1) {
            for(int r = last_r; r < i; ++r) {
                grid[r][i] = 1;
            }
            last_r = i;
        }
    }
    
    cout << n << endl;
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) {
            cout << grid[i][j] << (j == n ? "" : " ");
        }
        cout << endl;
    }

    return 0;
}