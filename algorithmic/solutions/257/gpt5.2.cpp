#include <bits/stdc++.h>
using namespace std;

static inline pair<long long,int> ask(int l, int r) {
    cout << "? " << l << " " << r << '\n' << flush;
    long long x;
    if (!(cin >> x)) exit(0);
    if (x == -1) exit(0);
    int f;
    cin >> f;
    return {x, f};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;

    vector<long long> a(n + 1);

    int i = 1;
    while (i <= n) {
        if (i == n) {
            auto res = ask(i, i);
            a[i] = res.first;
            break;
        }

        auto res = ask(i, i + 1);
        long long val = res.first;
        int f = res.second;

        if (f == 1) {
            a[i] = val;
            i++;
            continue;
        }

        // f == 2 => at least two equal elements starting at i
        if (i + 1 == n) {
            a[i] = a[i + 1] = val;
            break;
        }

        int prevLen = 2; // known constant length starting at i
        while (true) {
            long long len = 1LL * prevLen * 2;
            int r = i + (int)len - 1;
            if (r > n) r = n;

            auto res2 = ask(i, r);
            int m = r - i + 1;

            if (res2.second == m) {
                // still constant
                val = res2.first;
                prevLen = m;
                if (r == n) {
                    for (int p = i; p <= n; p++) a[p] = val;
                    i = n + 1;
                    break;
                }
            } else {
                // guaranteed (due to sorted array and m <= 2*prevLen <= 2*t) that mode is the first value, and f is run length t
                val = res2.first;
                int t = res2.second;
                int endPos = i + t - 1;
                for (int p = i; p <= endPos; p++) a[p] = val;
                i = endPos + 1;
                break;
            }
        }
    }

    cout << "!";
    for (int idx = 1; idx <= n; idx++) cout << ' ' << a[idx];
    cout << '\n' << flush;

    return 0;
}