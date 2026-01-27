#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    if (n == 0) {
        cout << 0 << '\n';
        return 0;
    }

    long long N = n + 1LL;
    int B = 1;
    while (1LL * B * B * B < N) ++B;

    vector<int> lengths;
    // Group 1: small lengths 2..B-1
    for (int s = 2; s <= B - 1 && s <= n; ++s) {
        lengths.push_back(s);
    }
    // Group 2: multiples of B, k = 1..min(B-1, n/B)
    int k2max = min(B - 1, n / B);
    for (int k = 1; k <= k2max; ++k) {
        int s = B * k;
        if (s <= n) lengths.push_back(s);
    }
    // Group 3: multiples of B^2, k = 1..n/(B^2)
    int B2 = B * B;
    int k3max = n / B2;
    for (int k = 1; k <= k3max; ++k) {
        int s = B2 * k;
        if (s <= n) lengths.push_back(s);
    }

    // Precompute decomposition pairs s = x + y with x,y already available
    vector<pair<int,int>> pairLen(n + 1, {-1, -1});
    vector<int> avail;
    avail.push_back(1);
    vector<char> existsLen(n + 1, 0);
    existsLen[1] = 1;

    for (int s : lengths) {
        int xFound = -1, yFound = -1;
        for (int x : avail) {
            if (x >= s) continue;
            int y = s - x;
            if (y >= 1 && y < s && y <= n && existsLen[y]) {
                xFound = x;
                yFound = y;
                break;
            }
        }
        if (xFound == -1) {
            // Should not happen for our construction; try simple fallback
            int x = 1, y = s - 1;
            if (y >= 1 && y <= n && existsLen[y]) {
                xFound = x;
                yFound = y;
            } else {
                continue; // Skip unusable length (theoretically never)
            }
        }
        pairLen[s] = {xFound, yFound};
        avail.push_back(s);
        existsLen[s] = 1;
    }

    // Filter lengths that actually got a decomposition
    vector<int> lengthsFiltered;
    lengthsFiltered.reserve(lengths.size());
    for (int s : lengths) {
        if (pairLen[s].first != -1) lengthsFiltered.push_back(s);
    }

    // Count total operations
    long long m = 0;
    for (int s : lengthsFiltered) {
        m += (long long)(n + 1 - s);
    }

    cout << m << '\n';

    // Output operations
    for (int s : lengthsFiltered) {
        int x = pairLen[s].first;
        int y = pairLen[s].second;
        (void)y; // y is not directly needed here
        for (int u = 0; u + s <= n; ++u) {
            int c = u + x;
            int v = u + s;
            cout << u << ' ' << c << ' ' << v << '\n';
        }
    }

    return 0;
}