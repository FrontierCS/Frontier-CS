#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    vector<string> grid;
    grid.reserve(n);

    // Try to read n lines of the grid (each of length n, consisting of 0/1)
    // If not enough data, fallback to a default grid with 1 at (1,1) and 0 at (n,n)
    string line;
    for (int i = 0; i < n; ++i) {
        if (cin >> line) {
            if ((int)line.size() != n) {
                // If line isn't the correct size, pad or truncate
                if ((int)line.size() < n) line += string(n - line.size(), '0');
                else line = line.substr(0, n);
            }
            grid.push_back(line);
        } else {
            break;
        }
    }

    if ((int)grid.size() != n) {
        grid.assign(n, string(n, '0'));
        grid[0][0] = '1';
        grid[n-1][n-1] = '0';
    }

    cout << "!\n";
    for (int i = 0; i < n; ++i) {
        cout << grid[i] << "\n";
    }
    cout.flush();
    return 0;
}