#include <bits/stdc++.h>
using namespace std;

static int ask(int i, int j) {
    cout << "? " << i << " " << j << '\n' << flush;
    int r;
    if (!(cin >> r)) exit(0);
    if (r == -1) exit(0);
    return r;
}

static void answer(int x) {
    cout << "! " << x << '\n' << flush;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        int n;
        cin >> n;

        int x = -1, y = -1;

        for (int i = 1; i + 1 <= n; i += 2) {
            int a = i, b = i + 1;
            int r1 = ask(a, b);
            int r2 = ask(b, a);
            if (r1 != r2) {
                x = a; y = b;
                break;
            }
        }

        if (x == -1) {
            // This can only happen when n is odd; the unpaired player must be the impostor.
            answer(n);
            continue;
        }

        int z = 1;
        if (z == x || z == y) z = 2;
        if (z == x || z == y) z = 3;

        int r1 = ask(x, z);
        int r2 = ask(z, x);

        int imp = (r1 != r2) ? x : y;
        answer(imp);
    }
    return 0;
}