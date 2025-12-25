#include <bits/stdc++.h>
using namespace std;

int computeLimit(int n) {
    const double base = 1.116;
    int k = 0;
    double cur = 1.0;
    while (cur < (double)n) {
        cur *= base;
        ++k;
    }
    return 2 * k;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        int n;
        if (!(cin >> n)) return 0;

        int qLimit = computeLimit(n);
        int qUsed = 0;

        vector<int> last1(n + 1, -1), last2(n + 1, -1);
        vector<char> alive(n + 1, 1);

        auto buildAlive = [&]() {
            vector<int> v;
            v.reserve(n);
            for (int i = 1; i <= n; ++i)
                if (alive[i]) v.push_back(i);
            return v;
        };

        while (true) {
            auto aliveIdx = buildAlive();
            if ((int)aliveIdx.size() <= 2) break;
            if (qUsed >= qLimit) break;

            int m = (int)aliveIdx.size();
            int l, r;
            if (m >= 4) {
                int q1 = aliveIdx[m / 4];
                int q3 = aliveIdx[(3 * m) / 4];
                l = q1;
                r = q3;
            } else { // m == 3
                l = aliveIdx[1];
                r = aliveIdx[1];
            }

            if (l < 1) l = 1;
            if (r > n) r = n;
            if (l > r) swap(l, r);

            cout << "? " << l << " " << r << "\n";
            cout.flush();

            int x;
            if (!(cin >> x)) return 0;
            int len = r - l + 1;
            int B = (x == len) ? 1 : 0;
            ++qUsed;

            for (int a = 1; a <= n; ++a) {
                if (!alive[a]) continue;
                int E = (l <= a && a <= r) ? 1 : 0;
                int H = B ^ E;
                if (last2[a] != -1 && last1[a] != -1 &&
                    last2[a] == last1[a] && last1[a] == H) {
                    alive[a] = 0;
                    continue;
                }
                last2[a] = last1[a];
                last1[a] = H;
            }
        }

        auto aliveIdx = buildAlive();

        if (aliveIdx.empty()) {
            int first = 1;
            cout << "! " << first << "\n";
            cout.flush();
            int y;
            if (!(cin >> y)) return 0;
            if (y == 1) {
                cout << "#\n";
                cout.flush();
            } else {
                int second = 2;
                cout << "! " << second << "\n";
                cout.flush();
                int y2;
                if (!(cin >> y2)) return 0;
                cout << "#\n";
                cout.flush();
            }
        } else if (aliveIdx.size() == 1) {
            int first = aliveIdx[0];
            cout << "! " << first << "\n";
            cout.flush();
            int y;
            if (!(cin >> y)) return 0;
            if (y == 1) {
                cout << "#\n";
                cout.flush();
            } else {
                int second = (first == 1 ? 2 : 1);
                cout << "! " << second << "\n";
                cout.flush();
                int y2;
                if (!(cin >> y2)) return 0;
                cout << "#\n";
                cout.flush();
            }
        } else {
            int first = aliveIdx[0];
            int second = aliveIdx[1];
            cout << "! " << first << "\n";
            cout.flush();
            int y;
            if (!(cin >> y)) return 0;
            if (y == 1) {
                cout << "#\n";
                cout.flush();
            } else {
                cout << "! " << second << "\n";
                cout.flush();
                int y2;
                if (!(cin >> y2)) return 0;
                cout << "#\n";
                cout.flush();
            }
        }
    }

    return 0;
}