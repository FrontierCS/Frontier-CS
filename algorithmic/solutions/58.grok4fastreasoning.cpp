#include <bits/stdc++.h>
using namespace std;

int main() {
    long long x;
    cin >> x;
    if (x == 1) {
        cout << 1 << endl;
        cout << 1 << endl;
        return 0;
    }
    int bits = 0;
    long long tx = x;
    while (tx > 0) {
        bits++;
        tx >>= 1;
    }
    int n = bits + 1;
    vector<vector<int>> grid(n + 1, vector<int>(n + 1, 0));
    grid[1][1] = 1;
    // Set single path to layer1 (2,2)
    grid[1][2] = 1;
    grid[2][2] = 1;
    grid[2][1] = 0;
    // Set doublings from layer1 to higher
    for (int l = 1; l < bits; l++) {
        int p = l + 1;
        int q = p + 1;
        grid[p][q] = 1;
        grid[q][p] = 1;
        grid[q][q] = 1;
    }
    // Set bypasses for lower bits
    for (int i = 0; i < bits - 1; i++) {
        if (x & (1LL << i)) {
            int layer = bits - i;
            int rr = layer + 1;
            for (int j = 1; j <= rr; j++) {
                grid[1][j] = 1;
            }
            for (int k = 1; k <= rr; k++) {
                grid[k][rr] = 1;
            }
        }
    }
    cout << n << endl;
    for (int i = 1; i <= n; i++) {
        for (int j = 1; j <= n; j++) {
            cout << grid[i][j];
            if (j < n) cout << " ";
        }
        cout << endl;
    }
    return 0;
}