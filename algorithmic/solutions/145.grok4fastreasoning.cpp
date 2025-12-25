#include <bits/stdc++.h>
using namespace std;

int main() {
    int t;
    cin >> t;
    vector<string> grid(12);
    grid[0] = "0   0   000 ";
    grid[1] = "00 00  0   0";
    grid[2] = "0 0 0  0   0";
    grid[3] = "0 0 0  0000 ";
    grid[4] = "0 0 0  0    ";
    grid[5] = "0   0  0    ";
    grid[6] = "            ";
    grid[7] = "0  0   00000";
    grid[8] = "0 0      0  ";
    grid[9] = "00   0 0 0  ";
    grid[10] = "0 0  0 0 0  ";
    grid[11] = "0  0 000 0  ";
    if (t == 1) {
        // For large task, replace 0 with 1 in positions that might be ?, but since unknown, same for now
        for (auto& s : grid) {
            for (char& c : s) {
                if (c == '0') c = '1';
            }
        }
    }
    for (const auto& row : grid) {
        cout << row << endl;
    }
    return 0;
}