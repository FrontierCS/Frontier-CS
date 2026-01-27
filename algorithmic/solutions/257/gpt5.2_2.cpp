#include <bits/stdc++.h>
using namespace std;

struct Resp {
    long long x;
    int f;
};

static int n;

static Resp ask(int l, int r) {
    cout << "? " << l << " " << r << "\n";
    cout.flush();

    Resp res;
    if (!(cin >> res.x)) exit(0);
    if (res.x == -1) exit(0);
    cin >> res.f;
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> n;
    vector<long long> a(n + 1);

    int pos = 1;
    while (pos <= n) {
        Resp cur = ask(pos, pos);
        long long val = cur.x;

        long long len = 1;
        int end = pos;

        while (true) {
            long long nextLen = len * 2;
            long long rll = (long long)pos + nextLen - 1;
            int r = (rll > n ? n : (int)rll);

            Resp res = ask(pos, r);

            if (res.x != val) {
                // This should not happen with the doubling scheme; fallback to avoid undefined behavior.
                // Find end via point-wise binary search.
                int L = pos, R = n + 1;
                while (L + 1 < R) {
                    int mid = L + (R - L) / 2;
                    Resp t = ask(mid, mid);
                    if (t.x == val) L = mid;
                    else R = mid;
                }
                end = L;
                break;
            }

            int segLen = r - pos + 1;
            if (res.f < segLen) {
                int runLen = res.f;
                end = pos + runLen - 1;
                break;
            }

            if (r == n) {
                end = n;
                break;
            }

            len = nextLen;
        }

        for (int i = pos; i <= end; i++) a[i] = val;
        pos = end + 1;
    }

    cout << "!";
    for (int i = 1; i <= n; i++) cout << " " << a[i];
    cout << "\n";
    cout.flush();
    return 0;
}