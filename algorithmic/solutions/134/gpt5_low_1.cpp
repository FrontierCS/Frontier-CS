#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    long long n;
    if (!(cin >> n)) return 0;

    auto ask = [&](long long x, long long y) -> int {
        cout << x << " " << y << "\n";
        cout.flush();
        int r;
        if (!(cin >> r)) exit(0);
        if (r == 0) exit(0);
        return r;
    };

    long long lx = 1, rx = n, ly = 1, ry = n;

    while (true) {
        if (lx == rx && ly == ry) {
            int r = ask(lx, ly);
            if (r == 0) return 0;
            // If not 0, continue just in case interactor expects more, but try to break.
            return 0;
        }

        if ((rx - lx) >= (ry - ly)) {
            long long midx = lx + (rx - lx) / 2;
            int r = ask(midx, ly);
            if (r == 1) {
                lx = midx + 1;
            } else if (r == 3) {
                if (midx > 1) rx = midx - 1;
                else rx = 0; // Should not happen, but guard
            } else if (r == 2) {
                if (ly < n) ly++;
            }
        } else {
            long long midy = ly + (ry - ly) / 2;
            int r = ask(lx, midy);
            if (r == 2) {
                ly = midy + 1;
            } else if (r == 3) {
                if (midy > 1) ry = midy - 1;
                else ry = 0;
            } else if (r == 1) {
                if (lx < n) lx++;
            }
        }
    }

    return 0;
}