#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N, K;
    if (!(cin >> N >> K)) return 0;
    vector<int> a(11);
    for (int d = 1; d <= 10; ++d) cin >> a[d];
    vector<int> xs(N), ys(N);
    unordered_set<int> sx, sy;
    sx.reserve(N*2); sy.reserve(N*2);
    for (int i = 0; i < N; ++i) {
        cin >> xs[i] >> ys[i];
        sx.insert(xs[i]);
        sy.insert(ys[i]);
    }

    // Determine numbers of vertical (G) and horizontal (H) lines
    int G = K / 2;
    int H = K - G;

    // We'll place lines within [-9500, 9500] approximately evenly spaced
    auto genLines = [&](int L, const unordered_set<int>& avoid) -> vector<long long> {
        vector<long long> cs;
        if (L <= 0) return cs;
        // Use double spacing to avoid clustering
        double left = -9500.0, right = 9500.0;
        for (int i = 1; i <= L; ++i) {
            double pos = left + (right - left) * (i) / (L + 1);
            long long c = llround(pos);
            // Adjust to avoid exact coordinates of strawberries and duplicates
            // Try small shifts within [-10000, 10000]
            int tries = 0;
            while ((avoid.find((int)c) != avoid.end() || (!cs.empty() && cs.back() == c)) && tries < 100) {
                c++;
                if (c > 10000) c = -10000;
                ++tries;
            }
            cs.push_back(c);
        }
        // Ensure strictly increasing (not necessary but helpful to avoid coincidences)
        sort(cs.begin(), cs.end());
        for (size_t i = 1; i < cs.size(); ++i) {
            if (cs[i] <= cs[i-1]) cs[i] = cs[i-1] + 1;
            if (cs[i] > 10000) cs[i] = 10000;
        }
        return cs;
    };

    vector<long long> vlines = genLines(G, sx);
    vector<long long> hlines = genLines(H, sy);

    vector<array<long long,4>> cuts;
    cuts.reserve(K);
    const long long BIG = 1000000000LL;

    for (auto c : vlines) {
        cuts.push_back({c, -BIG, c, BIG});
    }
    for (auto c : hlines) {
        cuts.push_back({-BIG, c, BIG, c});
    }

    cout << cuts.size() << "\n";
    for (auto &ln : cuts) {
        cout << ln[0] << " " << ln[1] << " " << ln[2] << " " << ln[3] << "\n";
    }
    return 0;
}