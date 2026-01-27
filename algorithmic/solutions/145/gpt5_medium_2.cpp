#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int t;
    if (!(cin >> t)) return 0;
    vector<string> small(12, "012301230123");
    vector<string> large(12, "123123123123");
    const auto &grid = (t == 1) ? large : small;
    for (const auto &row : grid) cout << row << '\n';
    return 0;
}