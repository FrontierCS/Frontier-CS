#include <bits/stdc++.h>
using namespace std;

int main() {
    unsigned long long x;
    cin >> x;
    const int MAX_M = 80;
    vector<vector<unsigned long long>> pascal(MAX_M + 1, vector<unsigned long long>(MAX_M + 1, 0ULL));
    for (int i = 0; i <= MAX_M; ++i) {
        pascal[i][0] = 1ULL;
        if (i <= MAX_M) pascal[i][i] = 1ULL;
    }
    for (int i = 2; i <= MAX_M; ++i) {
        for (int j = 1; j < i; ++j) {
            pascal[i][j] = pascal[i - 1][j - 1] + pascal[i - 1][j];
        }
    }
    int n_found = -1;
    vector<pair<int, int>> blocks;
    for (int n = 1; n <= 40; ++n) {
        int mm = 2 * n - 2;
        unsigned long long B = (mm >= 0 && n - 1 >= 0 && n - 1 <= mm) ? pascal[mm][n - 1] : 0ULL;
        if (B < x) continue;
        unsigned long long d = B - x;
        blocks.clear();
        bool found = false;
        if (d == 0) {
            found = true;
        } else {
            // try single
            for (int i = 1; i <= n && !found; ++i) {
                for (int j = 1; j <= n && !found; ++j) {
                    int a = i + j - 2;
                    int b = i - 1;
                    unsigned long long to_val = (a >= 0 && b >= 0 && b <= a) ? pascal[a][b] : 0ULL;
                    int c = 2 * n - i - j;
                    int dd_val = n - i;
                    unsigned long long fr_val = (c >= 0 && dd_val >= 0 && dd_val <= c) ? pascal[c][dd_val] : 0ULL;
                    unsigned long long th = to_val * fr_val;
                    if (th == d) {
                        found = true;
                        blocks.emplace_back(i, j);
                    }
                }
            }
            if (!found) {
                // try pairs
                for (int i1 = 1; i1 <= n && !found; ++i1) {
                    for (int j1 = 1; j1 <= n && !found; ++j1) {
                        int a1 = i1 + j1 - 2;
                        int b1 = i1 - 1;
                        unsigned long long to1 = (a1 >= 0 && b1 >= 0 && b1 <= a1) ? pascal[a1][b1] : 0ULL;
                        int c1 = 2 * n - i1 - j1;
                        int d1 = n - i1;
                        unsigned long long fr1 = (c1 >= 0 && d1 >= 0 && d1 <= c1) ? pascal[c1][d1] : 0ULL;
                        unsigned long long th1 = to1 * fr1;
                        if (th1 > d) continue;
                        for (int i2 = 1; i2 <= n && !found; ++i2) {
                            for (int j2 = 1; j2 <= n && !found; ++j2) {
                                if (i2 == i1 && j2 == j1) continue;
                                int a2 = i2 + j2 - 2;
                                int b2 = i2 - 1;
                                unsigned long long to2 = (a2 >= 0 && b2 >= 0 && b2 <= a2) ? pascal[a2][b2] : 0ULL;
                                int c2 = 2 * n - i2 - j2;
                                int d2 = n - i2;
                                unsigned long long fr2 = (c2 >= 0 && d2 >= 0 && d2 <= c2) ? pascal[c2][d2] : 0ULL;
                                unsigned long long th2 = to2 * fr2;
                                if (th1 + th2 != d) continue;
                                bool comp1 = (i1 <= i2 && j1 <= j2);
                                bool comp2 = (i2 <= i1 && j2 <= j1);
                                if (!comp1 && !comp2) {
                                    found = true;
                                    blocks.emplace_back(i1, j1);
                                    blocks.emplace_back(i2, j2);
                                }
                            }
                        }
                    }
                }
            }
        }
        if (found) {
            n_found = n;
            break;
        }
    }
    // assume found
    assert(n_found != -1);
    cout << n_found << endl;
    set<pair<int, int>> block_set;
    for (auto& p : blocks) {
        block_set.insert(p);
    }
    for (int i = 1; i <= n_found; ++i) {
        for (int j = 1; j <= n_found; ++j) {
            if (block_set.count({i, j})) {
                cout << 0;
            } else {
                cout << 1;
            }
            if (j < n_found) cout << " ";
            else cout << endl;
        }
    }
    return 0;
}