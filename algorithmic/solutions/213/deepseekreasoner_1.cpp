#include <bits/stdc++.h>
using namespace std;

struct ShiftSolver {
    int n, x;
    vector<int> a;
    vector<int> pos; // position of value i
    vector<tuple<int, int, int>> ops; // l, r, dir

    ShiftSolver(int n) : n(n) {
        a.resize(n+1);
        pos.resize(n+1);
        x = max(2, n/2); // chosen x
    }

    void read(istream& in) {
        for (int i = 1; i <= n; ++i) {
            in >> a[i];
            pos[a[i]] = i;
        }
    }

    // apply cyclic shift on segment [l, r] (length = r-l+1)
    // dir = 0: left shift, dir = 1: right shift
    void apply(int l, int r, int dir) {
        ops.emplace_back(l, r, dir);
        if (dir == 0) { // left shift
            int tmp = a[l];
            for (int i = l; i < r; ++i) {
                a[i] = a[i+1];
                pos[a[i]] = i;
            }
            a[r] = tmp;
            pos[tmp] = r;
        } else { // right shift
            int tmp = a[r];
            for (int i = r; i > l; --i) {
                a[i] = a[i-1];
                pos[a[i]] = i;
            }
            a[l] = tmp;
            pos[tmp] = l;
        }
    }

    void solve() {
        for (int i = 1; i <= n; ++i) {
            int p = pos[i];
            if (p == i) continue;

            if (i <= n - x + 1) {
                // can use segment starting at i
                if (p <= i + x - 1) {
                    // within target segment
                    int d = p - i;
                    if (d <= x - d) {
                        for (int k = 0; k < d; ++k)
                            apply(i, i + x - 1, 0);
                    } else {
                        for (int k = 0; k < x - d; ++k)
                            apply(i, i + x - 1, 1);
                    }
                } else {
                    // p > i + x - 1, need to move left
                    while (p > i + x - 1) {
                        int l = p - (x - 1);
                        apply(l, l + x - 1, 0);
                        p--;
                    }
                    // now p in [i, i+x-1]
                    int d = p - i;
                    if (d <= x - d) {
                        for (int k = 0; k < d; ++k)
                            apply(i, i + x - 1, 0);
                    } else {
                        for (int k = 0; k < x - d; ++k)
                            apply(i, i + x - 1, 1);
                    }
                }
            } else {
                // i > n - x + 1, use segment ending at i
                if (p < i - x + 1) {
                    // p is left of target segment, move right
                    while (p < i - x + 1) {
                        apply(p, p + x - 1, 1);
                        p++;
                    }
                    // now p in [i-x+1, i]
                    int d = i - p;
                    if (d <= x - d) {
                        for (int k = 0; k < d; ++k)
                            apply(i - x + 1, i, 1);
                    } else {
                        for (int k = 0; k < x - d; ++k)
                            apply(i - x + 1, i, 0);
                    }
                } else if (p > i) {
                    // p is right of i, move left
                    while (p > i) {
                        apply(p - x + 1, p, 0);
                        p--;
                    }
                } else {
                    // p in [i-x+1, i] and p != i
                    int d = i - p;
                    if (d <= x - d) {
                        for (int k = 0; k < d; ++k)
                            apply(i - x + 1, i, 1);
                    } else {
                        for (int k = 0; k < x - d; ++k)
                            apply(i - x + 1, i, 0);
                    }
                }
            }
        }
    }

    void output(ostream& out) {
        out << x << "\n";
        out << ops.size() << "\n";
        for (auto [l, r, dir] : ops)
            out << l << " " << r << " " << dir << "\n";
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;
    ShiftSolver solver(n);
    solver.read(cin);
    solver.solve();
    solver.output(cout);

    return 0;
}