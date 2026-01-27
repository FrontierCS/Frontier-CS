#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if(!(cin >> n)) return 0;
    long long m = 1LL * n * (n - 1) / 2;
    vector<int> vals(m);
    for (long long i = 0; i < m; ++i) cin >> vals[i];

    vector<vector<int>> mat(n, vector<int>(n, 0));
    long long idx = 0;
    for (int i = 0; i < n; ++i) {
        for (int j = i + 1; j < n; ++j) {
            int x = vals[idx++];
            mat[i][j] = mat[j][i] = x;
        }
    }

    vector<int> p(n, 0);
    for (int i = 0; i < n; ++i) {
        int res = ~0;
        for (int j = 0; j < n; ++j) if (j != i) {
            res &= mat[i][j];
        }
        p[i] = res;
    }

    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << p[i];
    }
    cout << '\n';
    return 0;
}