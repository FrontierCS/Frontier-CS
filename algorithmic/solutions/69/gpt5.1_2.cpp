#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    // Output n distinct words: "X", "XX", "XXX", ...
    for (int i = 0; i < n; ++i) {
        cout << string(i + 1, 'X') << '\n';
    }
    cout.flush();

    int q;
    if (!(cin >> q)) return 0;
    while (q--) {
        long long p;
        cin >> p;
        // Dummy answers
        cout << 1 << ' ' << 1 << '\n';
        cout.flush();
    }

    return 0;
}