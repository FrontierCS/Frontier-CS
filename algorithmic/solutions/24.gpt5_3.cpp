#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    while (cin >> n) {
        vector<vector<unsigned char>> C(n, vector<unsigned char>(n));
        for (int i = 0; i < n; ++i) {
            int filled = 0;
            while (filled < n) {
                string tok;
                if (!(cin >> tok)) return 0;
                // If token is exactly n chars of 0/1, take whole row
                bool all01 = !tok.empty();
                for (char ch : tok) {
                    if (ch != '0' && ch != '1') { all01 = false; break; }
                }
                if ((int)tok.size() == n && all01) {
                    for (int j = 0; j < n; ++j) C[i][j] = tok[j] - '0';
                    filled = n;
                } else {
                    // Parse per character digits
                    for (char ch : tok) {
                        if (ch == '0' || ch == '1') {
                            C[i][filled++] = ch - '0';
                            if (filled == n) break;
                        }
                    }
                }
            }
        }

        vector<int> a;
        a.reserve(n);
        for (int v = 1; v <= n; ++v) {
            a.push_back(v);
            int sz = (int)a.size();
            for (int i = sz - 3; i >= 0; --i) {
                int x = a[i], y = a[i+1], z = a[i+2];
                unsigned char xy = C[x-1][y-1];
                unsigned char yz = C[y-1][z-1];
                if (xy == yz) continue;
                unsigned char xz = C[x-1][z-1];
                if (xy == xz) {
                    // center should be x
                    if (y < z) {
                        a[i] = y; a[i+1] = x; a[i+2] = z;
                    } else {
                        a[i] = z; a[i+1] = x; a[i+2] = y;
                    }
                } else {
                    // center should be z
                    if (x < y) {
                        a[i] = x; a[i+1] = z; a[i+2] = y;
                    } else {
                        a[i] = y; a[i+1] = z; a[i+2] = x;
                    }
                }
            }
        }

        for (int i = 0; i < n; ++i) {
            if (i) cout << ' ';
            cout << a[i];
        }
        if (!cin.eof()) cout << '\n';
    }
    return 0;
}