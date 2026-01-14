#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m, T;
    if (!(cin >> n >> m >> T)) return 0;

    vector<pair<int,int>> edges(m);
    for (int i = 0; i < m; ++i) {
        cin >> edges[i].first >> edges[i].second;
    }

    long long addEdges = 1LL * n * (n - 1) / 2;
    long long K = m + addEdges;

    // Phase 1: Graph modification
    cout << K << '\n';
    for (auto &e : edges) {
        cout << "- " << e.first << " " << e.second << '\n';
    }
    for (int i = 2; i <= n; ++i) {
        for (int j = 1; j < i; ++j) {
            cout << "+ " << i << " " << j << '\n';
        }
    }
    cout.flush();

    // Phase 2: T rounds
    for (int tc = 0; tc < T; ++tc) {
        int found = -1;
        string ans;

        for (int i = 1; i <= n; ++i) {
            cout << "? 1 " << i << '\n';
            cout.flush();
            if (!(cin >> ans)) return 0;
            if (ans == "Lose") {
                found = i;
                break;
            }
            // "Win" or possibly "Draw" - treat as not equal
        }

        if (found == -1) found = 1; // Fallback; should not happen

        cout << "! " << found << '\n';
        cout.flush();

        string verdict;
        if (!(cin >> verdict)) return 0;
        if (verdict == "Wrong") return 0;
    }

    return 0;
}