#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int n = 19, m = 20;
    cout << n << " " << m << "\n";
    for (int r = 0; r < n; r++) {
        string row(m, '0');
        if (r % 2 == 0) {
            row.assign(m, '1');
        } else {
            int k = (r - 1) / 2;
            int c = (k % 2 == 0) ? (m - 1) : 0;
            row[c] = '1';
        }
        cout << row << "\n";
    }
    return 0;
}