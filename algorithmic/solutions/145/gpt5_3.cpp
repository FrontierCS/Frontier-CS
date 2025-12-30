#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int t;
    if (!(cin >> t)) return 0;
    vector<string> grid(12);
    if (t == 0) {
        string row = "000000000000";
        for (int i = 0; i < 12; ++i) grid[i] = row;
    } else {
        string row = "111111111111";
        for (int i = 0; i < 12; ++i) grid[i] = row;
    }
    for (int i = 0; i < 12; ++i) {
        cout << grid[i] << "\n";
    }
    return 0;
}