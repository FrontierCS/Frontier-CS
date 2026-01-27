#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    long long x;
    if (!(cin >> x)) return 0;

    if (x == 1) {
        cout << 1 << "\n1\n";
        return 0;
    }

    // Binary representation (LSB first)
    long long tmp = x;
    vector<int> bits;
    while (tmp) {
        bits.push_back(tmp & 1);
        tmp >>= 1;
    }
    int k = bits.size(); // highest bit index = k-1, and bits[k-1] == 1

    // Build operations: from most significant (excluding top) down to LSB
    // cur starts from 1, then for i = k-2..0: cur = 2*cur; if bits[i]==1 -> cur++
    vector<char> ops; // 'D' for double, 'I' for increment
    for (int i = k - 2; i >= 0; --i) {
        ops.push_back('D');
        if (bits[i]) ops.push_back('I');
    }

    int m = (int)ops.size();
    int n = 2 * m + 1;
    vector<vector<int>> a(n + 1, vector<int>(n + 1, 0));

    // Start cell
    a[1][1] = 1;
    int maxColTree = 1;

    int r = 1, c = 1; // current value cell P_t

    for (int t = 0; t < m; ++t) {
        char op = ops[t];
        if (op == 'D') {
            // Doubling gadget
            // P_t at (r, c)
            a[r][c] = 1;
            a[r][c + 1] = 1;
            a[r + 1][c] = 1;
            a[r + 1][c + 1] = 1;
            a[r + 2][c + 1] = 1;
            a[r + 2][c + 2] = 1; // P_{t+1}
        } else { // 'I'
            int colTarget = c + 2;

            // Extend top row for ONE-tree if needed
            if (colTarget > maxColTree) {
                for (int j = maxColTree + 1; j <= colTarget; ++j)
                    a[1][j] = 1;
                maxColTree = colTarget;
            }

            // Vertical ONE-tree column from row 2 to r at colTarget
            for (int i = 2; i <= r; ++i)
                a[i][colTarget] = 1;

            // Corridor from P_t to L
            a[r + 1][c] = 1;     // C1
            a[r + 2][c] = 1;     // C2
            a[r + 2][c + 1] = 1; // L

            // Injection cell U and new value cell
            a[r + 1][c + 2] = 1; // U
            a[r + 2][c + 2] = 1; // P_{t+1}
        }
        r += 2;
        c += 2;
    }

    cout << n << "\n";
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) {
            cout << a[i][j];
            if (j < n) cout << ' ';
        }
        cout << "\n";
    }

    return 0;
}