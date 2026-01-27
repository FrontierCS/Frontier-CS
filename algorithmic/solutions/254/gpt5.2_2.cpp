#include <bits/stdc++.h>
using namespace std;

static void die() {
    exit(0);
}

struct InteractiveSolver {
    int n, N, k;
    vector<int> S;            // size k = n-1 (intended slowest)
    vector<int> fillers;      // size n-2, subset of S
    vector<vector<int8_t>> cmp; // cmp[a][b]=1 if a faster than b, -1 if slower, 0 unknown

    int ask(const vector<int>& v) {
        cout << "?";
        for (int x : v) cout << " " << x;
        cout << "\n";
        cout.flush();

        int p;
        if (!(cin >> p)) die();
        if (p == -1) die();
        return p;
    }

    void init(int nn) {
        n = nn;
        N = n * n;
        k = n - 1;
        S.clear();
        S.reserve(k);
        for (int i = 1; i <= k; i++) S.push_back(i);

        // Find k slowest using "keep k smallest with max query" in one pass
        for (int x = k + 1; x <= N; x++) {
            vector<int> q = S;
            q.push_back(x);
            int w = ask(q);
            if (w != x) {
                for (int &s : S) {
                    if (s == w) {
                        s = x;
                        break;
                    }
                }
            }
        }

        fillers.clear();
        for (int i = 0; i < n - 2; i++) fillers.push_back(S[i]);

        cmp.assign(N + 1, vector<int8_t>(N + 1, 0));
    }

    bool faster(int a, int b) {
        if (a == b) return false;
        int8_t &c = cmp[a][b];
        if (c != 0) return c > 0;

        vector<int> q;
        q.reserve(n);
        q.push_back(a);
        q.push_back(b);
        for (int f : fillers) q.push_back(f);

        if ((int)q.size() != n) {
            // Fallback (should not be needed)
            vector<char> used(N + 1, false);
            for (int x : q) used[x] = true;
            for (int s : S) {
                if (!used[s]) {
                    q.push_back(s);
                    used[s] = true;
                    if ((int)q.size() == n) break;
                }
            }
        }

        int w = ask(q);
        if (w == a) {
            cmp[a][b] = 1;
            cmp[b][a] = -1;
            return true;
        } else {
            cmp[a][b] = -1;
            cmp[b][a] = 1;
            return false;
        }
    }

    vector<int> solve_case() {
        vector<char> inS(N + 1, false);
        for (int s : S) inS[s] = true;

        vector<int> R;
        R.reserve(N - k);
        for (int i = 1; i <= N; i++) if (!inS[i]) R.push_back(i);

        // Iterative merge sort in descending order by speed
        int m = (int)R.size();
        vector<int> a = R, tmp(m);

        for (int width = 1; width < m; width <<= 1) {
            for (int i = 0; i < m; i += (width << 1)) {
                int l = i;
                int mid = min(i + width, m);
                int r = min(i + (width << 1), m);

                int p = l, q = mid, t = l;
                while (p < mid || q < r) {
                    if (q == r || (p < mid && faster(a[p], a[q]))) tmp[t++] = a[p++];
                    else tmp[t++] = a[q++];
                }
            }
            a.swap(tmp);
        }
        return a;
    }

    void answer(const vector<int>& ord) {
        cout << "!";
        for (int x : ord) cout << " " << x;
        cout << "\n";
        cout.flush();
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;

    InteractiveSolver solver;
    while (t--) {
        int n;
        cin >> n;
        solver.init(n);
        vector<int> ans = solver.solve_case();
        solver.answer(ans);
    }
    return 0;
}