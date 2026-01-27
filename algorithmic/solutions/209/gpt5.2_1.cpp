#include <bits/stdc++.h>
#include <boost/multiprecision/cpp_int.hpp>

using namespace std;
using boost::multiprecision::cpp_int;

static inline cpp_int iabs_cpp(cpp_int x) { return x < 0 ? -x : x; }

static cpp_int gcd_cpp(cpp_int a, cpp_int b) {
    a = iabs_cpp(a);
    b = iabs_cpp(b);
    while (b != 0) {
        cpp_int r = a % b;
        a = b;
        b = r;
    }
    return a;
}

static cpp_int lcm_cpp(const cpp_int& a, const cpp_int& b) {
    if (a == 0 || b == 0) return 0;
    return (a / gcd_cpp(a, b)) * b;
}

struct Frac {
    cpp_int num, den; // den > 0

    Frac(cpp_int n = 0, cpp_int d = 1) : num(std::move(n)), den(std::move(d)) { norm(); }

    void norm() {
        if (den < 0) { den = -den; num = -num; }
        if (num == 0) { den = 1; return; }
        cpp_int g = gcd_cpp(iabs_cpp(num), den);
        num /= g;
        den /= g;
    }

    bool isZero() const { return num == 0; }
};

static inline Frac operator+(const Frac& a, const Frac& b) {
    Frac r(a.num * b.den + b.num * a.den, a.den * b.den);
    return r;
}
static inline Frac operator-(const Frac& a, const Frac& b) {
    Frac r(a.num * b.den - b.num * a.den, a.den * b.den);
    return r;
}
static inline Frac operator*(const Frac& a, const Frac& b) {
    Frac r(a.num * b.num, a.den * b.den);
    return r;
}
static inline Frac operator/(const Frac& a, const Frac& b) {
    Frac r(a.num * b.den, a.den * b.num);
    return r;
}
static inline Frac operator-(const Frac& a) { return Frac(-a.num, a.den); }

static cpp_int int128_to_cpp(__int128 x) {
    bool neg = x < 0;
    unsigned __int128 y = neg ? (unsigned __int128)(-x) : (unsigned __int128)x;
    uint64_t lo = (uint64_t)y;
    uint64_t hi = (uint64_t)(y >> 64);
    cpp_int res = hi;
    res <<= 64;
    res += lo;
    if (neg) res = -res;
    return res;
}

static long long count_nodes_at_dist(int h, int t, int d) {
    int H = h - 1;
    if (d < 1 || d > 2 * H) return 0;
    long long cnt = 0;

    // k = 0: go down only
    if (t + d <= H) cnt += (1LL << d);

    // k = 1..min(t, d-1): go up k, then down into sibling subtree
    int maxk = min(t, d - 1);
    for (int k = 1; k <= maxk; k++) {
        int deepest = t + d - 2 * k; // depth reached in sibling subtree
        if (deepest <= H) {
            int exp = d - k - 1;
            cnt += (1LL << exp);
        }
    }

    // k = d: the ancestor at distance d
    if (d <= t) cnt += 1;

    return cnt;
}

static vector<int> select_pivot_columns(const vector<vector<long long>>& M) {
    int h = (int)M.size();
    int m = (int)M[0].size();
    vector<vector<Frac>> A(h, vector<Frac>(m));
    for (int i = 0; i < h; i++) {
        for (int j = 0; j < m; j++) A[i][j] = Frac(M[i][j], 1);
    }

    vector<int> pivots;
    int row = 0;
    for (int col = 0; col < m && row < h; col++) {
        int sel = -1;
        for (int i = row; i < h; i++) {
            if (!A[i][col].isZero()) { sel = i; break; }
        }
        if (sel == -1) continue;
        if (sel != row) swap(A[sel], A[row]);
        pivots.push_back(col);

        Frac inv = Frac(1, 1) / A[row][col];
        for (int j = col; j < m; j++) A[row][j] = A[row][j] * inv;

        for (int i = 0; i < h; i++) {
            if (i == row) continue;
            if (A[i][col].isZero()) continue;
            Frac factor = A[i][col];
            for (int j = col; j < m; j++) A[i][j] = A[i][j] - factor * A[row][j];
        }
        row++;
    }
    return pivots;
}

