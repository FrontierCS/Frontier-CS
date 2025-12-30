#include <bits/stdc++.h>
using namespace std;

int main() {
    long long n;
    cin >> n;
    long long la = 1, ra = n, lb = 1, rb = n;
    while (true) {
        if (la == ra && lb == rb) {
            cout << la << " " << lb << endl;
            int res;
            cin >> res;
            return 0;
        }
        long long sa = ra - la + 1;
        long long sb = rb - lb + 1;
        if (sa >= sb) {
            // probe a
            long long offset = (ra - la) / 2;
            long long x = la + offset;
            long long y = lb;
            cout << x << " " << y << endl;
            int res;
            cin >> res;
            if (res == 0) return 0;
            if (res == 1) {
                la = x + 1;
            } else if (res == 3) {
                ra = x - 1;
            } else if (res == 2) {
                lb = lb + 1;
            }
        } else {
            // probe b
            long long offset = (rb - lb) / 2;
            long long y = lb + offset;
            long long x = la;
            cout << x << " " << y << endl;
            int res;
            cin >> res;
            if (res == 0) return 0;
            if (res == 2) {
                lb = y + 1;
            } else if (res == 3) {
                rb = y - 1;
            } else if (res == 1) {
                la = la + 1;
            }
        }
        if (la > ra || lb > rb) {
            // should not happen
            break;
        }
    }
    return 0;
}