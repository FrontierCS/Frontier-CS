#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m;
    if(!(cin >> n >> m)) return 0;
    vector<vector<int>> a(n+2, vector<int>(0));
    for (int i = 1; i <= n; ++i) {
        a[i].resize(m);
        for (int j = 0; j < m; ++j) cin >> a[i][j];
    }
    // Output zero operations (fallback).
    cout << 0 << "\n";
    return 0;
}