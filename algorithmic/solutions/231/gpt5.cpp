#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m, T;
    if (!(cin >> n >> m >> T)) {
        return 0;
    }
    vector<pair<int,int>> edges(m);
    for (int i = 0; i < m; ++i) {
        int a, b;
        cin >> a >> b;
        edges[i] = {a, b};
    }

    long long K = m + 1LL * n * (n - 1) / 2;
    cout << K << '\n';
    // Remove all existing edges
    for (auto &e : edges) {
        cout << "- " << e.first << ' ' << e.second << '\n';
    }
    // Add edges to make a lower-triangular DAG: i -> j for j < i
    for (int i = 2; i <= n; ++i) {
        for (int j = 1; j < i; ++j) {
            cout << "+ " << i << ' ' << j << '\n';
        }
    }
    cout.flush();

    for (int t = 0; t < T; ++t) {
        int found = -1;
        for (int i = 1; i <= n; ++i) {
            cout << "? 1 " << i << '\n';
            cout.flush();
            string ans;
            if (!(cin >> ans)) return 0;
            if (ans == "Lose") {
                found = i;
                break;
            } else if (ans == "Wrong") {
                return 0;
            }
            // "Win" or potentially "Draw" (shouldn't happen in our DAG)
        }
        if (found == -1) found = 1; // Fallback, should not happen
        cout << "! " << found << '\n';
        cout.flush();
        string verdict;
        if (!(cin >> verdict)) return 0;
        if (verdict == "Wrong") {
            return 0;
        }
    }

    return 0;
}