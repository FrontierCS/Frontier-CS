#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    int T;
    cin >> T;
    for (int test = 0; test < T; ++test) {
        long long n;
        cin >> n;
        long long dc = n / 2;
        vector<long long> bases(3);
        bases[0] = 1;
        long long step = n / 3;
        bases[1] = 1 + step;
        bases[2] = 1 + 2 * step;
        long long s = -1, tt = -1, dd = -1;
        for (int bi = 0; bi < 3; ++bi) {
            long long base = bases[bi];
            long long opp = ((base - 1 + dc) % n + n) % n + 1;
            cout << "? " << base << " " << opp << endl;
            long long res;
            cin >> res;
            if (res < dc) {
                s = base;
                tt = opp;
                dd = res;
                break;
            }
        }
        // Now binary search for m
        long long low = 0;
        long long high = dc;
        while (low < high) {
            long long mid = (low + high + 1) / 2;
            long long p = ((s - 1 + mid) % n + n) % n + 1;
            cout << "? " << s << " " << p << endl;
            long long res;
            cin >> res;
            if (res == mid) {
                low = mid;
            } else {
                high = mid - 1;
            }
        }
        long long m = low;
        long long delta = dc - dd + 1;
        long long half = (delta + 1) / 2;
        long long ii = m - half;
        long long jj = ii + delta;
        long long aa = ((s - 1 + ii) % n + n) % n + 1;
        long long bb = ((s - 1 + jj) % n + n) % n + 1;
        if (aa > bb) swap(aa, bb);
        cout << "! " << aa << " " << bb << endl;
        int r;
        cin >> r;
        if (r == -1) return 0;
    }
    return 0;
}