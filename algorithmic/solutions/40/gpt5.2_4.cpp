#include <bits/stdc++.h>
using namespace std;

static const int MAX_Q = 200;

struct Solver {
    int qcnt = 0;

    long long ask(const vector<int>& idx) {
        int k = (int)idx.size();
        if (k < 1 || k > 1000) exit(0);
        qcnt++;
        if (qcnt > MAX_Q) exit(0);

        cout << "0 " << k;
        for (int v : idx) cout << ' ' << v;
        cout << '\n';
        cout.flush();

        long long res;
        if (!(cin >> res)) exit(0);
        if (res == -1) exit(0);
        return res;
    }

    void solveCase(int n) {
        qcnt = 0;

        int d = 1; // reference index
        vector<int> diff(n + 1, 0);

        const int B = 8;
        for (int start = 1; start <= n; start += B) {
            int end = min(n, start + B - 1);
            vector<int> pos;
            pos.reserve(end - start + 1);
            for (int i = start; i <= end; i++) pos.push_back(i);

            int m = (int)pos.size();
            vector<int> q;
            q.reserve(3 * ((1 << m) - 1));

            for (int j = 0; j < m; j++) {
                int w = 1 << j;
                for (int t = 0; t < w; t++) {
                    q.push_back(d);
                    q.push_back(pos[j]);
                    q.push_back(d);
                }
            }

            long long r = ask(q);

            for (int j = 0; j < m; j++) {
                diff[pos[j]] = (int)((r >> j) & 1LL);
            }
        }

        int e = -1;
        for (int i = 1; i <= n; i++) {
            if (i != d && diff[i] == 1) {
                e = i;
                break;
            }
        }
        if (e == -1) exit(0); // should not happen due to guarantee

        const int A = 500;
        vector<int> orient;
        orient.reserve(2 * A);
        for (int i = 0; i < A; i++) orient.push_back(d);
        for (int i = 0; i < A; i++) orient.push_back(e);

        long long res = ask(orient);

        char sd = (res > 0 ? '(' : ')');
        string ans(n, '?');
        for (int i = 1; i <= n; i++) {
            if (sd == '(') ans[i - 1] = diff[i] ? ')' : '(';
            else ans[i - 1] = diff[i] ? '(' : ')';
        }

        cout << "1 " << ans << '\n';
        cout.flush();
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    Solver solver;
    int n;
    if (!(cin >> n)) return 0;
    solver.solveCase(n);

    // If multiple test cases are provided (unlikely for this interactive), handle them.
    while (cin >> n) {
        solver.solveCase(n);
    }
    return 0;
}