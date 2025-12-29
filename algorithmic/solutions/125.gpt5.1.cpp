#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    if (!(cin >> N)) return 0;
    int M = 2 * N;

    vector<vector<int>> pos(N + 1);
    for (int i = 1; i <= M; ++i) {
        int t;
        if (!(cin >> t)) return 0;
        if (t >= 1 && t <= N) {
            pos[t].push_back(i);
        }
    }

    for (int t = 1; t <= N; ++t) {
        if (pos[t].size() == 2) {
            cout << "! " << pos[t][0] << " " << pos[t][1] << "\n";
        } else {
            // In case of malformed input (not exactly two per type),
            // pair sequentially among available positions of this type.
            for (size_t i = 0; i + 1 < pos[t].size(); i += 2) {
                cout << "! " << pos[t][i] << " " << pos[t][i + 1] << "\n";
            }
        }
    }

    return 0;
}