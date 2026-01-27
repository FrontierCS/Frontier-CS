#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;

    vector<long long> vals;
    {
        long long x;
        while (cin >> x) vals.push_back(x);
    }

    // Helper to compute bitmask covering numbers [0..n-1]
    auto fullMask = [&]() {
        int m = 1;
        while (m < n) m <<= 1;
        return m - 1;
    };
    int mask = fullMask();

    vector<int> p(n, 0);

    if ((int)vals.size() == n) {
        // Direct permutation given
        for (int i = 0; i < n; ++i) p[i] = (int)vals[i];
    } else if ((int)vals.size() == n * n) {
        // Full matrix given in row-major: M[i][j] = p_i | p_j
        // p_i = AND over all j (M[i][j])
        for (int i = 0; i < n; ++i) {
            int v = mask;
            for (int j = 0; j < n; ++j) {
                long long mj = vals[i * n + j];
                v &= (int)mj;
            }
            p[i] = v;
        }
    } else if ((int)vals.size() == n * (n - 1) / 2) {
        // Upper triangular (i<j) row-major: for i=0..n-1, j=i+1..n-1
        vector<int> ans(n, mask);
        int idx = 0;
        for (int i = 0; i < n; ++i) {
            for (int j = i + 1; j < n; ++j) {
                int v = (int)vals[idx++];
                ans[i] &= v;
                ans[j] &= v; // M[j][i] = v contributes to row j as well
            }
        }
        p = ans;
    } else {
        // Fallback: output identity permutation
        for (int i = 0; i < n; ++i) p[i] = i;
    }

    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << p[i];
    }
    cout << '\n';
    return 0;
}