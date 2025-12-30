#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>

using namespace std;

const int MAXN = 200;
int grid[MAXN][MAXN];

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    long long x;
    cin >> x;

    int n = 190;
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            grid[i][j] = 0;
        }
    }

    // Source path along the top row
    grid[0][0] = 1;
    for (int j = 1; j < 185; ++j) {
        grid[0][j] = 1;
    }

    // Collector path on the bottom-most part of the active grid
    int meeting_row = 65;
    for (int j = 0; j < 185; ++j) {
        grid[meeting_row][j] = 1;
    }
    
    // For each bit k, if it's 1, create 2^k paths and route them to the meeting row
    for (int k = 0; k < 62; ++k) {
        if ((x >> k) & 1) {
            // Start a path from (0, 3*k) which has 1 way
            int r = 1, c = 3 * k;
            grid[r][c] = 1;

            // k doubler gadgets
            for (int i = 0; i < k; ++i) {
                grid[r][c + 1] = 1;
                grid[r + 1][c] = 1;
                grid[r + 1][c + 1] = 1;
                r++;
                c++;
            }
            
            // Route to the meeting row
            for (int i = r; i < meeting_row; ++i) {
                grid[i][c] = 1;
            }
        }
    }

    // Final path to destination (n-1, n-1)
    for (int i = meeting_row; i < n; ++i) {
        grid[i][184] = 1;
    }
     for (int j = 184; j < n; ++j) {
        grid[n-1][j] = 1;
    }

    cout << n << endl;
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            cout << grid[i][j] << (j == n - 1 ? "" : " ");
        }
        cout << endl;
    }

    return 0;
}