static vector<Frac> solve_linear_system(vector<vector<Frac>> aug) {
    // aug: n x (m+1), solve for m vars, assuming unique solvable.
    int n = (int)aug.size();
    int m = (int)aug[0].size() - 1;

    vector<int> where(m, -1);
    int row = 0;
    for (int col = 0; col < m && row < n; col++) {
        int sel = -1;
        for (int i = row; i < n; i++) {
            if (!aug[i][col].isZero()) { sel = i; break; }
        }
        if (sel == -1) continue;
        if (sel != row) swap(aug[sel], aug[row]);
        where[col] = row;

        Frac inv = Frac(1, 1) / aug[row][col];
        for (int j = col; j <= m; j++) aug[row][j] = aug[row][j] * inv;

        for (int i = 0; i < n; i++) {
            if (i == row) continue;
            if (aug[i][col].isZero()) continue;
            Frac factor = aug[i][col];
            for (int j = col; j <= m; j++) aug[i][j] = aug[i][j] - factor * aug[row][j];
        }
        row++;
    }

    vector<Frac> ans(m, Frac(0, 1));
    for (int i = 0; i < m; i++) {
        if (where[i] != -1) ans[i] = aug[where[i]][m];
    }
    return ans;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int h;
    if (!(cin >> h)) return 0;
    int n = (1 << h) - 1;
    int H = h - 1;
    int m = 2 * H; // distances 1..m

    vector<vector<long long>> Nd(h, vector<long long>(m + 1, 0)); // Nd[depth][dist]
    for (int t = 0; t < h; t++) {
        for (int d = 1; d <= m; d++) Nd[t][d] = count_nodes_at_dist(h, t, d);
    }

    vector<vector<long long>> M(h, vector<long long>(m));
    for (int t = 0; t < h; t++) for (int d = 1; d <= m; d++) M[t][d - 1] = Nd[t][d];

    vector<int> piv = select_pivot_columns(M);
    if ((int)piv.size() < h) {
        // Should not happen; fallback to first h columns.
        piv.clear();
        for (int i = 0; i < h && i < m; i++) piv.push_back(i);
    } else {
        piv.resize(h);
    }

    vector<int> dists(h);
    for (int i = 0; i < h; i++) dists[i] = piv[i] + 1;

    vector<vector<Frac>> aug(h, vector<Frac>(h + 1, Frac(0, 1)));
    for (int t = 0; t < h; t++) {
        for (int i = 0; i < h; i++) aug[t][i] = Frac(Nd[t][dists[i]], 1);
        aug[t][h] = Frac(1, 1);
    }
    vector<Frac> coeff = solve_linear_system(aug);

    cpp_int L = 1;
    for (int i = 0; i < h; i++) L = lcm_cpp(L, coeff[i].den);

    vector<cpp_int> icoeff(h);
    for (int i = 0; i < h; i++) {
        cpp_int mult = L / coeff[i].den;
        icoeff[i] = coeff[i].num * mult;
    }

    vector<__int128> totals(h, 0);
    for (int u = 1; u <= n; u++) {
        for (int i = 0; i < h; i++) {
            cout << "? " << u << " " << dists[i] << '\n' << flush;
            long long ans;
            if (!(cin >> ans)) return 0;
            if (ans == -1) return 0;
            totals[i] += ( __int128 )ans;
        }
    }

    cpp_int num = 0;
    for (int i = 0; i < h; i++) {
        cpp_int Ti = int128_to_cpp(totals[i]);
        num += Ti * icoeff[i];
    }

    cpp_int S = num / L;

    cout << "! " << S << '\n' << flush;
    return 0;
}