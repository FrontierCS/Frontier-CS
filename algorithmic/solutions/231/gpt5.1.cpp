#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m, T;
    if (!(cin >> n >> m >> T)) return 0;

    vector<pair<int,int>> edges(m);
    for (int i = 0; i < m; ++i) {
        int a, b;
        cin >> a >> b;
        edges[i] = {a, b};
    }

    long long K = m + 1LL * n * (n - 1) / 2;
    cout << K << '\n';

    // Remove all existing edges
    for (int i = 0; i < m; ++i) {
        cout << "- " << edges[i].first << ' ' << edges[i].second << '\n';
    }

    // Add edges: for each i, edges to all j < i (complete DAG)
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j < i; ++j) {
            cout << "+ " << i << ' ' << j << '\n';
        }
    }
    cout.flush();

    for (int tc = 0; tc < T; ++tc) {
        int answer_vertex = n; // fallback, should be overwritten

        for (int i = 1; i <= n; ++i) {
            cout << "? 1 " << i << '\n';
            cout.flush();

            string res;
            if (!(cin >> res)) return 0;

            if (res == "Lose" || res == "Draw") {
                answer_vertex = i;
                break;
            }
            // if "Win", continue to next i
        }

        cout << "! " << answer_vertex << '\n';
        cout.flush();

        string verdict;
        if (!(cin >> verdict)) return 0;
        if (verdict == "Wrong") {
            return 0;
        }
        // if "Correct", proceed to next test case
    }

    return 0;
}