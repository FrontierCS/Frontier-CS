#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

int main() {
    long long x;
    if (!(cin >> x)) return 0;

    int n = 300; // Using max size to be safe and simple
    // The grid is 1-indexed conceptually for problem, 0-indexed for C++ vector
    // We will use 1-based indexing for logic and output.
    
    // Grid:
    vector<vector<int>> grid(n + 1, vector<int>(n + 1, 0));

    // Identify bits
    vector<int> bits;
    for (int i = 0; i < 62; ++i) {
        if ((x >> i) & 1) {
            bits.push_back(i);
        }
    }
    
    // We need to generate powers up to highest needed bit.
    // If x has bit k set, we need 2^k.
    // Max bit index
    int max_bit = 0;
    if (!bits.empty()) max_bit = bits.back();
    
    // Spaced doubling structure
    // Node for 2^k starts at (2k+1, 2k+1).
    // We generate up to 2^(max_bit).
    // Doubler k converts 2^k at (2k+1, 2k+1) to 2^(k+1) at (2k+3, 2k+3).
    // We need doublers for k = 0 to max_bit - 1.
    
    // Initialize 2^0 at (1,1)
    grid[1][1] = 1;

    for (int k = 0; k < max_bit; ++k) {
        int r = 2 * k + 1;
        int c = 2 * k + 1;
        
        // Path 1 (Top): (r, c) -> (r, c+1) -> (r, c+2) -> (r+1, c+2) -> (r+2, c+2)
        grid[r][c+1] = 1;
        grid[r][c+2] = 1;
        grid[r+1][c+2] = 1;
        grid[r+2][c+2] = 1;
        
        // Path 2 (Bot): (r, c) -> (r+1, c) -> (r+2, c) -> (r+2, c+1) -> (r+2, c+2)
        grid[r+1][c] = 1;
        grid[r+2][c] = 1;
        grid[r+2][c+1] = 1;
        grid[r+2][c+2] = 1;
        
        // Ensure start and end are 1 (redundant but safe)
        grid[r][c] = 1;
        grid[r+2][c+2] = 1;
    }
    
    // If max_bit is 0 (x=1), loop doesn't run, only (1,1) is 1. Correct.

    // Highways
    // Bit k corresponds to node (2k+1, 2k+1).
    // However, in our doubler, the top path extends along row 2k+1.
    // Specifically, (2k+1, 2k+1) -> (2k+1, 2k+2) -> (2k+1, 2k+3) -> down.
    // Actually the logic above uses c+2 = 2k+3.
    // So row 2k+1 is used up to col 2k+3.
    // We can tap by continuing row 2k+1 to the right.
    
    // Assign columns: increasing bit index -> decreasing column index to avoid crossing.
    // Start columns from n backwards.
    // bit k uses column C_k.
    // C_k needs to be distinct.
    
    // Adjust n if we want better score, but 300 is guaranteed valid.
    // Let's stick to n=300 for simplicity as it fits constraints easily.
    
    int current_col = n;
    
    // Process bits
    // We iterate k in bits.
    // For each k, we construct highway.
    // Since we need C_k < C_m for k > m (wait, previous logic was C_m < C_k for m > k).
    // Let's re-verify crossing logic.
    // Row index increases with k.
    // Row m > Row k.
    // Vertical k is at C_k.
    // Horizontal m goes to C_m.
    // Vertical k crosses Horizontal m?
    // Vertical k spans rows k..n. Horizontal m is at row m.
    // Since m > k, yes they cross row-wise.
    // To avoid intersection, Horizontal m must stop before Vertical k.
    // So C_m < C_k.
    // So larger bits get smaller columns.
    
    // We sort bits descending to assign columns?
    // No, bits is sorted ascending.
    // k increases -> C_k decreases.
    // So for k=0 (smallest), C_0 is largest (n).
    
    for (int k : bits) {
        int r = 2 * k + 1;
        int col = n - k; // Simple assignment: bit 0 -> 300, bit 1 -> 299...
        
        // Horizontal path from end of doubler-top-segment to col.
        // Doubler top segment ends at col 2k+3.
        // So we fill 1s from 2k+4 to col.
        // Also ensure connection from 2k+3.
        // The cell (2k+1, 2k+3) is already 1.
        // So fill (2k+1, c) for c = 2k+4 to col.
        
        // Wait, if k=max_bit, the doubler loop didn't create the path for k!
        // The loop runs up to max_bit - 1.
        // So for k=max_bit, we have node (2k+1, 2k+1) with value 2^k, but no extending paths.
        // So we start highway from (2k+1, 2k+1).
        // So fill (2k+1, c) from 2k+2 to col.
        
        int start_c = (k == max_bit) ? (2 * k + 2) : (2 * k + 4);
        
        for (int c = start_c; c <= col; ++c) {
            grid[r][c] = 1;
        }
        
        // For k < max_bit, we also need to ensure continuity if gap is small?
        // Doubler k sets (2k+1, 2k+3).
        // If start_c = 2k+4, it connects.
        // For k = max_bit, start_c = 2k+2.
        // (2k+1, 2k+1) is set. (2k+1, 2k+2) set by loop.
        
        // Vertical path from (r, col) to (n, col).
        for (int row = r; row <= n; ++row) {
            grid[row][col] = 1;
        }
    }
    
    // Collector at bottom row n.
    // We need to connect all used columns to (n, n).
    // Used columns are n, n-1, ... n-max_bit.
    // The range is [n - max_bit, n].
    for (int c = n - max_bit; c <= n; ++c) {
        grid[n][c] = 1;
    }
    
    // Output
    cout << n << endl;
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) {
            cout << grid[i][j] << (j == n ? "" : " ");
        }
        cout << endl;
    }

    return 0;
}