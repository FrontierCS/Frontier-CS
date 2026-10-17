#include "testlib.h"
#include <algorithm>
#include <cmath>
#include <vector>
using namespace std;

int main(int argc, char* argv[]) {
    registerTestlibCmd(argc, argv);
    const int T = inf.readInt(1, 50000, "T");
    long double total_points = 0;
    for (int tc = 1; tc <= T; ++tc) {
        const int n = inf.readInt(1, 500000, "n");
        const int m = inf.readInt(1, 500000, "m");
        const long long c = inf.readLong(0LL, 500000LL, "c");
        vector<long long> a(n + 1, 0), b(m + 1, 0);
        for (int i = 1; i <= n; ++i)
            a[i] = a[i - 1] + inf.readLong(0LL, 1000000000000LL, "a[i]");
        for (int i = 1; i <= m; ++i)
            b[i] = b[i - 1] + inf.readLong(0LL, 1000000000000LL, "b[i]");
        auto rank = [&](long long experience) -> long long {
            return upper_bound(b.begin() + 1, b.end(), experience) - (b.begin() + 1);
        };
        const long long reference = ans.readLong();
        const long long baseline = rank(a[n]) - c;
        if (reference < baseline)
            quitf(_fail, "Case %d: reference %lld below one-character value %lld", tc, reference, baseline);

        const int d = ouf.readInt(1, n, "number of segments");
        long long value = -c * d;
        int next_day = 1;
        for (int j = 0; j < d; ++j) {
            const int l = ouf.readInt(1, n, "segment left endpoint");
            const int r = ouf.readInt(l, n, "segment right endpoint");
            if (l != next_day)
                quitf(_wa, "Case %d: segments must consecutively cover all days", tc);
            value += rank(a[r] - a[l - 1]);
            next_day = r + 1;
        }
        if (next_day != n + 1)
            quitf(_wa, "Case %d: final days are not covered", tc);
        if (value > reference)
            quitf(_fail, "Case %d: feasible value %lld exceeds reference %lld", tc, value, reference);

        // Subtract in a wide integer type before converting the physical regret.
        const __int128 regret = (__int128)reference - value;
        const __int128 reference_regret = (__int128)reference - baseline;
        long double points;
        if (regret == 0) points = 100;
        else if (reference_regret == 0) points = 0;
        else if (regret >= reference_regret)
            points = 60 * max(0.0L, 2.0L - (long double)regret / (long double)reference_regret);
        else
            points = min(100.0L, 60.0L + log((long double)reference_regret) - log((long double)regret));
        total_points += points;
    }
    if (!ouf.seekEof()) quitf(_wa, "Extra output found");
    const double ratio = (double)(total_points / (100.0L * T));
    quitp(ratio, "Ratio: %.12f, RatioUnbounded: %.12f", ratio, ratio);
}
