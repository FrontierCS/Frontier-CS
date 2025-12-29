#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) t = 0;

    vector<string> grid = {
        "1   1   111 ",
        "11 11  1   1",
        "1 1 1  1   1",
        "1 1 1  1111 ",
        "1 1 1  1    ",
        "1   1  1    ",
        "            ",
        "1  1   11111",
        "1 1      1  ",
        "11   1 1 1  ",
        "1 1  1 1 1  ",
        "1  1 111 1  "
    };

    for (int i = 0; i < 12; ++i) {
        cout << grid[i] << "\n";
    }

    return 0;
}