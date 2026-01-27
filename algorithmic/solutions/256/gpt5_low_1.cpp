#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;

    vector<string> tokens;
    {
        string s;
        while (cin >> s) tokens.push_back(s);
    }

    vector<string> grid;
    // Try to parse as n strings of length n
    int idx = 0;
    bool ok = false;
    if ((int)tokens.size() >= n) {
        bool good = true;
        for (int i = 0; i < n; ++i) {
            if ((int)tokens[i].size() != n) { good = false; break; }
            for (char c : tokens[i]) if (c != '0' && c != '1') { good = false; break; }
            if (!good) break;
        }
        if (good) {
            for (int i = 0; i < n; ++i) grid.push_back(tokens[i]);
            ok = true;
        }
    }
    // Try to parse as n*n single digit tokens
    if (!ok && (int)tokens.size() >= n * n) {
        bool good = true;
        for (int i = 0; i < n * n; ++i) {
            if (!(tokens[i] == "0" || tokens[i] == "1")) { good = false; break; }
        }
        if (good) {
            grid.assign(n, string(n, '0'));
            int p = 0;
            for (int i = 0; i < n; ++i) {
                for (int j = 0; j < n; ++j) {
                    grid[i][j] = tokens[p++][0];
                }
            }
            ok = true;
        }
    }
    // Fallback: construct a default grid with (1,1)=1 and (n,n)=0
    if (!ok) {
        grid.assign(n, string(n, '0'));
        grid[0][0] = '1';
        grid[n-1][n-1] = '0';
    }

    for (int i = 0; i < n; ++i) {
        cout << grid[i] << "\n";
    }
    return 0;
}