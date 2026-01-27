#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    cin >> t;
    while (t--) {
        int n, m;
        cin >> n >> m;
        vector<pair<int, int>> edges(m);
        for (int i = 0; i < m; ++i) {
            cin >> edges[i].first >> edges[i].second;
        }

        vector<int> repaired(m, 0);

        // For each edge, test if it is a bridge by blocking it
        // and querying its endpoints.
        for (int i = 0; i < m; ++i) {
            int u = edges[i].first, v = edges[i].second;

            // Block edge i+1
            cout << "- " << i+1 << endl;
            cout.flush();

            // Query endpoint u
            cout << "? 1 " << u << endl;
            cout.flush();
            int ans1;
            cin >> ans1;
            if (ans1 == -1) return 0; // Invalid

            // Query endpoint v
            cout << "? 1 " << v << endl;
            cout.flush();
            int ans2;
            cin >> ans2;
            if (ans2 == -1) return 0;

            // If answers differ, the edge is a repaired bridge.
            if (ans1 != ans2) {
                repaired[i] = 1;
            }

            // Unblock edge i+1
            cout << "+ " << i+1 << endl;
            cout.flush();
        }

        // Output answer
        cout << "! ";
        for (int i = 0; i < m; ++i) {
            cout << repaired[i] << " \n"[i == m-1];
        }
        cout.flush();

        // Read verdict
        int verdict;
        cin >> verdict;
        if (verdict == -1 || verdict == 0) {
            return 0; // Wrong answer or invalid
        }
    }

    return 0;
}