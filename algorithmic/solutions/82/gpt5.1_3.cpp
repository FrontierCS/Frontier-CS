#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    vector<long long> data;
    long long x;
    while (cin >> x) data.push_back(x);

    // Case 1: data directly is the permutation
    if ((int)data.size() == n) {
        for (int i = 0; i < n; ++i) {
            cout << data[i] << (i + 1 < n ? ' ' : '\n');
        }
        return 0;
    }

    // Determine bit mask (values are in [0, n-1])
    int bits = 0;
    while ((1 << bits) < n) ++bits;
    int mask = (1 << bits) - 1;

    vector<int> p(n);

    size_t sz = data.size();
    size_t nn = (size_t)n * (size_t)n;
    size_t tri = (size_t)n * (size_t)(n - 1) / 2;
    size_t tri_diag = (size_t)n * (size_t)(n + 1) / 2;

    if (sz == nn || sz == tri || sz == tri_diag) {
        // Interpret as OR-matrix in some form.
        vector<vector<int>> a(n, vector<int>(n, 0));

        if (sz == nn) {
            // Full n x n matrix, row-major.
            size_t idx = 0;
            for (int i = 0; i < n; ++i) {
                for (int j = 0; j < n; ++j) {
                    a[i][j] = (int)data[idx++];
                }
            }
        } else if (sz == tri) {
            // Upper triangle without diagonal, i < j.
            size_t idx = 0;
            for (int i = 0; i < n; ++i) {
                for (int j = i + 1; j < n; ++j) {
                    int val = (int)data[idx++];
                    a[i][j] = a[j][i] = val;
                }
            }
        } else { // sz == tri_diag
            // Assume first n elements are diagonal, then upper triangle (i < j).
            size_t idx = 0;
            for (int i = 0; i < n; ++i) {
                a[i][i] = (int)data[idx++];
            }
            for (int i = 0; i < n; ++i) {
                for (int j = i + 1; j < n; ++j) {
                    int val = (int)data[idx++];
                    a[i][j] = a[j][i] = val;
                }
            }
        }

        // Reconstruct permutation: p[i] = AND_j (OR(i, j)), j != i
        for (int i = 0; i < n; ++i) {
            int val = mask;
            for (int j = 0; j < n; ++j) {
                if (j == i) continue;
                val &= a[i][j];
            }
            p[i] = val;
        }

        for (int i = 0; i < n; ++i) {
            cout << p[i] << (i + 1 < n ? ' ' : '\n');
        }
        return 0;
    }

    // Fallback: treat first n numbers (if present) as permutation.
    vector<int> out(n, 0);
    for (int i = 0; i < n && i < (int)data.size(); ++i) {
        out[i] = (int)data[i];
    }
    for (int i = 0; i < n; ++i) {
        cout << out[i] << (i + 1 < n ? ' ' : '\n');
    }

    return 0;
}