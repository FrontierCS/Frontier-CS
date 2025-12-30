#include <bits/stdc++.h>
using namespace std;

// A trivial reference solution:
// outputs 15000 frames of no-op ("OK"), scoring 0.
// This is only to demonstrate the required output format.

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // Consume the entire input (not required, but avoids unused-input surprises).
    // The real solver would parse and plan.
    int n, m;
    if (!(cin >> n >> m)) return 0;
    string row;
    for (int i = 0; i < n; i++) cin >> row;
    int nb;
    cin >> nb;
    for (int i = 0; i < nb; i++) {
        int x, y;
        long long g, c, d, v;
        cin >> x >> y >> g >> c >> d >> v;
    }
    int nr;
    cin >> nr;
    for (int i = 0; i < nr; i++) {
        int x, y;
        long long g, c, d, v;
        cin >> x >> y >> g >> c >> d >> v;
    }
    int k;
    cin >> k;
    for (int i = 0; i < k; i++) {
        int x, y;
        long long G, C;
        cin >> x >> y >> G >> C;
    }

    const int MAX_FRAMES = 15000;
    for (int t = 0; t < MAX_FRAMES; t++) {
        cout << "OK\n";
    }
    return 0;
}


