#include <bits/stdc++.h>
using namespace std;

static const long long LIM_A = 10000;
static const long long LIM_B = 10000;

struct InteractiveSolver {
    int n;
    long long X = 40000; // must be > 2*LIM_B to make centers unique and allow decoding b via modulo
    long long Q = 0;
    unordered_map<long long, long double> cacheF; // y -> f(X,y)

    long double queryF(long long y) {
        auto it = cacheF.find(y);
        if (it != cacheF.end()) return it->second;

        cout << "? " << X << " " << y << "\n" << flush;
        Q++;
        long double ans;
        if (!(cin >> ans)) exit(0);
        cacheF.emplace(y, ans);
        return ans;
    }

    long double queryG(long long t) { // g(t) = f(t+1) - f(t)
        long double f1 = queryF(t + 1);
        long double f0 = queryF(t);
        return f1 - f0;
    }

    pair<int,int> decode_center(long long c) {
        long long rem = c % X;
        if (rem < 0) rem += X; // [0, X-1]
        long long b1 = rem;
        long long b2 = rem - X;

        long long b;
        if (-LIM_B <= b1 && b1 <= LIM_B) b = b1;
        else if (-LIM_B <= b2 && b2 <= LIM_B) b = b2;
        else {
            // fallback: choose signed remainder closest to 0
            b = (rem <= X/2 ? rem : rem - X);
        }

        long long num = c - b;
        long long a = num / X;
        return {(int)a, (int)b};
    }

    vector<long long> recover_centers() {
        long long L = -LIM_A * X - LIM_B;
        long long R =  LIM_A * X + LIM_B;

        // expand a bit to be safely outside possible centers
        long long left = L - 10;
        long long right = R + 10;

        const long double EPS = 1e-5L;

        long long t_cur = left;
        long double g_cur = queryG(t_cur);

        vector<long long> centers;
        centers.reserve(n);

        for (int i = 0; i < n; i++) {
            long long lo = t_cur + 1, hi = right;
            while (lo < hi) {
                long long mid = lo + (hi - lo) / 2;
                long double g_mid = queryG(mid);
                if (g_mid > g_cur + EPS) hi = mid;
                else lo = mid + 1;
            }
            long long c = lo;

            // local correction to ensure c is the first t where g(t) > g_cur + EPS
            while (c > t_cur + 1) {
                long double g_prev = queryG(c - 1);
                if (g_prev > g_cur + EPS) c--;
                else break;
            }
            while (c < right) {
                long double g_here = queryG(c);
                if (g_here > g_cur + EPS) break;
                c++;
            }

            centers.push_back(c);
            g_cur = queryG(c);
            t_cur = c;
        }

        return centers;
    }

    void solve() {
        cin >> n;

        // Ensure X is valid (within territory)
        if (llabs(X) > (long long)1e12) X = 40000;

        vector<long long> centers = recover_centers();

        vector<int> a(n), b(n);
        for (int i = 0; i < n; i++) {
            auto [ai, bi] = decode_center(centers[i]);
            a[i] = ai;
            b[i] = bi;
        }

        cout << "!";
        for (int i = 0; i < n; i++) cout << " " << a[i];
        for (int i = 0; i < n; i++) cout << " " << b[i];
        cout << "\n" << flush;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    InteractiveSolver solver;
    solver.solve();
    return 0;
}