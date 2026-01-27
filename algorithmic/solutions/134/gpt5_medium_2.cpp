#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    long long n;
    if (!(cin >> n)) return 0;

    auto ask = [&](long long x, long long y) -> long long {
        cout << x << " " << y << endl;
        cout.flush();
        long long r;
        if (!(cin >> r)) exit(0);
        if (r == 0) exit(0);
        return r;
    };

    long long la = 1, ra = n, lb = 1, rb = n;

    while (true) {
        // If narrowed down to a single point, confirm and exit
        if (la == ra && lb == rb) {
            ask(la, lb); // should receive 0 and exit
            // If not, loop continues (but theoretically impossible)
        }

        long long x = la + (ra - la) / 2;
        long long y = lb + (rb - lb) / 2;

        long long r = ask(x, y);
        if (r == 1) {
            la = max(la, x + 1);
        } else if (r == 2) {
            lb = max(lb, y + 1);
        } else if (r == 3) {
            // Disambiguate using (x, rb): here, resp can be 1 (x<a) or 3 (x>a)
            long long r2 = ask(x, rb);
            if (r2 == 1) {
                // x < a, thus previous 3 was due to b <= y-1
                la = max(la, x + 1);
                rb = min(rb, y - 1);
            } else if (r2 == 3) {
                // x > a
                ra = min(ra, x - 1);
            } else if (r2 == 0) {
                // Found exact answer and exited in ask
                return 0;
            } else {
                // Unexpected per protocol; fail-safe: do nothing
            }
        } else if (r == 0) {
            // ask already exits on 0, but included for completeness
            return 0;
        }
        // Ensure bounds remain valid
        la = max(la, 1LL);
        lb = max(lb, 1LL);
        ra = min(ra, n);
        rb = min(rb, n);
        if (la > ra) la = ra;
        if (lb > rb) lb = rb;
    }

    return 0;
}