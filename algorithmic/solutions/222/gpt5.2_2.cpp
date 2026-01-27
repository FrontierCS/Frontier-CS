#include <bits/stdc++.h>
using namespace std;

static const int MAXV = 1'000'000;

static vector<int> posArr(MAXV + 1, -1);
static vector<int> markArr(MAXV + 1, 0);

static int ask(int v, long long x) {
    cout << "? " << v << " " << x << '\n';
    cout.flush();
    int res;
    if (!(cin >> res)) exit(0);
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    int mark = 1;

    for (int tc = 0; tc < n; tc++, mark++) {
        int c = ask(1, 1);

        auto setPos = [&](int v, int p) {
            if (markArr[v] != mark) {
                markArr[v] = mark;
                posArr[v] = p;
            } else {
                posArr[v] = min(posArr[v], p);
            }
        };

        const int m = 1000; // m*m = 1e6
        setPos(c, 0);

        for (int r = 1; r < m; r++) {
            int v = ask(c, r);
            setPos(v, r);
        }

        long long M = -1;
        for (int j = 1; j <= m; j++) {
            int u = ask(c, 1LL * j * m);
            if (markArr[u] == mark) {
                int r = posArr[u];
                long long cand = 1LL * j * m - r;
                if (cand > 0) {
                    M = cand;
                    break;
                }
            }
        }

        if (M <= 0) M = 1'000'000; // should never happen

        long long ans = M;

        vector<long long> primes;
        long long tmp = M;
        for (long long p = 2; p * p <= tmp; p += (p == 2 ? 1 : 2)) {
            if (tmp % p == 0) {
                primes.push_back(p);
                while (tmp % p == 0) tmp /= p;
            }
        }
        if (tmp > 1) primes.push_back(tmp);

        for (long long p : primes) {
            while (ans % p == 0) {
                long long k = ans / p;
                if (k <= 0) break;
                int w = ask(c, k);
                if (w == c) ans = k;
                else break;
            }
        }

        cout << "! " << ans << '\n';
        cout.flush();

        int verdict;
        if (!(cin >> verdict)) return 0;
        if (verdict == -1) return 0;
    }

    return 0;
}