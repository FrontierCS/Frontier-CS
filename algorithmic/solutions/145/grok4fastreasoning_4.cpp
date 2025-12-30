#include <bits/stdc++.h>

using namespace std;

int main() {
    int t;
    cin >> t;
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
    if (t == 1) {
        for (auto &s : grid) {
            for (char &c : s) {
                if (c == '0') c = '1';
            }
        }
    }
    for (const auto &s : grid) {
        cout << s << endl;
    }
    return 0;
}