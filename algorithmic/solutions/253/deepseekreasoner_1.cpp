#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    int t;
    cin >> t;
    while (t--) {
        int n, m;
        cin >> n >> m;
        vector<pair<int, int>> edges(m);
        for (int i = 0; i < m; ++i) {
            cin >> edges[i].first >> edges[i].second;
        }
        vector<bool> repaired(m, false);
        // Test each edge individually
        for (int i = 0; i < m; ++i) {
            int u = edges[i].first, v = edges[i].second;
            // Block every edge except i
            for (int j = 0; j < m; ++j) {
                if (j != i) {
                    cout << "- " << j + 1 << endl;
                }
            }
            // Ensure edge i is unblocked
            cout << "+ " << i + 1 << endl;
            // Query with Y = {u}
            cout << "? 1 " << u << endl;
            int res1;
            cin >> res1;
            // Query with Y = {v}
            cout << "? 1 " << v << endl;
            int res2;
            cin >> res2;
            // If both queries returned 1, consider the edge repaired
            if (res1 == 1 && res2 == 1) {
                repaired[i] = true;
            }
            // Block edge i again for the next tests
            cout << "- " << i + 1 << endl;
        }
        // Output the answer
        cout << "!";
        for (int i = 0; i < m; ++i) {
            cout << " " << repaired[i];
        }
        cout << endl;
        // Read verdict
        int verdict;
        cin >> verdict;
        if (verdict != 1) {
            // Wrong answer
            break;
        }
    }
    return 0;
}