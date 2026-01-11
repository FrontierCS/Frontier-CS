#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    const double alpha = 0.15;
    const double decay = 1.0 - alpha;

    vector<double> w(n, 1.0);

    std::mt19937_64 rng(
        (uint64_t)chrono::steady_clock::now().time_since_epoch().count()
    );

    string s;
    char actual;
    for (int round = 0; round < m; ++round) {
        if (!(cin >> s)) return 0;

        double totalW = 0.0;
        for (int i = 0; i < n; ++i) totalW += w[i];

        if (totalW <= 0) {
            for (int i = 0; i < n; ++i) w[i] = 1.0;
            totalW = n;
        }

        std::uniform_real_distribution<double> dist(0.0, totalW);
        double r = dist(rng);
        int chosen = n - 1;
        double acc = 0.0;
        for (int i = 0; i < n; ++i) {
            acc += w[i];
            if (r <= acc) {
                chosen = i;
                break;
            }
        }

        char guess = s[chosen];
        cout << guess << '\n';
        cout.flush();

        if (!(cin >> actual)) return 0;

        double maxW = 0.0;
        for (int i = 0; i < n; ++i) {
            if (s[i] != actual) w[i] *= decay;
            if (w[i] > maxW) maxW = w[i];
        }

        if (maxW == 0.0) {
            for (int i = 0; i < n; ++i) w[i] = 1.0;
        } else if (maxW < 1e-200) {
            double scale = 1.0 / maxW;
            for (int i = 0; i < n; ++i) w[i] *= scale;
        } else if (maxW > 1e200) {
            double scale = 1.0 / maxW;
            for (int i = 0; i < n; ++i) w[i] *= scale;
        }
    }

    return 0;
}