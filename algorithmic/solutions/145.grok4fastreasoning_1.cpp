#include <bits/stdc++.h>

using namespace std;

int main() {
    int t;
    cin >> t;
    vector<string> grid(12);
    if (t == 0) {
        grid[0] = "0   0   000 ";
        grid[1] = "00 00  0   0";
        grid[2] = "0 0 0  0   0";
        grid[3] = "0 0 0  0000 ";
        grid[4] = "0 0 0  0    ";
        grid[5] = "0   0  0    ";
        grid[6] = "0  0   00000";
        grid[7] = "0 0      0  ";
        grid[8] = "00   0 0 0  ";
        grid[9] = "0 0  0 0 0  ";
        grid[10] = "0  0 000 0  ";
        grid[11] = "          0 ";
    } else {
        grid[0] = "1   1   111 ";
        grid[1] = "11 11  1   1";
        grid[2] = "1 1 1  1   1";
        grid[3] = "1 1 1  1111 ";
        grid[4] = "1 1 1  1    ";
        grid[5] = "1   1  1    ";
        grid[6] = "1  1   11111";
        grid[7] = "1 1      1  ";
        grid[8] = "11   1 1 1  ";
        grid[9] = "1 1  1 1 1  ";
        grid[10] = "1  1 111 1  ";
        grid[11] = "          1 ";
    }
    for (auto& s : grid) {
        cout << s << endl;
    }
    return 0;
}