#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, K;
    if (!(cin >> N >> K)) return 0;
    vector<int> a(11);
    for (int i = 1; i <= 10; ++i) cin >> a[i];
    vector<pair<int,int>> pts(N);
    for (int i = 0; i < N; ++i) cin >> pts[i].first >> pts[i].second;

    const int R = 9999; // inside circle radius (<10000)
    int nv = K / 2;
    int nh = K - nv;

    unordered_set<int> xs, ys;
    xs.reserve(N*2);
    ys.reserve(N*2);
    for (auto &p : pts) {
        xs.insert(p.first);
        ys.insert(p.second);
    }

    auto pick_positions = [&](int cnt, const unordered_set<int>& forbidden) -> vector<int> {
        vector<int> pos;
        pos.reserve(cnt);
        unordered_set<int> used;
        used.reserve(cnt*2);
        if (cnt <= 0) return pos;
        double step = (2.0 * R) / (cnt + 1);
        for (int j = 1; j <= cnt; ++j) {
            double target = -R + j * step;
            int c0 = (int)llround(target);
            int best = INT_MAX;
            // search nearest available integer within [-R, R]
            for (int d = 0; d <= 2*R+2; ++d) {
                int cand1 = c0 + d;
                if (cand1 >= -R && cand1 <= R && !forbidden.count(cand1) && !used.count(cand1)) { best = cand1; break; }
                int cand2 = c0 - d;
                if (d != 0 && cand2 >= -R && cand2 <= R && !forbidden.count(cand2) && !used.count(cand2)) { best = cand2; break; }
            }
            if (best == INT_MAX) {
                // fallback: pick any unused within [-R,R]
                for (int c = -R; c <= R; ++c) {
                    if (!forbidden.count(c) && !used.count(c)) { best = c; break; }
                }
                if (best == INT_MAX) best = max(-R, min(R, c0)); // should not happen
            }
            used.insert(best);
            pos.push_back(best);
        }
        return pos;
    };

    vector<int> vx = pick_positions(nv, xs);
    vector<int> vy = pick_positions(nh, ys);

    vector<array<int,4>> lines;
    lines.reserve(K);
    const int LIM = 1000000000;
    for (int c : vx) {
        lines.push_back({c, -LIM, c, LIM}); // vertical x=c
    }
    for (int c : vy) {
        lines.push_back({-LIM, c, LIM, c}); // horizontal y=c
    }

    cout << (int)lines.size() << "\n";
    for (auto &ln : lines) {
        cout << ln[0] << " " << ln[1] << " " << ln[2] << " " << ln[3] << "\n";
    }
    return 0;
}