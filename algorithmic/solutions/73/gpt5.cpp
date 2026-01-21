#include <bits/stdc++.h>
using namespace std;

struct Solver {
    int n;
    int N;
    vector<signed char> invCache; // cache for I(l,r)
    vector<signed char> pairCache; // cache for x_{i,j} with i<j
    long long queryCount = 0;

    Solver(int n_) : n(n_), N(n_ + 1), invCache((n_ + 1) * (n_ + 1), -1), pairCache((n_ + 1) * (n_ + 1), -1) {}

    inline int idxLR(int l, int r) const {
        return l * N + r;
    }

    int inv_query(int l, int r) {
        if (l >= r) return 0;
        int idx = idxLR(l, r);
        if (invCache[idx] != -1) return invCache[idx];
        cout << "0 " << l << " " << r << endl;
        cout.flush();
        int res;
        if (!(cin >> res)) {
            // If interactor fails, exit
            exit(0);
        }
        res &= 1;
        invCache[idx] = (signed char)res;
        queryCount++;
        return res;
    }

    int pair_x(int i, int j) { // i < j, returns x_{i,j} = [p_i > p_j]
        int idx = idxLR(i, j);
        if (pairCache[idx] != -1) return pairCache[idx];

        int a = inv_query(i, j);
        int b = inv_query(i + 1, j);
        int c = inv_query(i, j - 1);
        int d = inv_query(i + 1, j - 1);
        int val = a ^ b ^ c ^ d;
        pairCache[idx] = (signed char)val;
        return val;
    }

    bool less_by_value(int u, int v) {
        if (u == v) return false;
        if (u < v) {
            int x = pair_x(u, v); // 1 if p_u > p_v
            return x == 0;
        } else {
            int x = pair_x(v, u); // 1 if p_v > p_u
            return x == 1;
        }
    }

    void run() {
        vector<int> idxs(n);
        for (int i = 0; i < n; ++i) idxs[i] = i + 1;

        stable_sort(idxs.begin(), idxs.end(), [&](int a, int b) {
            return less_by_value(a, b);
        });

        vector<int> ans(n + 1, 0);
        for (int i = 0; i < n; ++i) {
            ans[idxs[i]] = i + 1;
        }

        cout << "1";
        for (int i = 1; i <= n; ++i) {
            cout << " " << ans[i];
        }
        cout << endl;
        cout.flush();
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    if (!(cin >> n)) return 0;
    Solver solver(n);
    solver.run();
    return 0;
}