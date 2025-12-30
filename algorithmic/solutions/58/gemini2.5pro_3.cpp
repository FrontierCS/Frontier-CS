#include <iostream>
#include <vector>
#include <numeric>

using namespace std;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    long long x;
    cin >> x;

    int n = 64;
    vector<vector<int>> grid(n, vector<int>(n, 0));

    // Power-of-two path generators
    // Paths from (1,1) to (k,k) will be 2^(k-1)
    grid[1][1] = 1;
    for (int i = 2; i <= 62; ++i) {
        grid[i][i] = 1;
        grid[i-1][i] = 1;
        grid[i][i-1] = 1;
    }

    long long rem = x;
    int last_r = 63;
    int last_c = 63;

    // Connect power-of-two paths to a collector path
    for (int i = 60; i >= 0; --i) {
        long long ways = 1LL << i;
        if (rem >= ways) {
            rem -= ways;
            // Connect (i+1, i+1) to (last_r, last_c - 1)
            for (int j = i + 1; j < last_c; ++j) {
                grid[i + 1][j] = 1;
            }
            for (int j = i + 1; j < last_r; ++j) {
                grid[j][last_c - 1] = 1;
            }
            last_c--;
        }
    }
    
    // Connect (1,1) to handle the remaining part (typically 1 if x is odd)
    for (int j = 1; j < last_c; ++j) {
        grid[1][j] = 1;
    }
    for (int j = 1; j < last_r; ++j) {
        grid[j][last_c - 1] = 1;
    }
    
    // Final sink
    grid[n - 1][n - 1] = 1;

    cout << n - 1 << endl;
    for (int i = 1; i < n; ++i) {
        for (int j = 1; j < n; ++j) {
            cout << grid[i][j] << (j == n - 1 ? "" : " ");
        }
        cout << endl;
    }

    return 0;
}