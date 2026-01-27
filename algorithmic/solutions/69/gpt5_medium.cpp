#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    // Print n distinct words over {X, O}
    for (int i = 1; i <= n; ++i) {
        string s = "X";
        s.append(i, 'O');
        cout << s << "\n";
    }
    cout.flush();

    int q;
    if (!(cin >> q)) return 0;
    while (q--) {
        long long p;
        cin >> p;
        // Dummy response (placeholder)
        cout << 1 << " " << 1 << "\n";
        cout.flush();
    }

    return 0;
}