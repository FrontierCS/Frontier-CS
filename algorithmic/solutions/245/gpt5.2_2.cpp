#include <bits/stdc++.h>
using namespace std;

static int ask(int i, int j) {
    cout << "? " << i << " " << j << '\n';
    cout.flush();
    int r;
    if (!(cin >> r)) exit(0);
    if (r == -1) exit(0);
    return r;
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
        int uv = -1, vu = -1;

        for (int i = 1; i + 1 <= n; i += 2) {
            int a = ask(i, i + 1);
            int b = ask(i + 1, i);
            if (a != b) {
                u = i;
                v = i + 1;
                uv = a;
                vu = b;
                break;
            }
        }

        if (u == -1) {
            // No unequal pair found among disjoint pairs => n must be odd and last is impostor
            int imp = n;
            cout << "! " << imp << '\n';
            cout.flush();
            continue;
        }

        int w = 1;
        if (w == u || w == v) w = 2;
        if (w == u || w == v) w = 3;

        int uw = ask(u, w);
        int vw = ask(v, w);

        int imp;
        if (uv == 1 && vu == 0) {
            imp = (uw == vw) ? u : v;
        } else { // uv == 0 && vu == 1
            imp = (uw == vw) ? v : u;
        }

        cout << "! " << imp << '\n';
        cout.flush();
    }
    return 0;
}