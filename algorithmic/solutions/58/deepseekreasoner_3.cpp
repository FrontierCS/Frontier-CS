#include <bits/stdc++.h>
using namespace std;

const int MAXN = 301;
int grid[MAXN][MAXN]; // 1-indexed, initialized to 0

int main() {
    long long x;
    cin >> x;
    vector<int> bits;
    for (int b = 0; b <= 60; b++) {
        if ((x >> b) & 1) bits.push_back(b);
    }
    int m = bits.size();
    // sort bits in increasing order
    sort(bits.begin(), bits.end());
    int B = bits.back(); // maximum bit
    int C0 = 3 * B + 1;
    
    // initialize all to 0
    memset(grid, 0, sizeof(grid));
    
    // start column: rows 1..m are 1
    for (int i = 1; i <= m; i++) {
        grid[i][1] = 1;
    }
    // block further down in column 1
    if (m+1 < MAXN) grid[m+1][1] = 0;
    
    // for each route i (1-indexed)
    int max_leaf_row = 0;
    for (int idx = 0; idx < m; idx++) {
        int i = idx + 1;
        int b = bits[idx];
        // start of gadget at (i,2)
        grid[i][2] = 1;
        if (b == 0) {
            // horizontal corridor from (i,2) to (i, C0)
            for (int col = 2; col <= C0; col++) grid[i][col] = 1;
            max_leaf_row = max(max_leaf_row, i);
        } else {
            int r = i, c = 2;
            for (int t = 0; t < b; t++) {
                // set 3x3 block, all ones except center
                for (int dr = 0; dr < 3; dr++) {
                    for (int dc = 0; dc < 3; dc++) {
                        grid[r+dr][c+dc] = 1;
                    }
                }
                grid[r+1][c+1] = 0; // center blocked
                if (t < b-1) {
                    // connector to next block
                    grid[r+2][c+3] = 1;
                    grid[r+3][c+3] = 1;
                }
                r += 3;
                c += 3;
            }
            // after b blocks, exit is at (i+3b-1, 3b+1)
            int leaf_row = i + 3*b - 1;
            // horizontal corridor to column C0
            for (int col = 3*b+1; col <= C0; col++) {
                grid[leaf_row][col] = 1;
            }
            max_leaf_row = max(max_leaf_row, leaf_row);
        }
    }
    
    // merging tree
    int A_row, A_col;
    // first leaf
    if (bits[0] == 0) {
        A_row = 1;
    } else {
        A_row = 1 + 3*bits[0] - 1;
    }
    A_col = C0;
    
    for (int idx = 1; idx < m; idx++) {
        int i = idx + 1; // route index
        int b = bits[idx];
        int leaf_row = (b == 0) ? i : i + 3*b - 1;
        int M_col = C0 + i - 1;
        
        // merge cell
        grid[leaf_row][M_col] = 1;
        
        // path from accumulator to merge cell: right then down
        for (int col = A_col + 1; col <= M_col; col++) {
            grid[A_row][col] = 1;
        }
        for (int row = A_row + 1; row <= leaf_row; row++) {
            grid[row][M_col] = 1;
        }
        
        // path from leaf to merge cell: horizontal
        for (int col = C0 + 1; col <= M_col; col++) {
            grid[leaf_row][col] = 1;
        }
        
        // update accumulator
        A_row = leaf_row;
        A_col = M_col;
    }
    
    // determine n
    int n = max(max_leaf_row, C0 + m - 1) + 1;
    // ensure n <= 300 (by construction it should be)
    n = min(n, 300);
    
    // exit path from (A_row, A_col) to (n, n)
    for (int col = A_col + 1; col <= n; col++) {
        grid[A_row][col] = 1;
    }
    for (int row = A_row + 1; row <= n; row++) {
        grid[row][n] = 1;
    }
    grid[n][n] = 1;
    
    // output
    cout << n << endl;
    for (int i = 1; i <= n; i++) {
        for (int j = 1; j <= n; j++) {
            cout << grid[i][j] << (j < n ? ' ' : '\n');
        }
    }
    
    return 0;
}