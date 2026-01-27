#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    auto ask = [&](int i, int j) -> int {
        cout << "? " << i << " " << j << "\n";
        cout.flush();
        int ans;
        if (!(cin >> ans)) exit(0);
        if (ans == -1) exit(0);
        return ans;
    };

    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        int n;
        if (!(cin >> n)) return 0;

        int u = -1;

        // Try to find a certified non-impostor using adjacent pairs
        for (int i = 1; i + 1 <= n; i += 2) {
            int a = ask(i, i + 1);
            int b = ask(i + 1, i);
            if (a == -1 || b == -1) return 0;
            if (a == b) {
                u = i; // both i and i+1 are non-impostors; pick i
                break;
            }
        }

        // If not found and n is odd, the leftover is a non-impostor (only possible for n=3 in valid scenarios)
        if (u == -1 && (n % 2 == 1)) {
            u = n;
        }

        // As a very defensive fallback (shouldn't happen in valid interaction)
        if (u == -1) u = 1;

        int impostor = -1;
        for (int x = 1; x <= n; ++x) {
            if (x == u) continue;
            int a = ask(u, x);
            int b = ask(x, u);
            if (a == -1 || b == -1) return 0;
            if (a != b) {
                impostor = x;
                break;
            }
        }

        if (impostor == -1) impostor = u; // Fallback; shouldn't trigger in valid interaction

        cout << "! " << impostor << "\n";
        cout.flush();
    }

    return 0;
}