#include <bits/stdc++.h>
using namespace std;

double query(double x, double y) {
    cout << fixed << setprecision(15) << "? " << x << " " << y << endl;
    fflush(stdout);
    double s;
    cin >> s;
    return s;
}

vector<double> get_mus(double x, int n) {
    vector<double> res;
    double max_ab = 10000.0;
    double y_start = -max_ab * x - max_ab - 100.0;
    double delta_init = 100.0;
    double fa = query(x, y_start);
    double fb = query(x, y_start + delta_init);
    double s0 = (fb - fa) / delta_init;
    double y0 = y_start + delta_init;
    double f0 = fb;
    double eps = 1e-8;
    long long max_y = (long long)(max_ab * x + max_ab + 1);
    for (int i = 0; i < n; i++) {
        long long lo = (long long)ceil(y0) + 1;
        long long hi = max_y;
        while (lo < hi) {
            long long m = lo + (hi - lo) / 2;
            double yy = (double)m;
            double ff = query(x, yy);
            double pred = f0 + s0 * (yy - y0);
            if (ff <= pred + eps) {
                lo = m + 1;
            } else {
                hi = m;
            }
        }
        double kink = (double)(lo - 1);
        res.push_back(kink);
        double f_new = f0 + s0 * (kink - y0);
        double y_half = kink + 0.5;
        double f_half = query(x, y_half);
        double new_s = (f_half - f_new) / 0.5;
        y0 = y_half;
        f0 = f_half;
        s0 = new_s;
    }
    return res;
}

int main() {
    int N;
    cin >> N;
    double x1 = 20001.0;
    double x2 = 20002.0;
    vector<double> mus = get_mus(x1, N);
    vector<double> nus = get_mus(x2, N);
    sort(mus.begin(), mus.end());
    sort(nus.begin(), nus.end());
    vector<long long> as(N), bs(N);
    for (int k = 0; k < N; k++) {
        double da = nus[k] - mus[k];
        long long a = llround(da);
        as[k] = a;
        double db = mus[k] - (double)a * x1;
        long long b = llround(db);
        bs[k] = b;
    }
    cout << "!";
    for (auto aa : as) cout << " " << aa;
    for (auto bb : bs) cout << " " << bb;
    cout << endl;
    return 0;
}