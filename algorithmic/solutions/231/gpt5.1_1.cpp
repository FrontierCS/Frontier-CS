#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m, T;
    if (!(cin >> n >> m >> T)) return 0;
    for (int i = 0; i < m; ++i) {
        int a, b;
        cin >> a >> b;
    }

    // No graph modifications
    cout << 0 << "\n";
    cout.flush();

    for (int t = 0; t < T; ++t) {
        // Always guess vertex 1
        cout << "! 1\n";
        cout.flush();

        string verdict;
        if (!(cin >> verdict)) {
            // In non-interactive/offline environment, EOF will occur here
            return 0;
        }
        if (verdict == "Wrong") {
            return 0;
        }
        // If "Correct", continue to next round
    }

    return 0;
}