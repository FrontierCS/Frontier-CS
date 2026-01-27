#include <bits/stdc++.h>
using namespace std;

pair<long long, int> ask(int l, int r) {
    cout << "? " << l << " " << r << endl;
    cout.flush();
    string sx;
    if (!(cin >> sx)) exit(0);
    if (sx == "-1") exit(0);
    long long x = stoll(sx);
    int f;
    if (!(cin >> f)) exit(0);
    return {x, f};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;
    vector<long long> a(n + 1, 0);

    int i = 1;
    while (i <= n) {
        // Query single element to obtain its value
        auto [v, f1] = ask(i, i);
        (void)f1; // f1 should be 1
        // Find the rightmost index of the run starting at i
        int Rlo = i;
        if (i == n) {
            a[i] = v;
            break;
        }
        long long step = 1;
        int Rhi = n;
        bool need_binsearch = false;

        while (true) {
            if (Rlo == n) {
                // run goes to the end
                break;
            }
            long long nextR = Rlo + step;
            if (nextR > n) nextR = n;
            auto [x, f] = ask(i, (int)nextR);
            int len = (int)nextR - i + 1;
            if (x == v && f == len) {
                // All elements in [i, nextR] are v
                Rlo = (int)nextR;
                step <<= 1;
                if (Rlo == n) break;
            } else {
                // We've crossed beyond the run; binary search between (Rlo, nextR]
                Rhi = (int)nextR;
                need_binsearch = true;
                break;
            }
        }

        int Rv = Rlo;
        if (need_binsearch) {
            int l = Rlo + 1, r = Rhi;
            while (l <= r) {
                int mid = (l + r) >> 1;
                auto [x2, f2] = ask(i, mid);
                int len2 = mid - i + 1;
                if (x2 == v && f2 == len2) {
                    Rv = mid;
                    l = mid + 1;
                } else {
                    r = mid - 1;
                }
            }
        }

        for (int t = i; t <= Rv; ++t) a[t] = v;
        i = Rv + 1;
    }

    cout << "! ";
    for (int j = 1; j <= n; ++j) {
        if (j > 1) cout << ' ';
        cout << a[j];
    }
    cout << endl;
    cout.flush();

    return 0;
}