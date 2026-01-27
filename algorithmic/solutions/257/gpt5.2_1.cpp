#include <bits/stdc++.h>
using namespace std;

static const long long UNKNOWN = LLONG_MIN;

struct Interactor {
    vector<long long> cache;
    int n;

    Interactor(int n_) : cache(n_ + 1, UNKNOWN), n(n_) {}

    pair<long long,int> ask(int l, int r) {
        cout << "? " << l << " " << r << "\n";
        cout.flush();
        long long x;
        if (!(cin >> x)) exit(0);
        if (x == -1) exit(0);
        int f;
        cin >> f;
        return {x, f};
    }

    long long getVal(int i) {
        if (cache[i] != UNKNOWN) return cache[i];
        auto [x, f] = ask(i, i);
        cache[i] = x;
        return x;
    }

    int findEnd(int pos, long long v) {
        int high = pos;
        int step = 1;

        while (true) {
            long long nxtIdxLL = 1LL * pos + step;
            if (nxtIdxLL > n) break;
            int nxtIdx = (int)nxtIdxLL;
            if (getVal(nxtIdx) == v) {
                high = nxtIdx;
                step <<= 1;
            } else {
                break;
            }
        }

        int right = min(n, pos + step - 1);
        int left = high + 1;

        while (left <= right) {
            int mid = left + (right - left) / 2;
            if (getVal(mid) == v) {
                high = mid;
                left = mid + 1;
            } else {
                right = mid - 1;
            }
        }
        return high;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    Interactor it(n);
    vector<long long> a(n + 1, 0);

    int pos = 1;
    while (pos <= n) {
        long long v = it.getVal(pos);
        int endPos = it.findEnd(pos, v);
        for (int i = pos; i <= endPos; i++) a[i] = v;
        pos = endPos + 1;
    }

    cout << "!";
    for (int i = 1; i <= n; i++) cout << " " << a[i];
    cout << "\n";
    cout.flush();
    return 0;
}