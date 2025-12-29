#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int t;
    if (!(cin >> t)) t = 0;
    char d = (t == 1 ? '1' : '0');
    vector<string> pattern = {
        "x   x   xxx ",
        "xx xx  x   x",
        "x x x  x   x",
        "x x x  xxxx ",
        "x x x  x    ",
        "x   x  x    ",
        "            ",
        "x  x   xxxxx",
        "x x      x  ",
        "xx   x x x  ",
        "x x  x x x  ",
        "x  x xxx x  "
    };
    for (auto &s : pattern) {
        for (char c : s) cout << (c == 'x' ? d : ' ');
        cout << '\n';
    }
    return 0;
}