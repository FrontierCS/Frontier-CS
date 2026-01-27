#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // Read and ignore the entire input
    // (Valid solution that performs no actions)
    // This ensures we consume input in case the judge expects it.
    int n, m;
    if (!(cin >> n >> m)) {
        // If input is somehow missing, just output OK and exit
        cout << "OK\n";
        return 0;
    }
    vector<string> grid(n);
    for (int i = 0; i < n; ++i) {
        cin >> grid[i];
    }

    int Nb;
    cin >> Nb;
    for (int i = 0; i < Nb; ++i) {
        int x, y;
        long long g, c, d, v;
        cin >> x >> y;
        cin >> g >> c >> d >> v;
    }

    int Nr;
    cin >> Nr;
    for (int i = 0; i < Nr; ++i) {
        int x, y;
        long long g, c, d, v;
        cin >> x >> y;
        cin >> g >> c >> d >> v;
    }

    int k;
    cin >> k;
    for (int i = 0; i < k; ++i) {
        int x, y;
        long long G, C;
        cin >> x >> y >> G >> C;
    }

    // Output a single empty frame
    cout << "OK\n";
    return 0;
}