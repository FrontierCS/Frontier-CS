#include <iostream>
#include <vector>
#include <cmath>

using namespace std;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    long long x;
    cin >> x;

    int n = 200;
    vector<vector<int>> grid(n + 1, vector<int>(n + 1, 0));

    // 1. Path Generators for 2^k
    // A structure along the main diagonal creates path counts of 2^k.
    // Let dp[i][j] be paths from (1,1) to (i,j).
    // With grid[i][i-1]=1 and grid[i-1][i]=1, dp[i][i] roughly doubles.
    // Specifically, dp[k+1][k+1] will have 2^k paths.
    grid[1][1] = 1;
    for (int i = 2; i <= 130; ++i) {
        grid[i][i-1] = 1;
        grid[i-1][i] = 1;
    }

    // 2. Collector Path
    // We use row 150 as a collector.
    int collector_row = 150;

    // 3. Selective Tapping
    // For each set bit b_k in x, connect generator S_k=(k+1,k+1) to the collector.
    int last_col = 0;
    for (int k = 0; k < 63; ++k) {
        if ((x >> k) & 1) {
            // S_k = (k+1, k+1) has 2^k paths.
            // Route from S_k to (collector_row, k+1)
            int start_r = k + 1;
            int start_c = k + 1;
            for (int i = start_r; i <= collector_row; ++i) {
                grid[i][start_c] = 1;
            }
            last_col = max(last_col, start_c);
        }
    }

    // Make the collector row a continuous path up to the last tapped column.
    for (int j = 1; j <= last_col; ++j) {
        grid[collector_row][j] = 1;
    }

    // 4. Final Route
    // Connect the collector's end to the grid destination (n,n).
    if (last_col > 0) {
        for (int j = last_col; j < n; ++j) {
            grid[collector_row][j + 1] = 1;
        }
        for (int i = collector_row; i < n; ++i) {
            grid[i + 1][n] = 1;
        }
    } else { // Handle x=0 case if it were possible, or small x not needing taps
        if (x==1) { // A direct path for x=1
            for (int i=1; i<n; ++i) grid[i][i+1]=0; // break the doublers
            for (int i = 1; i < n; i++) grid[i+1][i] = 1;
            for (int i = 1; i < n; i++) grid[n][i+1] = 1;
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