#include <bits/stdc++.h>
using namespace std;

static const double BASE = 1.116;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;

    auto ask = [&](int l, int r, long long &qcount) -> int {
        cout << "? " << l << " " << r << "\n";
        cout.flush();
        int x;
        if (!(cin >> x)) exit(0);
        qcount++;
        return x;
    };

    auto calibrate = [&](int n, long long &qcount) -> int {
        int x = ask(1, n, qcount);
        // Return 0 for honest, 1 for dishonest
        return (x == n - 1) ? 0 : 1;
    };

    auto decideInRange = [&](int l, int r, int n, long long &qcount, long long maxQ) -> int {
        // returns 1 if absent in [l, r], else 0
        int len = r - l + 1;
        int tries = 0;
        while (qcount + 5 <= maxQ && tries < 30) {
            tries++;
            int s1 = calibrate(n, qcount);
            int x1 = ask(l, r, qcount);
            int b1 = (x1 == len - 1) ? 1 : 0;
            int s2 = calibrate(n, qcount);
            if (s1 == s2) {
                int sQ = 1 - s1;
                return b1 ^ sQ;
            } else {
                int x2 = ask(l, r, qcount);
                int b2 = (x2 == len - 1) ? 1 : 0;
                int s3 = calibrate(n, qcount);
                int s4 = calibrate(n, qcount);
                if (s3 == s4) {
                    int sQ2 = 1 - s3;
                    return b2 ^ sQ2;
                }
            }
        }
        // Fallback: attempt minimal bracket
        if (qcount + 3 <= maxQ) {
            int s1 = calibrate(n, qcount);
            int x1 = ask(l, r, qcount);
            int b1 = (x1 == (r - l + 1) - 1) ? 1 : 0;
            int s2 = calibrate(n, qcount);
            if (s1 == s2) {
                int sQ = 1 - s1;
                return b1 ^ sQ;
            }
        }
        // Last resort: assume honest for this query
        int x = ask(l, r, qcount);
        return (x == (r - l + 1) - 1) ? 1 : 0;
    };

    for (int _ = 0; _ < t; _++) {
        int n;
        if (!(cin >> n)) return 0;

        long long qcount = 0;
        long long maxQ = (long long)ceil(2.0 * (log((double)n) / log(BASE)));

        int L = 1, R = n;
        while (L < R) {
            int mid = L + (R - L) / 2;
            if (qcount >= maxQ - 10) break; // safety
            int inLeft = decideInRange(L, mid, n, qcount, maxQ);
            if (inLeft) R = mid;
            else L = mid + 1;
        }

        int candidate = L;
        // First mark
        cout << "! " << candidate << "\n";
        cout.flush();
        int ok;
        if (!(cin >> ok)) return 0;
        if (ok == 1) {
            cout << "#\n";
            cout.flush();
            continue;
        } else {
            // Second attempt: pick neighbor if possible, else 1
            int candidate2 = (candidate > 1) ? candidate - 1 : min(n, candidate + 1);
            if (candidate2 == candidate) candidate2 = (candidate % n) + 1;
            cout << "! " << candidate2 << "\n";
            cout.flush();
            int ok2;
            if (!(cin >> ok2)) return 0;
            cout << "#\n";
            cout.flush();
        }
    }

    return 0;
}