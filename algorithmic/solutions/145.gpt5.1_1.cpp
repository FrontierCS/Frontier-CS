#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int t;
    if (!(cin >> t)) return 0;

    if (t == 0) {
        vector<string> grid = {
            "0   0   000 ",
            "00 00  0   0",
            "0 0 0  0   0",
            "0 0 0  0000 ",
            "0 0 0  0    ",
            "0   0  0    ",
            "            ",
            "0  0   00000",
            "0 0      0  ",
            "00   0 0 0  ",
            "0 0  0 0 0  ",
            "0  0 000 0  "
        };
        for (auto &row : grid) cout << row << '\n';
    } else {
        vector<string> grid(12, string(12, '1'));
        for (auto &row : grid) cout << row << '\n';
    }

    return 0;
}