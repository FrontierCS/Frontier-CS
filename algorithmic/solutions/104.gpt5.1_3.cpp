#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;

    mt19937 rng((unsigned)chrono::steady_clock::now().time_since_epoch().count());
    const double BASE = 1.12;

    while (T--) {
        int n;
        if (!(cin >> n)) return 0;

        vector<char> alive(n + 1, 1);
        vector<unsigned char> lenbits(n + 1, 0), last1(n + 1, 0), last2(n + 1, 0);
        int alive_count = n;

        int qmax = (int)(2.0 * log((double)n) / log(BASE));
        if (qmax < 1) qmax = 1;
        int qcnt = 0;

        while (alive_count > 2 && qcnt < qmax) {
            vector<int> al;
            al.reserve(alive_count);
            for (int i = 1; i <= n; ++i)
                if (alive[i]) al.push_back(i);

            int tot = (int)al.size();
            if (tot <= 2) break;
            int k = tot / 2;
            if (k == 0) break;

            int maxStart = tot - k;
            int st = 0;
            if (maxStart > 0) st = (int)(rng() % (maxStart + 1));
            int l = al[st];
            int r = al[st + k - 1];

            cout << "? " << l << " " << r << '\n';
            cout.flush();
            ++qcnt;

            long long x;
            if (!(cin >> x)) return 0;
            int lenRange = r - l + 1;
            int s = (x == lenRange) ? 1 : 0;

            for (int i = 1; i <= n; ++i) {
                if (!alive[i]) continue;
                int P = (i >= l && i <= r) ? 1 : 0;
                int h = s ^ P;
                if (lenbits[i] == 0) {
                    last1[i] = (unsigned char)h;
                    lenbits[i] = 1;
                } else if (lenbits[i] == 1) {
                    last2[i] = last1[i];
                    last1[i] = (unsigned char)h;
                    lenbits[i] = 2;
                } else {
                    if (last1[i] == last2[i] && last1[i] == h) {
                        alive[i] = 0;
                        --alive_count;
                    } else {
                        last2[i] = last1[i];
                        last1[i] = (unsigned char)h;
                    }
                }
            }
        }

        vector<int> cand;
        cand.reserve(alive_count);
        for (int i = 1; i <= n; ++i)
            if (alive[i]) cand.push_back(i);
        if (cand.empty()) cand.push_back(1);

        int first = cand[0];
        cout << "! " << first << '\n';
        cout.flush();
        int y;
        if (!(cin >> y)) return 0;
        if (y == 1) {
            cout << "#\n";
            cout.flush();
            continue;
        } else {
            alive[first] = 0;
        }

        vector<int> cand2;
        for (int i = 1; i <= n; ++i)
            if (alive[i]) cand2.push_back(i);
        int second;
        if (cand2.empty()) {
            if (first == 1) second = 2;
            else second = 1;
        } else {
            second = cand2[0];
        }

        cout << "! " << second << '\n';
        cout.flush();
        if (!(cin >> y)) return 0;

        cout << "#\n";
        cout.flush();
    }

    return 0;
}