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

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;

    if (n == 1) {
        cout << "! 0" << endl;
        cout.flush();
        return 0;
    }

    int a = 1, b = 2;
    for (int i = 3; i <= n; ++i) {
        int x = ask(a, i);
        int y = ask(b, i);
        if (x < y) {
            b = i;
        } else {
            a = i;
        }
    }

    int zero = -1;
    for (int k = 1; k <= n; ++k) {
        if (k == a || k == b) continue;
        int x = ask(a, k);
        int y = ask(b, k);
        if (x < y) { zero = a; break; }
        if (y < x) { zero = b; break; }
    }

    if (zero == -1) {
        // Fallback: try more indices in case of repeated ties
        for (int k = 1; k <= n; ++k) {
            if (k == a || k == b) continue;
            int x = ask(a, k);
            int y = ask(b, k);
            if (x < y) { zero = a; break; }
            if (y < x) { zero = b; break; }
        }
    }

    // If still not determined (extremely unlikely), default to a
    if (zero == -1) zero = a;

    vector<int> p(n + 1, -1);
    p[zero] = 0;
    for (int i = 1; i <= n; ++i) {
        if (i == zero) continue;
        p[i] = ask(zero, i);
    }

    cout << "! ";
    for (int i = 1; i <= n; ++i) {
        cout << p[i] << (i == n ? '\n' : ' ');
    }
    cout.flush();
    return 0;
}