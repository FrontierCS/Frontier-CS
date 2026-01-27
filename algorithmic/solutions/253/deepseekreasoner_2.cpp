#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <cstdlib>
#include <ctime>

using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    cin >> t;
    srand(time(0));

    for (int test = 0; test < t; ++test) {
        int n, m;
        cin >> n >> m;
        vector<pair<int, int>> edges(m);
        for (int i = 0; i < m; ++i) {
            cin >> edges[i].first >> edges[i].second;
        }

        // Initially all edges are unblocked. We block all edges first.
        for (int i = 1; i <= m; ++i) {
            cout << "- " << i << endl;
        }
        // We don't need to read response for block/unblock commands.
        // The problem statement doesn't specify that we get a response for those.
        // Only for delivery queries and final answer we get response.
        // So we just flush.

        // Threshold parameters
        const int Q = 50;                 // number of queries per edge
        const int THRESHOLD = 35;         // if # of 1's >= THRESHOLD, consider repaired

        vector<int> repaired(m, 0);

        for (int i = 0; i < m; ++i) {
            int a = edges[i].first, b = edges[i].second;

            // Unblock edge i+1
            cout << "+ " << (i+1) << endl;

            int cnt_one = 0;
            for (int q = 0; q < Q; ++q) {
                cout << "? 2 " << a << " " << b << endl;
                int response;
                cin >> response;
                if (response == -1) {
                    // Invalid, should terminate
                    return 0;
                }
                cnt_one += response;
            }

            // Block edge i+1 again
            cout << "- " << (i+1) << endl;

            if (cnt_one >= THRESHOLD) {
                repaired[i] = 1;
            }
        }

        // Output final answer
        cout << "! ";
        for (int i = 0; i < m; ++i) {
            cout << repaired[i];
            if (i+1 < m) cout << " ";
        }
        cout << endl;

        // Read judge's response (1 or 0)
        int resp;
        cin >> resp;
        if (resp != 1) {
            // Wrong answer, terminate
            return 0;
        }
    }

    return 0;
}