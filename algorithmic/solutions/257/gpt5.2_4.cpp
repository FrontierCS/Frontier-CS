#include <bits/stdc++.h>
using namespace std;

struct Resp {
    long long x;
    int f;
};

static int n;

static Resp ask(int l, int r) {
    cout << "? " << l << " " << r << '\n';
    cout.flush();

    string s;
    if (!(cin >> s)) exit(0);
    if (s == "-1") exit(0);
    long long x = stoll(s);
    int f;
    cin >> f;
    return {x, f};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> n;
    vector<long long> a(n + 1);

    int pos = 1;
    while (pos <= n) {
        long long v;
        int len;

        if (pos == n) {
            auto r = ask(pos, pos);
            v = r.x;
            len = 1;
        } else {
            auto r = ask(pos, pos + 1);
            v = r.x;
            if (r.f == 1) {
                len = 1;
            } else {
                int m = 2; // confirmed prefix length of value v
                while (true) {
                    int rem = n - pos + 1;
                    int nextLen = (int)min<long long>(2LL * m, rem);
                    int rrIdx = pos + nextLen - 1;
                    auto rr = ask(pos, rrIdx);

                    if (rr.f < nextLen) {
                        len = rr.f;
                        break;
                    }
                    if (nextLen == rem) {
                        len = rem;
                        break;
                    }
                    m = nextLen;
                }
            }
        }

        for (int i = pos; i < pos + len; i++) a[i] = v;
        pos += len;
    }

    cout << "!";
    for (int i = 1; i <= n; i++) cout << ' ' << a[i];
    cout << '\n';
    cout.flush();
    return 0;
}