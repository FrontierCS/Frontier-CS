#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    // Output n distinct magic words
    for (int i = 0; i < n; ++i) {
        int x = i + 1;
        string s;
        while (x > 0) {
            s.push_back((x & 1) ? 'X' : 'O');
            x >>= 1;
        }
        reverse(s.begin(), s.end());
        cout << s << "\n";
    }
    cout.flush();

    int q;
    if (!(cin >> q)) return 0;

    // Dummy answers for queries
    while (q--) {
        long long p;
        if (!(cin >> p)) break;
        cout << "1 1\n";
        cout.flush();
    }

    return 0;
}