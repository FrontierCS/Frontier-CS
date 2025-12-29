#include <bits/stdc++.h>
using namespace std;

int main() {
    int n = 20, m = 20;
    vector<string> grid(n, string(m, '0'));
    int row = 10;
    int col = 10;
    for (int j = 0; j < m; j++) {
        grid[row][j] = '1';
    }
    for (int i = 0; i < n; i++) {
        grid[i][col] = '1';
    }
    cout << n << " " << m << endl;
    for (auto& s : grid) {
        cout << s << endl;
    }
    return 0;
}