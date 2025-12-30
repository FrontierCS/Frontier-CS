#include <iostream>
#include <vector>

using namespace std;

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    long long x;
    if (!(cin >> x)) return 0;

    // Calculate L = floor(log2(x)), the index of the highest set bit.
    // For x=1, L=0.
    int L = 0;
    long long temp = x;
    while (temp >>= 1) L++;
    
    // Set grid size n. 
    // We need enough space for the spine and a buffer column before the collector column.
    // n = L + 3 is sufficient to avoid conflicts for bits L-1 and L.
    // Example: x=1 (L=0) -> n=3. x=3 (L=1) -> n=4.
    int n = L + 3;
    
    // Initialize grid with 0s. Use 1-based indexing for convenience.
    vector<vector<int>> grid(n + 1, vector<int>(n + 1, 0));

    // Base case: start position
    grid[1][1] = 1;

    // Construct the "Spine" on the main diagonal.
    // This structure doubles the number of paths at each step.
    // At grid[k][k], the number of paths is 2^(k-1).
    // Loop runs L times to build paths up to row L+1.
    // After loop, grid[L+1][L+1] receives 2^L paths.
    for (int i = 1; i <= L; ++i) {
        grid[i][i] = 1;
        grid[i][i+1] = 1;
        grid[i+1][i] = 1;
        grid[i+1][i+1] = 1;
    }

    // Construct "Bridges" to tap specific powers of 2.
    // If bit j is set in x, we route flow from the spine at row j+1 to the collector column n.
    for (int j = 0; j <= L; ++j) {
        if ((x >> j) & 1) {
            int r = j + 1; // Row corresponding to bit j (value 2^j)
            int c_start;
            
            // Determine where the bridge starts.
            // For j < L, spine uses (r, r+1), so bridge must start at r+2.
            // For j == L, spine ends at (r, r), so bridge can start at r+1.
            if (j < L) {
                c_start = r + 2;
            } else {
                c_start = r + 1;
            }
            
            // Fill the bridge row with 1s up to column n
            for (int c = c_start; c <= n; ++c) {
                grid[r][c] = 1;
            }
        }
    }

    // Enable the Collector Column (last column n) to carry flow down to (n, n).
    for (int r = 1; r <= n; ++r) {
        grid[r][n] = 1;
    }

    // Output the result
    cout << n << "\n";
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) {
            cout << grid[i][j] << (j == n ? "" : " ");
        }
        cout << "\n";
    }

    return 0;
}