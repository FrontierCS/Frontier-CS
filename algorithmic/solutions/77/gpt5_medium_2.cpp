#include <bits/stdc++.h>
using namespace std;

struct LogSumExp {
    double m;
    double s;
    int cnt;
    LogSumExp(): m(-INFINITY), s(0.0), cnt(0) {}
    inline void add(double x) {
        if (cnt == 0) {
            m = x;
            s = 1.0;
            cnt = 1;
        } else {
            if (x <= m) {
                s += exp(x - m);
            } else {
                s = s * exp(m - x) + 1.0;
                m = x;
                cnt++;
            }
        }
    }
    inline double value() const {
        if (cnt == 0) return -INFINITY;
        return m + log(s);
    }
};

static inline double logsum2(double a, double b) {
    if (a == -INFINITY) return b;
    if (b == -INFINITY) return a;
    if (a < b) swap(a, b);
    return a + log1p(exp(b - a));
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) return 0;

    // Parameters for Randomized Weighted Majority
    const double eta = 0.3; // target 1+eta factor
    const double lbeta = log1p(-eta); // log(1 - eta)

    vector<double> lw(n, 0.0); // log-weights initialized to 0 (weight 1)

    std::mt19937_64 rng(7126872);
    std::uniform_real_distribution<double> dist(0.0, 1.0);

    string s;
    for (int t = 0; t < m; ++t) {
        if (!(cin >> s)) return 0;
        // Compute probability of 1 using log-sum-exp
        LogSumExp agg0, agg1;
        for (int i = 0; i < n; ++i) {
            if (s[i] == '1') agg1.add(lw[i]);
            else agg0.add(lw[i]);
        }
        double lsum1 = agg1.value();
        double lsum0 = agg0.value();
        double ltot = logsum2(lsum1, lsum0);
        int pred;
        if (lsum1 == -INFINITY && lsum0 == -INFINITY) {
            pred = 0; // should not happen as n>=1
        } else if (lsum1 == -INFINITY) {
            pred = 0;
        } else if (lsum0 == -INFINITY) {
            pred = 1;
        } else {
            double p1 = exp(lsum1 - ltot);
            double u = dist(rng);
            pred = (u < p1) ? 1 : 0;
        }

        cout << pred << '\n';
        cout.flush();

        string outcome;
        if (!(cin >> outcome)) return 0;
        char y = outcome[0];

        // Update weights: penalize wrong experts
        for (int i = 0; i < n; ++i) {
            if (s[i] != y) {
                lw[i] += lbeta;
            }
        }
    }

    return 0;
}