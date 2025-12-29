#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, T;
    if (!(cin >> N >> T)) return 0;
    vector<string> grid(N);
    for (int i = 0; i < N; i++) {
        string row;
        row.reserve(N);
        for (int j = 0; j < N; j++) {
            char c;
            cin >> c;
            row.push_back(c);
        }
        grid[i] = row;
    }

    cout << "\n";
    return 0;
}