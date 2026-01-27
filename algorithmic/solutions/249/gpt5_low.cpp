#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;
    vector<vector<int>> OR(n, vector<int>(n, 0));
    for (int i = 0; i < n; ++i) {
        for (int j = i + 1; j < n; ++j) {
            int x; 
            if (!(cin >> x)) return 0;
            OR[i][j] = OR[j][i] = x;
        }
    }
    vector<int> minVal(n, INT_MAX);
    for (int i = 0; i < n; ++i) {
        int mv = INT_MAX;
        for (int j = 0; j < n; ++j) if (i != j) {
            mv = min(mv, OR[i][j]);
        }
        minVal[i] = mv;
    }
    int z = 0;
    for (int i = 1; i < n; ++i) {
        if (minVal[i] < minVal[z]) z = i;
    }
    vector<int> p(n, 0);
    p[z] = 0;
    for (int j = 0; j < n; ++j) if (j != z) {
        p[j] = OR[z][j];
    }
    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << p[i];
    }
    cout << '\n';
    return 0;
}