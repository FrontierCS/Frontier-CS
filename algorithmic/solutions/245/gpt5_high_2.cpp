#include <bits/stdc++.h>
using namespace std;

int ask(int i, int j) {
    cout << "? " << i << " " << j << endl;
    cout.flush();
    int x;
    if (!(cin >> x)) exit(0);
    if (x == -1) exit(0);
    return x;
}

void answer(int x) {
    cout << "! " << x << endl;
    cout.flush();
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        int n;
        cin >> n;

        int u = -1, v = -1;
        for (int i = 1; i <= n - 1; ++i) {
            int a = ask(i, i + 1);
            int b = ask(i + 1, i);
            if (a != b) {
                u = i; v = i + 1;
                break;
            }
        }

        if (u == -1) {
            // Should not happen if there is exactly one impostor; fallback
            answer(1);
            continue;
        }

        int x = 1;
        if (x == u || x == v) x = (n >= 3 ? 3 : 2);
        if (x == u || x == v) {
            for (int i = 1; i <= n; ++i) {
                if (i != u && i != v) { x = i; break; }
            }
        }

        int p = ask(u, x);
        int q = ask(x, u);
        int imp = (p != q) ? u : v;
        answer(imp);
    }
    return 0;
}