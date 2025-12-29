#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, K;
    cin >> N >> K;
    vector<int> a(11);
    for (int i = 1; i <= 10; ++i) {
        cin >> a[i];
    }
    vector<pair<long long, long long>> points(N);
    for (int i = 0; i < N; ++i) {
        cin >> points[i].first >> points[i].second;
    }
    
    if (N == 0) {
        cout << 0 << endl;
        return 0;
    }
    
    // Vertical lines (by x)
    auto sx = points;
    sort(sx.begin(), sx.end());
    vector<int> cuts_x;
    for (int i = 0; i < N - 1; ++i) {
        if (sx[i].first + 1 < sx[i + 1].first) {
            cuts_x.push_back(i);
        }
    }
    vector<int> chosen_x;
    int prev_x = -1;
    int num_v = 50;
    for (int j = 1; j <= num_v; ++j) {
        double frac = static_cast<double>(j) / 51.0;
        int target = static_cast<int>(round(frac * N)) - 1;
        if (target < 0 || target >= N - 1) continue;
        int best_k = -1;
        long long min_dist = LLONG_MAX;
        for (size_t kk = 0; kk < cuts_x.size(); ++kk) {
            int ci = cuts_x[kk];
            if (ci <= prev_x) continue;
            long long dist = abs(static_cast<long long>(ci) - target);
            if (dist < min_dist) {
                min_dist = dist;
                best_k = static_cast<int>(kk);
            }
        }
        if (best_k != -1) {
            int ii = cuts_x[best_k];
            chosen_x.push_back(ii);
            prev_x = ii;
        }
    }
    
    // Horizontal lines (by y)
    vector<pair<long long, long long>> sy(N);
    for (int i = 0; i < N; ++i) {
        sy[i] = {points[i].second, points[i].first};
    }
    sort(sy.begin(), sy.end());
    vector<int> cuts_y;
    for (int i = 0; i < N - 1; ++i) {
        if (sy[i].first + 1 < sy[i + 1].first) {
            cuts_y.push_back(i);
        }
    }
    vector<int> chosen_y;
    int prev_y = -1;
    int num_h = 50;
    for (int j = 1; j <= num_h; ++j) {
        double frac = static_cast<double>(j) / 51.0;
        int target = static_cast<int>(round(frac * N)) - 1;
        if (target < 0 || target >= N - 1) continue;
        int best_k = -1;
        long long min_dist = LLONG_MAX;
        for (size_t kk = 0; kk < cuts_y.size(); ++kk) {
            int ci = cuts_y[kk];
            if (ci <= prev_y) continue;
            long long dist = abs(static_cast<long long>(ci) - target);
            if (dist < min_dist) {
                min_dist = dist;
                best_k = static_cast<int>(kk);
            }
        }
        if (best_k != -1) {
            int ii = cuts_y[best_k];
            chosen_y.push_back(ii);
            prev_y = ii;
        }
    }
    
    // Collect lines
    vector<tuple<long long, long long, long long, long long>> lines;
    long long BIG = 1000000000LL;
    
    // Vertical
    for (int idx : chosen_x) {
        long long cc = sx[idx].first + 1;
        lines.emplace_back(cc, -BIG, cc, BIG);
    }
    
    // Horizontal
    for (int idx : chosen_y) {
        long long dd = sy[idx].first + 1;
        lines.emplace_back(-BIG, dd, BIG, dd);
    }
    
    int k = lines.size();
    cout << k << endl;
    for (const auto& ln : lines) {
        long long px, py, qx, qy;
        tie(px, py, qx, qy) = ln;
        cout << px << " " << py << " " << qx << " " << qy << "\n";
    }
    
    return 0;
}