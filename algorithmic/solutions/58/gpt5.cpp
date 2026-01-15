#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    unsigned long long x;
    if (!(cin >> x)) return 0;

    // Highest set bit (0-based)
    int L = 0;
    while ((1ULL << (L + 1)) <= x) L++;
    // Base column for the diamond chain
    int C = 3;
    // Last column (vertical corridor)
    int n = L + 4; // n = C + L + 1, since C=3 -> n = L + 4

    vector<vector<int>> a(n, vector<int>(n, 0));

    // Vertical chain at column 1 from row 1 to row L+1
    for (int r = 1; r <= L + 1; ++r) a[r-1][0] = 1;

    // For each set bit p, create a horizontal branch from (k,1) to E_k (entry into diamonds)
    for (int p = 0; p <= L; ++p) {
        if ((x >> p) & 1ULL) {
            int k = L - p + 1; // entry index
            int r = k;         // row index (1-based)
            int c_entry = C + (k - 1); // column of E_k (1-based)
            for (int j = 2; j <= c_entry; ++j) a[r-1][j-1] = 1;
        }
    }

    // Build the diamond chain of length L starting at E_1 = (1, C)
    for (int k = 1; k <= L; ++k) {
        int r = k;
        int c = C + (k - 1);
        a[r-1][c-1] = 1;
        a[r-1][c]   = 1;
        a[r][c-1]   = 1;
        a[r][c]     = 1;
    }
    // Ensure the exit cell E_{L+1} exists (it already does via diamonds if L>=1)
    // and connect to last column (n)
    // Set entire last column to 1 so from any connection point there is a unique path down to (n,n)
    for (int r = 1; r <= n; ++r) a[r-1][n-1] = 1;

    cout << n << "\n";
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            if (j) cout << ' ';
            cout << a[i][j];
        }
        cout << "\n";
    }
    return 0;
}