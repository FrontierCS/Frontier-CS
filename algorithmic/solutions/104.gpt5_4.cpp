#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;
    const double base = 1.116;

    while (t--) {
        int n;
        if (!(cin >> n)) return 0;

        int qlim = 2 * (int)ceil(log((double)n) / log(base));
        int queries = 0;

        vector<char> run(n + 1, 0);
        vector<char> last(n + 1, 0);
        vector<int> candidates;
        candidates.reserve(n);
        for (int i = 1; i <= n; ++i) candidates.push_back(i);

        while ((int)candidates.size() > 2 && queries < qlim) {
            int m = (int)candidates.size();
            int k = m / 2;
            int r = candidates[k - 1];

            cout << "? " << 1 << " " << r << endl;
            cout.flush();

            int x;
            if (!(cin >> x)) return 0;
            ++queries;

            vector<int> newcand;
            newcand.reserve(m);

            for (int idx = 0; idx < m; ++idx) {
                int i = candidates[idx];
                bool in = (i <= r);
                bool cbit = (x == r - 1) ? in : !in;

                if (run[i] == 0) {
                    run[i] = 1;
                    last[i] = cbit;
                    newcand.push_back(i);
                } else {
                    if (last[i] == cbit) {
                        char rl = run[i] + 1;
                        if (rl >= 3) {
                            // eliminate
                        } else {
                            run[i] = rl;
                            newcand.push_back(i);
                        }
                    } else {
                        last[i] = cbit;
                        run[i] = 1;
                        newcand.push_back(i);
                    }
                }
            }

            candidates.swap(newcand);
        }

        int a1 = 1, a2 = min(2, n);
        if (!candidates.empty()) {
            a1 = candidates[0];
            if ((int)candidates.size() >= 2) a2 = candidates[1];
            else a2 = (a1 == n ? a1 - 1 : a1 + 1);
        }

        cout << "! " << a1 << endl;
        cout.flush();
        int y1; if (!(cin >> y1)) return 0;
        if (y1 == 0) {
            cout << "! " << a2 << endl;
            cout.flush();
            int y2; if (!(cin >> y2)) return 0;
        }
        cout << "#" << endl;
        cout.flush();
    }

    return 0;
}