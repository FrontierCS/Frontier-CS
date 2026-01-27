#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    while ( (cin >> n) ) {
        vector<string> row(n);
        for (int i = 0; i < n; ++i) {
            string s;
            cin >> s;
            if ((int)s.size() == n) {
                row[i] = s;
            } else {
                // spaced input
                string t = s;
                string line;
                row[i].assign(n, '0');
                row[i][0] = t[0];
                for (int j = 1; j < n; ++j) {
                    cin >> t;
                    row[i][j] = t[0];
                }
            }
        }
        // Output a trivial permutation (may not be optimal)
        for (int i = 1; i <= n; ++i) {
            if (i > 1) cout << ' ';
            cout << i;
        }
        cout << "\n";
    }
    return 0;
}