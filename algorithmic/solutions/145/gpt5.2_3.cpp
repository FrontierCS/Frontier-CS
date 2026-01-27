#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;

    vector<string> g0 = {
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

    vector<string> g1 = g0;
    for (auto &row : g1)
        for (char &c : row)
            if (c == '0') c = '1';

    const auto &out = (t == 0 ? g0 : g1);
    for (const auto &row : out) cout << row << "\n";
    return 0;
}