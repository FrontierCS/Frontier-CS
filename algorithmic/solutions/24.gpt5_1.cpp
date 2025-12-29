#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    while ( (cin >> n) ) {
        vector<string> C(n, string(n, '0'));
        for (int i = 0; i < n; ++i) {
            int read = 0;
            while (read < n) {
                char ch;
                if (!(cin >> ch)) return 0;
                if (ch == '0' || ch == '1') {
                    C[i][read++] = ch;
                }
            }
        }

        vector<int> p(n);
        iota(p.begin(), p.end(), 0);

        // Make c[1..n-1] monotone non-decreasing by eliminating 10 patterns using triple rotations
        int i = 0;
        while (i + 2 < n) {
            char c1 = C[p[i]][p[i+1]];
            char c2 = C[p[i+1]][p[i+2]];
            if (c1 == '1' && c2 == '0') {
                int a = p[i], b = p[i+1], c = p[i+2];
                p[i] = b; p[i+1] = c; p[i+2] = a;
                if (i > 0) --i;
            } else {
                ++i;
            }
        }

        // Compute c array
        vector<char> c(n);
        for (int j = 0; j < n - 1; ++j) c[j] = C[p[j]][p[j+1]];
        c[n-1] = C[p[n-1]][p[0]];

        // Find first internal change in c[0..n-2]
        int k = -1;
        for (int j = 0; j < n - 2; ++j) {
            if (c[j] != c[j+1]) { k = j; break; }
        }

        // If there is one internal boundary, rotate to place that boundary at the excluded comparison (wrap)
        if (k != -1) {
            int s = (k + 1) % n;
            vector<int> q(n);
            for (int t = 0; t < n; ++t) q[t] = p[(s + t) % n];
            p.swap(q);
        }

        // Output permutation (1-based)
        for (int idx = 0; idx < n; ++idx) {
            if (idx) cout << ' ';
            cout << (p[idx] + 1);
        }
        cout << '\n';
    }
    return 0;
}