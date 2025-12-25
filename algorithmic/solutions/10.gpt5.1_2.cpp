#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        int n;
        if (!(cin >> n)) return 0;

        if (n == 1) {
            cout << "!\n";
            cout.flush();
            continue;
        }

        vector<long long> dist(n + 1, 0);
        for (int i = 2; i <= n; ++i) {
            cout << "? " << 1 << " " << i << "\n";
            cout.flush();
            long long d;
            if (!(cin >> d)) return 0;
            dist[i] = d;
        }

        cout << "!";
        for (int i = 2; i <= n; ++i) {
            cout << " " << 1 << " " << i << " " << dist[i];
        }
        cout << "\n";
        cout.flush();
    }
    return 0;
}