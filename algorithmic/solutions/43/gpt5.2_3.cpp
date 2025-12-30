#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N = 6, M = 6;
    vector<string> g = {
        "SS....",
        "SS....",
        "..BB..",
        "..BB..",
        "......",
        ".....P"
    };

    cout << N << " " << M << "\n";
    for (auto &row : g) cout << row << "\n";
    return 0;
}