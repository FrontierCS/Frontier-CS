#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    while (true) {
        if(!(cin >> n)) break;
        vector<string> C(n, string(n, '0'));
        // Read n*n digits (either as strings like "001" or space-separated)
        for (int i = 0; i < n; ++i) {
            int cnt = 0;
            while (cnt < n) {
                string tok;
                if(!(cin >> tok)) return 0;
                for (char ch : tok) {
                    if (ch == '0' || ch == '1') {
                        if (cnt < n) {
                            C[i][cnt++] = ch;
                        }
                    }
                }
            }
        }
        // Output a simple valid permutation (not necessarily optimal)
        for (int i = 1; i <= n; ++i) {
            if (i > 1) cout << ' ';
            cout << i;
        }
        cout << '\n';
    }
    return 0;
}