#include "testlib.h"
#include <bits/stdc++.h>
using namespace std;

static double computeEnergy(
    int r,
    const vector<int>& eu, const vector<int>& ev, const vector<long long>& ew,
    const vector<long long>& p, const vector<long long>& q,
    const vector<long long>& bay)
{
    double total = 0.0;
    for (int i = 0; i < r; i++) {
        int u = eu[i], v = ev[i];
        long long d = llabs(bay[u] - bay[v]);
        if (d == 0) continue;

        __int128 twoqu  = (__int128)2 * q[u];
        __int128 twoquv = (__int128)2 * q[v];
        __int128 pd_u   = ((__int128)p[u] * (__int128)d) % twoqu;
        __int128 pd_v   = ((__int128)p[v] * (__int128)d) % twoquv;

        double angle_u = M_PI * (double)(long long)pd_u / (double)(long long)q[u];
        double angle_v = M_PI * (double)(long long)pd_v / (double)(long long)q[v];

        double val_u = fabs(sin(angle_u));
        double val_v = fabs(sin(angle_v));

        total += (double)ew[i] * val_u * val_v;
    }
    return total;
}

int main(int argc, char* argv[]) {
    registerTestlibCmd(argc, argv);

    int t = inf.readInt();

    double total_score_ratio = 0.0;

    for (int tc = 0; tc < t; tc++) {
        int n       = inf.readInt();
        long long m = inf.readLong();
        int r       = inf.readInt();

        vector<long long> p(n + 1), q(n + 1);
        for (int i = 1; i <= n; i++) {
            p[i] = inf.readLong();
            q[i] = inf.readLong();
        }

        vector<int>       eu(r), ev(r);
        vector<long long> ew(r);
        vector<double>    wdeg(n + 1, 0.0);

        for (int i = 0; i < r; i++) {
            eu[i] = inf.readInt();
            ev[i] = inf.readInt();
            ew[i] = inf.readLong();
            wdeg[eu[i]] += (double)ew[i];
            wdeg[ev[i]] += (double)ew[i];
        }

        // Read participant answer: n integers
        vector<long long> x(n + 1);
        for (int i = 1; i <= n; i++) {
            x[i] = ouf.readLong();
        }

        // Validate feasibility
        bool feasible = true;
        {
            set<long long> used;
            for (int i = 1; i <= n && feasible; i++) {
                if (x[i] < 0 || x[i] >= m) {
                    feasible = false;
                } else if (!used.insert(x[i]).second) {
                    feasible = false;
                }
            }
        }

        // Compute participant objective F
        double F = 0.0;
        if (feasible) {
            F = computeEnergy(r, eu, ev, ew, p, q, x);
        }

        // Compute baseline B
        vector<int> order(n);
        for (int i = 0; i < n; i++) order[i] = i + 1;
        sort(order.begin(), order.end(), [&](int a, int b) {
            if (wdeg[a] != wdeg[b]) return wdeg[a] > wdeg[b];
            return a < b;
        });

        vector<long long> baseline(n + 1, 0LL);
        if (n == 1) {
            baseline[order[0]] = 0LL;
        } else {
            for (int k = 0; k < n; k++) {
                baseline[order[k]] = (long long)k * (m - 1) / (long long)(n - 1);
            }
        }

        double B = computeEnergy(r, eu, ev, ew, p, q, baseline);

        // Per-case: clamp((F+1)/(B+1), 0, 2)
        // Normalize to [0,1] by dividing by 2 for aggregation via quitp
        double ratio = (F + 1.0) / (B + 1.0);
        if (ratio < 0.0) ratio = 0.0;
        if (ratio > 2.0) ratio = 2.0;

        // score_ratio in [0,1]
        double score_ratio = ratio / 2.0;
        total_score_ratio += score_ratio;
    }

    // Strict end-of-file check: reject any trailing garbage
    if (!ouf.seekEof()) {
        quitf(_wa, "extra output after all test cases");
    }

    // avg_ratio in [0,1]; quitp requires value in [0,1]
    double avg_ratio = total_score_ratio / (double)t;
    if (avg_ratio < 0.0) avg_ratio = 0.0;
    if (avg_ratio > 1.0) avg_ratio = 1.0;

    quitp(avg_ratio, "Ratio: %f", avg_ratio);
}