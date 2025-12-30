#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    vector<string> g = {
        "#########",
        "#SS..BBP#",
        "#SS..BB.#",
        "#.......#",
        "#.......#",
        "#.......#",
        "#########"
    };

    cout << (int)g.size() << " " << (int)g[0].size() << "\n";
    for (auto &row : g) cout << row << "\n";
    return 0;
}