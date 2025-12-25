#include <bits/stdc++.h>
using namespace std;

int main() {
    int N;
    cin >> N;
    double MM = 10000.0;
    double XX = 20001.0;
    // initial queries for W and sum_wp
    double y1 = -300000000.0;
    double delta_init = 10000000.0;
    double y2 = y1 + delta_init;
    cout << "? " << XX << " " << y1 << endl;
    cout.flush();
    double f1;
    cin >> f1;
    cout << "? " << XX << " " << y2 << endl;
    cout.flush();
    double f2;
    cin >> f2;
    double slope_init = (f2 - f1) / delta_init;
    double W = -slope_init;
    double sum_wp = f1 + y1 * W;
    double slope_cur = -W;
    double K_cur = sum_wp;
    int cur_min_a = -10001;
    vector<int> as, bs;
    double slope_thresh = 1e-4;
    double eps = 0.4;
    double diff_thresh = 3e-5;
    for(int m = 0; m < N; m++) {
        // binary search for next a
        int lo = cur_min_a + 1;
        int hi = 10000;
        while (lo < hi) {
            int mid = (lo + hi) / 2;
            double y0 = mid * XX + MM;
            cout << "? " << XX << " " << y0 << endl;
            cout.flush();
            double fy0;
            cin >> fy0;
            double y0p = y0 + eps;
            cout << "? " << XX << " " << y0p << endl;
            cout.flush();
            double fyp;
            cin >> fyp;
            double slope = (fyp - fy0) / eps;
            if (slope > slope_cur + slope_thresh) {
                hi = mid;
            } else {
                lo = mid + 1;
            }
        }
        // check lo
        int a_cand = lo;
        double y0 = a_cand * XX + MM;
        cout << "? " << XX << " " << y0 << endl;
        cout.flush();
        double fy0;
        cin >> fy0;
        double y0p = y0 + eps;
        cout << "? " << XX << " " << y0p << endl;
        cout.flush();
        double fyp;
        cin >> fyp;
        double slope = (fyp - fy0) / eps;
        if (slope <= slope_cur + slope_thresh) {
            // error, but assume correct
            continue;
        }
        int a = a_cand;
        // local binary search for p
        double Lp = a * XX - MM;
        double Rp = a * XX + MM;
        double lo_p = Lp;
        double hi_p = Rp;
        int iter_local = 0;
        const int max_local_iter = 60;
        while (hi_p - lo_p > 1e-10 && iter_local < max_local_iter) {
            iter_local++;
            double mid_p = (lo_p + hi_p) / 2.0;
            cout << "? " << XX << " " << mid_p << endl;
            cout.flush();
            double fmid;
            cin >> fmid;
            double exp = slope_cur * mid_p + K_cur;
            double dif = fmid - exp;
            if (dif > diff_thresh) {
                hi_p = mid_p;
            } else {
                lo_p = mid_p;
            }
        }
        double p_approx = (lo_p + hi_p) / 2.0;
        long long a_int = round(p_approx / XX);
        double p_exact = a_int * XX + round(p_approx - a_int * XX);
        long long b_int = round(p_exact - a_int * XX);
        as.push_back((int)a_int);
        bs.push_back((int)b_int);
        // update
        double aa = (double)a_int;
        double ww = 1.0 / sqrt(aa * aa + 1.0);
        double old_exp_p = slope_cur * p_exact + K_cur;
        slope_cur += 2.0 * ww;
        K_cur = old_exp_p - slope_cur * p_exact;
        cur_min_a = (int)a_int;
    }
    // output
    cout << "!";
    for (int aa : as) cout << " " << aa;
    for (int bb : bs) cout << " " << bb;
    cout << endl;
    cout.flush();
    return 0;
}