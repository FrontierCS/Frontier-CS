#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;

    auto flush_out = [](){ cout.flush(); };

    while (t--) {
        int n;
        cin >> n;

        auto ask = [&](int i, int j) -> int {
            cout << "? " << i << " " << j << "\n";
            flush_out();
            int ans;
            if (!(cin >> ans)) exit(0);
            if (ans == -1) exit(0);
            return ans;
        };

        auto answer = [&](int x) {
            cout << "! " << x << "\n";
            flush_out();
        };

        int kn = -1;
        for (int i = 1; i < n; ++i) {
            int a = ask(i, i + 1);
            int b = ask(i + 1, i);
            if (a != b) {
                kn = (a ? i : i + 1);
                break;
            }
        }
        if (kn == -1) {
            int a = ask(n, 1);
            int b = ask(1, n);
            if (a != b) {
                kn = (a ? n : 1);
            } else {
                // Should not happen, but as a fallback, try more pairs
                for (int i = 2; i <= n; ++i) {
                    int x = ask(i - 1, i);
                    int y = ask(i, i - 1);
                    if (x != y) {
                        kn = (x ? i - 1 : i);
                        break;
                    }
                }
                if (kn == -1) kn = 1; // ultimate fallback
            }
        }

        vector<int> s(n + 1, 0);
        s[kn] = 1;
        for (int j = 1; j <= n; ++j) {
            if (j == kn) continue;
            s[j] = ask(kn, j);
        }

        int imp = -1;
        for (int j = 1; j <= n; ++j) {
            if (j == kn) continue;
            if (s[j] == 1) {
                int a = ask(j, kn);
                if (a == 0) {
                    imp = j;
                    break;
                }
            }
        }

        if (imp == -1) {
            // Fallbacks (should not be needed in valid interaction)
            for (int j = 1; j <= n; ++j) {
                if (j != kn && s[j] == 1) { imp = j; break; }
            }
            if (imp == -1) {
                imp = (kn == 1 ? 2 : 1);
            }
        }

        answer(imp);
    }

    return 0;
}