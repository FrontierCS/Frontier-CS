#include <bits/stdc++.h>
using namespace std;

long long ask(long long v, unsigned long long x) {
    cout << "? " << v << " " << x << endl;
    cout.flush();
    long long res;
    if (!(cin >> res)) exit(0);
    if (res == -1) exit(0);
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    for (int tc = 0; tc < n; ++tc) {
        long long v = 1;
        long long t = ask(v, 1);

        unsigned long long lo = 2, hi = 2;
        while (true) {
            long long r = ask(v, hi);
            if (r == t) break;
            hi <<= 1;
        }

        while (lo < hi) {
            unsigned long long mid = lo + ((hi - lo) >> 1);
            long long r = ask(v, mid);
            if (r == t) {
                hi = mid;
            } else {
                lo = mid + 1;
            }
        }

        unsigned long long s = lo - 1;
        cout << "! " << s << endl;
        cout.flush();

        long long verdict;
        if (!(cin >> verdict)) return 0;
        if (verdict == -1) return 0;
    }
    return 0;
}