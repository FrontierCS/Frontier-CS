#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int t;
    if(!(cin >> t)) return 0;
    const int N = 12;
    vector<string> grid(N, string(N, '0'));
    if (t == 0) {
        for (int i = 0; i < N; ++i) {
            for (int j = 0; j < N; ++j) {
                if ((i == 0 || i == N-1) && (j == 0 || j == N-1)) grid[i][j] = '2';
                else if (i == 0 || i == N-1 || j == 0 || j == N-1) grid[i][j] = '1';
                else grid[i][j] = '0';
            }
        }
    } else {
        for (int i = 0; i < N; ++i) {
            for (int j = 0; j < N; ++j) {
                if ((i == 0 || i == N-1) && (j == 0 || j == N-1)) grid[i][j] = '2';
                else if (i == 0 || i == N-1 || j == 0 || j == N-1) grid[i][j] = '1';
                else grid[i][j] = '1';
            }
        }
    }
    for (int i = 0; i < N; ++i) {
        cout << grid[i] << "\n";
    }
    return 0;
}