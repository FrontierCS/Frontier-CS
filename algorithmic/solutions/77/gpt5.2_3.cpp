#include <bits/stdc++.h>
using namespace std;

static uint64_t splitmix64(uint64_t x) {
    x += 0x9e3779b97f4a7c15ULL;
    x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
    x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
    return x ^ (x >> 31);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    while (cin >> n >> m) {
        uint64_t seed = (uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count();
        seed ^= (uint64_t)(uintptr_t)&seed;
        seed = splitmix64(seed);
        mt19937_64 rng(seed);
        uniform_real_distribution<double> dist(0.0, 1.0);

        const int IDX0 = n;
        const int IDX1 = n + 1;
        const int N = n + 2;

        vector<long double> w(N, 1.0L);
        const long double beta = 0.6L;

        for (int t = 0; t < m; t++) {
            string s;
            cin >> s;

            long double sumAll = w[IDX0] + w[IDX1];
            long double sumOne = w[IDX1]; // constant-1 expert

            for (int i = 0; i < n; i++) {
                sumAll += w[i];
                if (s[i] == '1') sumOne += w[i];
            }

            double p1 = 0.5;
            if (sumAll > 0) p1 = (double)(sumOne / sumAll);
            double u = dist(rng);
            int pred = (u < p1) ? 1 : 0;

            cout << pred << "\n" << flush;

            string outStr;
            cin >> outStr;
            int y = outStr[0] - '0';

            for (int i = 0; i < n; i++) {
                int gi = s[i] - '0';
                if (gi != y) w[i] *= beta;
            }
            if (y == 1) w[IDX0] *= beta; // constant-0 wrong
            if (y == 0) w[IDX1] *= beta; // constant-1 wrong
        }
    }

    return 0;
}